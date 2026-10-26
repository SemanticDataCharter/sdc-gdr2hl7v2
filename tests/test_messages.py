"""The NHANES site profiles: every sample record a conformant HL7 v2.5.1 message; LOINC where the model binds it;
Exceptional Values in OBX-11 with an NTE, or lost where HL7 v2 has no place; refusals rather than guesses."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
import yaml
from lxml import etree

from sdc_mapper import (DECLARED, DEGRADED, ERROR, LOOKUP, LOST, NOT_REPRESENTABLE, PRESERVED, VALID, Engine,
                        load_mapping)
from sdc_gdr2hl7v2 import HL7v2Mapper, mapping_path
from sdc_gdr2hl7v2.er7 import escape
from sdc_gdr2hl7v2.validate import errors

ROOT = Path(__file__).resolve().parents[1]
PARTICIPANT = ("nhanes-participant", "xy8upneajsb8vdcmnve01g6g")
PARTICIPANT_423 = ("nhanes-participant-4.2.3", "eehpfapwgvxtzdrofgstdcfs")   # E-2026-10-01 corrected
PARTICIPANT_424 = ("nhanes-participant-4.2.4", "tp5pg0u4dasqarie0b3ujn2u")   # E-2026-10-03 corrected value bindings
MEDICATION = ("nhanes-medication", "epbdfmvxc3gbh5f66hhb3o2m")
SDC4 = "https://semanticdatacharter.com/ns/sdc4/"


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    return Engine(schema_dir=tmp_path_factory.mktemp("schemas"))


def records(doc):
    return sorted((ROOT / "samples" / doc[0] / "records").glob("*.xml"))


def run(engine, doc, xml: bytes, mapping=None):
    return engine.map_record(xml, HL7v2Mapper(), mapping or load_mapping(mapping_path(doc[1])),
                             directory=str(ROOT / "samples" / doc[0]))


def segments(r):
    return [s.split("|") for s in r.files["message.hl7"].decode().split("\r") if s]


@pytest.mark.parametrize("doc", [PARTICIPANT, PARTICIPANT_423, PARTICIPANT_424, MEDICATION], ids=lambda d: d[0])
def test_every_record_is_a_conformant_message(engine, doc):
    for f in records(doc):
        r = run(engine, doc, f.read_bytes())
        assert r.outcome == VALID, (f.name, r.errors)
        assert not errors(r.files["message.hl7"].decode()), f.name
        assert {v["class"] for v in r.report.values} <= {LOOKUP, DECLARED, NOT_REPRESENTABLE}


def test_the_same_record_gives_the_same_bytes(engine):
    xml = records(PARTICIPANT)[0].read_bytes()
    assert run(engine, PARTICIPANT, xml).files == run(engine, PARTICIPANT, xml).files


def test_header_and_patient_come_from_the_record_and_the_site_profile(engine):
    f = records(PARTICIPANT)[0]
    r = run(engine, PARTICIPANT, f.read_bytes())
    msh, pid = segments(r)[:2]
    assert msh[8] == "ORU^R01^ORU_R01" and msh[11] == "2.5.1" and msh[10] == "T"
    assert msh[9] == r.report.record["instance_id"], "the control id is the record's identifier"
    assert pid[3].endswith("^^^NHANES^PI") and pid[5] == '""'
    seqn = next(v for v in r.report.values if v["label"] == "Respondent Sequence Number (SEQN)")
    assert seqn["class"] == DECLARED and seqn["location"] == "PID-3"


def test_loinc_bound_observations_are_lookups(engine):
    r = run(engine, PARTICIPANT, records(PARTICIPANT)[0].read_bytes())
    obx = {s[3].split("^")[0]: s for s in segments(r) if s[0] == "OBX"}
    assert obx["718-7"][3].endswith("^LN") and obx["718-7"][6].endswith("^UCUM"), "hemoglobin, LOINC, UCUM"
    hgb = next(v for v in r.report.values if v["label"] == "Hemoglobin")
    assert hgb["class"] == LOOKUP
    local = next(v for v in r.report.values if v["label"] == "Annual Household Income (INDHHIN2)")
    assert local["class"] == DECLARED, "no LOINC binding: the component's identifier is the local code"
    assert any(s[3].endswith("^99SDC") for s in obx.values())


def test_a_coded_cluster_is_one_cwe(engine):
    r = run(engine, MEDICATION, records(MEDICATION)[0].read_bytes())
    dx = [s for s in segments(r) if s[0] == "OBX" and s[3].split("^")[1] == "Diagnosis (ICD-10-CM)"]
    assert dx and all(s[2] == "CWE" and s[5].endswith("^I10C") for s in dx)


def test_mmhg_is_written_as_ucum_writes_it(engine):
    r = run(engine, PARTICIPANT, records(PARTICIPANT)[0].read_bytes())
    assert any(s[0] == "OBX" and s[6] == "mm[Hg]^mmHg^UCUM" for s in segments(r))


def test_escape():
    assert escape("a|b^c&d~e\\f") == "a\\F\\b\\S\\c\\T\\d\\R\\e\\E\\f"


# ---------------------------------------------------------------- Exceptional Values
def with_ev(doc, xml: bytes, label: str, code: str, name: str) -> bytes:
    from sdcreader import load_package, read_model
    model = read_model(load_package(ROOT / "samples" / doc[0], doc[1]))
    ids = {c.ct_id for c in model.components.values() if c.label == label}
    tree = etree.parse(io.BytesIO(xml))
    el = next(e for e in tree.getroot().iter() if isinstance(e.tag, str) and e.tag.startswith(f"{{{SDC4}}}ms-")
              and e.tag.split("ms-", 1)[1] in ids)
    after = el.find("sdc4:act", {"sdc4": SDC4})
    after = after if after is not None else el.find("label")
    ev = etree.Element(f"{{{SDC4}}}{code}")
    etree.SubElement(ev, "ev-name").text = name
    after.addnext(ev)
    return etree.tostring(tree)


def test_an_exceptional_observation_is_sent_with_its_status_and_an_nte(engine):
    xml = with_ev(PARTICIPANT, records(PARTICIPANT)[0].read_bytes(), "Hemoglobin", "ASKR", "Asked and Refused")
    r = run(engine, PARTICIPANT, xml)
    assert r.outcome == VALID, r.errors
    segs = segments(r)
    i = next(i for i, s in enumerate(segs) if s[0] == "OBX" and s[3].startswith("718-7^"))
    assert segs[i][5] == "" and segs[i][11] == "X"
    assert segs[i + 1][0] == "NTE" and "ASKR" in segs[i + 1][3]
    ev = r.report.exceptional[0]
    assert (ev["class"], ev["target_code"]) == (DEGRADED, "X") and "NASK" not in ev["merged_with"]
    assert not errors(r.files["message.hl7"].decode())


def test_not_asked_is_preserved(engine):
    xml = with_ev(PARTICIPANT, records(PARTICIPANT)[0].read_bytes(), "Hemoglobin", "NASK", "Not Asked")
    r = run(engine, PARTICIPANT, xml)
    assert [(e["class"], e["target_code"]) for e in r.report.exceptional] == [(PRESERVED, "N")]


def test_an_exceptional_value_in_a_field_is_lost(engine):
    xml = with_ev(PARTICIPANT, records(PARTICIPANT)[0].read_bytes(), "Administrative Gender", "UNK", "Unknown")
    r = run(engine, PARTICIPANT, xml)
    assert r.outcome == VALID, r.errors
    assert [e["class"] for e in r.report.exceptional] == [LOST]
    assert len(segments(r)[1]) < 9 or segments(r)[1][8] == ""


def test_an_exceptional_patient_identifier_refuses_the_message(engine):
    xml = with_ev(PARTICIPANT, records(PARTICIPANT)[0].read_bytes(), "Respondent Sequence Number (SEQN)", "MSK",
                  "Masked")
    r = run(engine, PARTICIPANT, xml)
    assert r.outcome == ERROR and "PID" in r.errors[0]["reason"]


# ---------------------------------------------------------------- the mapping decides
def test_no_mapping_no_message(engine):
    r = engine.map_record(records(PARTICIPANT)[0].read_bytes(), HL7v2Mapper(), None,
                          directory=str(ROOT / "samples" / PARTICIPANT[0]))
    assert r.outcome == ERROR and "site profile" in r.errors[0]["reason"]


def test_a_value_no_rule_reaches_is_an_incomplete_mapping(engine, tmp_path):
    doc = yaml.safe_load(mapping_path(MEDICATION[1]).read_text())
    doc["rules"] = [r for r in doc["rules"] if r.get("to") != "PID-3"]
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    r = run(engine, MEDICATION, records(MEDICATION)[0].read_bytes(), load_mapping(p))
    assert r.outcome == ERROR and "Respondent Sequence Number" in r.errors[0]["reason"]


def test_a_units_symbol_outside_the_table_is_an_error(engine, tmp_path):
    doc = yaml.safe_load(mapping_path(MEDICATION[1]).read_text())
    for rule in doc["rules"]:
        if "units" in rule:
            rule["units"]["table"] = {"nothing": "x"}
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    r = run(engine, MEDICATION, records(MEDICATION)[0].read_bytes(), load_mapping(p))
    assert r.outcome == ERROR and "units table" in r.errors[0]["reason"]


def pregnancy_answers(engine, doc):
    """Every "Are you pregnant now?" OBX-5 in the sample, as (code, text)."""
    out = set()
    for f in records(doc):
        for seg in segments(run(engine, doc, f.read_bytes())):
            if seg[0] == "OBX" and "Are you pregnant now?" in seg[3]:
                code, text, system = seg[5].split("^")[:3]
                assert system == "LN"
                out.add((code, text))
    return out


def test_the_corrected_model_sends_the_right_loinc_answer_codes(engine):
    """E-2026-10-01: the NIH CDE record bound each answer to the next one's LOINC code. NHANES Participant 4.2.3
    composes the NIH CDE library's correction; the 4.2.0 model, kept for its published records, still carries the
    source's codes."""
    right = {("LA15173-0", "Yes"), ("LA26683-5", "No"), ("LA4489-6", "Unknown")}
    assert pregnancy_answers(engine, PARTICIPANT_423) == right
    assert pregnancy_answers(engine, PARTICIPANT_424) == right
    assert pregnancy_answers(engine, PARTICIPANT).isdisjoint(right)


