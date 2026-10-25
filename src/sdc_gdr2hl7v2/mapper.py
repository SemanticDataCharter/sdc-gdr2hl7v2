"""The HL7 v2.5.1 mapper: a Governed Data Record as an ORU^R01 message in ER7, by a mapping file (a site profile).

What a mapping file says, by its rules' `to`:

- a cluster to `MSH`: the record itself; the rule's `attributes` are the site profile's constants (`MSH-4`, `MSH-11`,
  `PID-5`, the default `OBX-11`, ...);
- a cluster to `OBR`: an order group; its OBR-4 is the cluster's LOINC code where the model binds one, else the
  rule's `attributes["OBR-4"]`, else the cluster's own identifier as a local code (`<ct_id>^<label>^99SDC`);
- a cluster to `OBX`: one OBX for the cluster (a code, its display text and its system, held as three values), whose
  fields its values set (`OBX-5.1`, `OBX-5.2`, ...); `attributes` give its fixed fields (`OBX-2`, `OBX-5.3`);
- `.`: no segment of its own; `omit`: nothing under it, with a reason;
- a component to `OBX`: an observation of its own. OBX-2 follows from the SDC type (NM, ST, CWE, DT, TS, TM); OBX-3 is
  the LOINC code the model binds the component to (`skos:exactMatch`), and the value is then a lookup; otherwise the
  component's identifier as a local code, and the value is declared. A coded value is CWE: the code the model binds
  it to (LOINC, SNOMED CT, NCI Thesaurus) with the text, or the text alone. Units go to OBX-6 through the rule's units
  table (UCUM);
- a component to a field: `PID-n`, `MSH-n`, `OBR-n` (its group's OBR), `OBX-n` (its cluster's OBX), or `OBX*-n`
  (every OBX in its group, unless an OBX sets its own: a reading's status for each of its results).

HL7 v2 has no general null flavor. An observation whose value is an Exceptional Value is still sent, with OBX-5
empty: Not Asked is OBX-11 `N` ("not asked", table 0085), preserved; every other code is OBX-11 `X` ("results
cannot be obtained"), degraded, and an NTE after the OBX carries the ISO 21090 code and name. An Exceptional Value in
any other field is lost: the field is left empty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from sdc_mapper import (DECLARED, DEGRADED, EXACT_MATCH, LOINC, LOOKUP, LOST, NCIT, NOT_REPRESENTABLE, PRESERVED,
                        SNOMED_CT, EVRule, IncompleteMapping, MapResult, MappingError, ValueOutcome, code_of,
                        linked_code)
from sdcreader.record import EXCEPTIONAL_VALUES

from . import __version__
from .er7 import Segment, escape, message
from .validate import errors as validation_errors

VERSION = "2.5.1"
LOCAL = "99SDC"          # HL7 table 0396: a local coding system (99zzz); the code is the component's identifier
#: The code systems the model names (sdc_mapper.codes), as HL7 table 0396 coding systems.
CODING_SYSTEMS = {LOINC: "LN", SNOMED_CT: "SCT", NCIT: "NCIT"}
NOT_ASKED = "NASK"
OTHER_EVS = tuple(c for c in EXCEPTIONAL_VALUES if c != NOT_ASKED)
#: What an observation's OBX-11 (HL7 table 0085) says for each ISO 21090 code.
EV_TABLE = {code: (EVRule(PRESERVED, "N") if code == NOT_ASKED
                   else EVRule(DEGRADED, "X", tuple(c for c in OTHER_EVS if c != code)))
            for code in EXCEPTIONAL_VALUES}
CANNOT_HOLD = [
    "a general null flavor: outside an observation's result status, an Exceptional Value can only be left empty",
    "validity windows and the time a value was recorded (act, vtb, vte, tr)",
    "the definitions the model binds each component to, beyond a code and its coding system",
    "the record's provenance and audit clusters",
]


@dataclass
class _OBX:
    segment: Segment
    ntes: list[str] = field(default_factory=list)


@dataclass
class _Group:
    key: tuple
    cluster: object                      # the cluster component
    rule: object
    obr: Segment
    members: list[_OBX] = field(default_factory=list)
    defaults: dict[str, str] = field(default_factory=dict)   # OBX*-n


def _date(raw: str, form: str | None) -> str:
    if form == "date":
        return date.fromisoformat(raw).strftime("%Y%m%d")
    if form == "time":
        t = time.fromisoformat(raw)
        return t.strftime("%H%M%S")
    if form == "datetime":
        d = datetime.fromisoformat(raw)
        out = d.strftime("%Y%m%d%H%M%S")
        return out + (d.strftime("%z") if d.tzinfo else "")
    return raw


def _text(v) -> str | None:
    """A value as HL7 writes it, unescaped."""
    x = v.value
    if x is None:
        return None
    if v.kind == "temporal":
        return _date(str(x), v.detail.get("form"))
    if isinstance(x, bool):
        return "Y" if x else "N"
    if isinstance(x, Decimal):
        return format(x, "f")
    if isinstance(x, list):
        return " ".join("" if i is None else str(i) for i in x)
    return str(x)


def _coded(iri: str | None) -> tuple[str, str] | None:
    """The code an IRI names and its HL7 coding system, for the code systems v2 writes."""
    ref = code_of(iri)
    return (ref.code, CODING_SYSTEMS[ref.system]) if ref and ref.system in CODING_SYSTEMS else None


def _loinc_of(component) -> str | None:
    """The LOINC code the model binds a component to (skos:exactMatch)."""
    ref = linked_code(component, LOINC, (EXACT_MATCH,))
    return ref.code if ref else None


VALUE_TYPE = {"decimal": "NM", "integer": "NM", "string": "ST", "token": "CWE", "boolean": "CWE", "link": "ST"}


class HL7v2Mapper:
    name = "hl7v2"
    target = "HL7 Version 2"
    target_version = VERSION
    package = "sdc-gdr2hl7v2"
    version = __version__
    ev_table = {code: rule for code, rule in EV_TABLE.items()}

    def map(self, record, mapping) -> MapResult:
        if mapping is None:
            raise MappingError("HL7 v2 needs a mapping file (a site profile): the model does not say which segment "
                               "or field each value goes to")
        for code, override in mapping.exceptional_values.items():
            raise MappingError(f"the HL7 v2 mapper's table for {code} follows from OBX-11; a mapping cannot change it")
        values = record.values
        if not values:
            raise MappingError("nothing to write: the record holds no values")
        root = values[0].path[0]
        root_rule = mapping.cluster_rule(root.ct_id, [])
        if root_rule is None or root_rule.to != "MSH":
            raise MappingError(f"mapping {mapping.id}: the record's root cluster ({root.label}) maps to MSH, with the "
                               "site profile's constants as its attributes")
        site = dict(root_rule.attributes)
        msh, pid = Segment("MSH"), Segment("PID")
        groups: dict[tuple, _Group] = {}
        cluster_obx: dict[tuple, tuple[_Group, _OBX]] = {}
        outcomes: dict[int, ValueOutcome] = {}
        missing = []

        for v in values:
            ids = [c.ct_id for c in v.path]
            group = obx_cluster = omitted = None
            for i, c in enumerate(v.path):
                rule = mapping.cluster_rule(c.ct_id, ids[:i])
                if rule is None or rule.to in (".", "MSH"):
                    continue
                if rule.transform == "omit":
                    omitted = rule
                    break
                key = v.instance_key[: i + 1]
                if rule.to == "OBR":
                    if key not in groups:
                        groups[key] = _Group(key, c, rule, Segment("OBR"))
                    group = groups[key]
                elif rule.to == "OBX":
                    if group is None:
                        raise MappingError(f"mapping {mapping.id}: {c.label} maps to an OBX outside any OBR group")
                    if key not in cluster_obx:
                        seg = Segment("OBX")
                        for addr, raw in rule.attributes.items():
                            seg.set(addr.split("-", 1)[1], raw)
                        if not seg.has("3"):
                            seg.set("3", self._code(c))
                        entry = _OBX(seg)
                        group.members.append(entry)
                        cluster_obx[key] = (group, entry)
                    obx_cluster = cluster_obx[key][1]
                else:
                    raise MappingError(f"mapping {mapping.id}: a cluster maps to MSH, OBR, OBX, '.' or omit, not {rule.to!r}")
            if omitted is not None:
                outcomes[v.position] = ValueOutcome(v.position, NOT_REPRESENTABLE, note=omitted.reason or "")
                continue
            rule = mapping.rule_for(v.ct_id, v.sdc_type, ids)
            if rule is None:
                missing.append(f"{' / '.join(v.path_labels + [v.label])} ({v.ct_id})")
                continue
            if rule.transform == "omit":
                outcomes[v.position] = ValueOutcome(v.position, NOT_REPRESENTABLE, note=rule.reason or "")
                continue
            if rule.to == "OBX":
                if group is None:
                    raise MappingError(f"mapping {mapping.id}: {v.label} is an observation outside any OBR group")
                outcomes[v.position] = self._observation(v, rule, group, mapping)
                continue
            targets = [(rule.to, rule.transform, rule.table, rule.value, rule.format, rule.on_miss)]
            targets += [(a["to"], a["transform"], a.get("table", {}), a.get("value"), a.get("format"),
                         a.get("on_miss", "fail")) for a in rule.also]
            first = None
            for to, transform, table, const, fmt, on_miss in targets:
                o = self._field(v, to, transform, table, const, fmt, on_miss, msh, pid, group, obx_cluster, mapping)
                first = first or o
            outcomes[v.position] = first

        if missing:
            raise IncompleteMapping(f"mapping {mapping.id} has no rule for {len(missing)} value(s): " + "; ".join(missing[:5]))
        er7 = self._assemble(record, site, msh, pid, groups)
        problems = validation_errors(er7)
        if problems:
            raise MappingError(f"the message does not conform to HL7 v{VERSION}: {problems[0]}")
        return MapResult(files={"message.hl7": er7.encode("utf-8")},
                         outcomes=[outcomes[v.position] for v in values if v.position in outcomes],
                         cannot_hold=list(CANNOT_HOLD))

    # ------------------------------------------------------------ observations
    @staticmethod
    def _code(component) -> str:
        loinc = _loinc_of(component)
        if loinc:
            return f"{loinc}^{escape(component.label)}^LN"
        return f"{component.ct_id}^{escape(component.label)}^{LOCAL}"

    def _observation(self, v, rule, group: _Group, mapping) -> ValueOutcome:
        seg = Segment("OBX")
        attrs = dict(rule.attributes)
        component = v.component
        seg.set("2", attrs.pop("OBX-2", None) or self._value_type(v))
        if "OBX-3" in attrs:
            seg.set("3", attrs.pop("OBX-3"))
            cls = DECLARED
        else:
            seg.set("3", self._code(component))
            cls = LOOKUP if _loinc_of(component) else DECLARED
        for addr, raw in attrs.items():
            seg.set(addr.split("-", 1)[1], raw)
        entry = _OBX(seg)
        group.members.append(entry)
        where = f"OBX({seg.fields[3][0][0]})"
        if v.exceptional:
            ev = EV_TABLE[v.exceptional.code]
            seg.set("11", ev.target_code)
            entry.ntes.append(escape(f"ISO 21090 null flavor {v.exceptional.code}: {v.exceptional.name}"))
            if mapping.carry_rejected and v.rejected:
                entry.ntes.append(escape("REJECTED: " + "; ".join(f"{k}={x}" for k, x in v.rejected.items()
                                                                  if isinstance(x, str))))
            return ValueOutcome(v.position, ev.cls, location=where + "-11", target_code=ev.target_code,
                                merged_with=list(ev.merged_with), note="an NTE carries the ISO 21090 code")
        raw = self._value(v, rule)
        if raw is None:
            return ValueOutcome(v.position, NOT_REPRESENTABLE, note="no value to write")
        seg.set("5", raw)
        if rule.units and v.units:
            symbol = v.units.symbol
            table = rule.units.get("table", {})
            if rule.units.get("transform") == "code":
                if symbol not in table:
                    raise MappingError(f"mapping {mapping.id}: the units {symbol!r} of {v.label} are not in its "
                                       "units table")
                seg.set("6", f"{escape(table[symbol])}^{escape(symbol)}^UCUM")
            else:
                seg.set("6", f"{escape(symbol)}^{escape(symbol)}")
        return ValueOutcome(v.position, cls, location=where + "-5")

    @staticmethod
    def _value_type(v) -> str:
        if v.kind == "temporal":
            return {"date": "DT", "time": "TM"}.get(v.detail.get("form"), "TS")
        return VALUE_TYPE.get(v.kind, "ST")

    @staticmethod
    def _value(v, rule) -> str | None:
        text = _text(v)
        if text is None:
            return None
        if rule.transform == "format" and rule.format:
            return rule.format.format(escape(text))
        if rule.transform == "code":
            if text not in rule.table:
                raise MappingError(f"{v.label} ({v.ct_id}) holds {text!r}, which its code table does not list")
            return rule.table[text]
        if rule.transform == "constant":
            return rule.value
        if v.kind == "boolean":
            return f"{text}^{'Yes' if text == 'Y' else 'No'}^HL70136"
        if v.kind == "token":
            coded = _coded(v.code.defined_by if v.code else None)
            return f"{escape(coded[0])}^{escape(text)}^{coded[1]}" if coded else f"^{escape(text)}"
        return escape(text)

    # ------------------------------------------------------------ fields
    def _field(self, v, to, transform, table, const, fmt, on_miss, msh, pid, group, obx_cluster, mapping):
        m = re.fullmatch(r"(MSH|PID|OBR|OBX\*|OBX)-(\d+(?:\.\d+){0,2})", to)
        if not m:
            raise MappingError(f"mapping {mapping.id}: {v.label} maps to {to!r}, which is not OBX, MSH-n, PID-n, OBR-n, "
                               "OBX-n or OBX*-n")
        seg_name, addr = m.groups()
        if v.exceptional:
            return ValueOutcome(v.position, LOST, location=to, note="HL7 v2 leaves the field empty")
        text = _text(v)
        if transform == "constant":
            raw = const
        elif text is None:
            return ValueOutcome(v.position, NOT_REPRESENTABLE, note="no value to write")
        elif transform == "code":
            if text not in table:
                if on_miss == "omit":
                    return ValueOutcome(v.position, NOT_REPRESENTABLE, location=to,
                                        note=f"{text!r} is not in the code table for {to}")
                raise MappingError(f"mapping {mapping.id}: {v.label} ({v.ct_id}) holds {text!r}, which its code table "
                                   f"for {to} does not list")
            raw = table[text]
        elif transform == "format" and fmt:
            raw = fmt.format(escape(text))
        else:
            raw = escape(text)
        if seg_name == "MSH":
            msh.set(addr, raw)
        elif seg_name == "PID":
            pid.set(addr, raw)
        elif seg_name == "OBR":
            if group is None:
                raise MappingError(f"mapping {mapping.id}: {v.label} maps to {to} outside any OBR group")
            group.obr.set(addr, raw)
        elif seg_name == "OBX*":
            if group is None:
                raise MappingError(f"mapping {mapping.id}: {v.label} maps to {to} outside any OBR group")
            group.defaults[addr] = raw
        else:
            if obx_cluster is None:
                raise MappingError(f"mapping {mapping.id}: {v.label} maps to {to} outside a cluster mapped to OBX")
            obx_cluster.segment.set(addr, raw)
        return ValueOutcome(v.position, DECLARED, location=to)

    # ------------------------------------------------------------ the message
    def _assemble(self, record, site: dict, msh: Segment, pid: Segment, groups: dict) -> str:
        created = record.attributes.get("creation_timestamp")
        if not created:
            raise MappingError("the record has no creation timestamp for MSH-7")
        msh.set("7", _date(created, "datetime"))
        msh.set("9", "ORU^R01^ORU_R01")
        msh.set("10", escape(record.instance_id))
        msh.set("12", VERSION)
        for key, raw in site.items():
            seg, addr = key.split("-", 1)
            if seg == "MSH" and not msh.has(addr):
                msh.set(addr, raw)
            elif seg == "PID" and not pid.has(addr):
                pid.set(addr, raw)
        if not pid.has("1"):
            pid.set("1", "1")
        segments = [msh, pid]
        default_status = site.get("OBX-11")
        for n, g in enumerate(groups.values(), start=1):
            g.obr.set("1", str(n))
            if not g.obr.has("4"):
                g.obr.set("4", g.rule.attributes.get("OBR-4") or self._code(g.cluster))
            segments.append(g.obr)
            for k, entry in enumerate(g.members, start=1):
                seg = entry.segment
                seg.set("1", str(k))
                for addr, raw in g.defaults.items():
                    if not seg.has(addr):
                        seg.set(addr, raw)
                if not seg.has("11"):
                    if default_status is None:
                        raise MappingError("HL7 v2.5.1 requires OBX-11: the site profile states the default result "
                                           "status (OBX-11 among the MSH rule's attributes)")
                    seg.set("11", default_status)
                segments.append(seg)
                for j, note in enumerate(entry.ntes, start=1):
                    nte = Segment("NTE")
                    nte.set("1", str(j))
                    nte.set("3", note)
                    segments.append(nte)
        return message(segments)
