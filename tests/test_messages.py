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


@pytest.mark.parametrize("doc", [PARTICIPANT, MEDICATION], ids=lambda d: d[0])
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