def coded_values(engine, doc) -> dict[tuple[str, str], str]:
    """(SEQN, observation label) -> OBX-5, for every coded observation of the sample."""
    import re
    out = {}
    for f in records(doc):
        xml = f.read_bytes()
        seqn = re.search(rb"SEQN=(\d+)", xml).group(1).decode()
        for seg in segments(run(engine, doc, xml)):
            if seg[0] == "OBX" and seg[2] == "CWE" and "^" in seg[3]:
                out[(seqn, seg[3].split("^")[1])] = seg[5]
    return out


def test_the_4_2_4_model_sends_the_codes_its_terminologies_confirm(engine):
    """E-2026-10-03 (the FAIR Data Demo's SOURCE-ERRATA.md): 4.2.3 bound every level of the difficulty scale to NCIt
    C17998 Unknown, both pregnancy-at-exam answers to C25191, citizenship to C41130 and Mexican American to C67175. The
    two samples hold the same participants."""
    old, new = coded_values(engine, PARTICIPANT_423), coded_values(engine, PARTICIPANT_424)
    assert old.keys() == new.keys()
    assert new[("100913", "Difficulty Lifting or Carrying (PFQ061E)")] == "C121736^No difficulty^NCIT"
    assert old[("100913", "Difficulty Lifting or Carrying (PFQ061E)")] == "C17998^No difficulty^NCIT"
    assert new[("100913", "Pregnancy Status at Exam (RIDEXPRG)")] == "C82475^Not pregnant at exam^NCIT"
    assert new[("100913", "Citizenship Status (DMDCITZN)")] == "C90516^Citizen by birth or naturalization^NCIT"
    assert new[("93946", "Race/Hispanic Origin with NH Asian (RIDRETH3)")] == "C67114^Mexican American^NCIT"
    assert not {v.split("^")[0] for v in new.values()} & {"C25191", "C41130", "C67175", "C39303"}
    assert {v for v in new.values() if v.startswith("C17998^")} <= {"C17998^Cannot ascertain if pregnant at exam^NCIT"}


@pytest.mark.parametrize("doc", [PARTICIPANT, PARTICIPANT_423, PARTICIPANT_424], ids=lambda d: d[0])
def test_a_value_defined_by_a_codebook_is_sent_as_text_never_as_a_code(engine, doc):
    """A value the model defines by an agency codebook page (DEMO_J.htm#DMDCITZN) carries no code: OBX-5 is its text,
    with no identifier and no coding system. A coded OBX-5 is a LOINC, SNOMED CT or NCIt code under its own system."""
    import re
    systems = {"LN": re.compile(r"^(LA)?[0-9]+-[0-9]$"), "SCT": re.compile(r"^[0-9]+$"), "NCIT": re.compile(r"^C[0-9]+$")}
    for value in coded_values(engine, doc).values():
        ident, text, system = (value.split("^") + ["", "", ""])[:3]
        assert text and "://" not in value, value
        if ident or system:
            assert system in systems and systems[system].match(ident), value
    texts = [v for v in coded_values(engine, doc).values() if v.startswith("^")]
    if doc is PARTICIPANT_424:
        assert "^Not a citizen of the US" in texts and "^Do not do this activity" in texts

