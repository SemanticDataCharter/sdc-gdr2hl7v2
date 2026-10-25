# sdc-gdr2hl7v2

Governed Data Records as HL7 v2.5.1 messages in ER7 encoding. A target mapper for
[sdc-mapper](https://github.com/SemanticDataCharter/sdc-mapper): the core validates the record, resolves every value
against its model and reports each one; this package says which segment and field each value goes to and writes the
message. Outbound only. Apache 2.0.

**Status:** 4.0.2. Two models so far, from the FAIR Data Demo:

| Model | ct_id | Message | Rules |
|---|---|---|---|
| NHANES Participant | `xy8upneajsb8vdcmnve01g6g` | ORU^R01 | 44 |
| NHANES Medication | `epbdfmvxc3gbh5f66hhb3o2m` | ORU^R01 | 18 |

## Use

```python
from sdc_mapper import Engine, load_mapping
from sdc_gdr2hl7v2 import HL7v2Mapper, mapping_path

result = Engine().map_record(xml, HL7v2Mapper(), load_mapping(mapping_path("xy8upneajsb8vdcmnve01g6g")))
result.files["message.hl7"]      # ER7, segments separated by carriage returns
result.report                    # every value: lookup, declared or not representable, and why
```

Through sdc-mapper's MCP server and CLI the mapper is the target `hl7v2`.

## The target and its terms

**HL7 Version 2.5.1**, ER7 encoding. Since 1 April 2013 HL7 International has made its core standards, HL7 v2
among them, available free of charge under a click-through license agreement (http://www.hl7.org/legal/ippolicy.cfm).
HL7 keeps the copyright, and use depends on who the user is: a non-member may view, evaluate and use the standards to
build and sell products that implement HL7 v2, but may not copy or redistribute the text of the specifications, in
whole or in part. This package implements HL7 v2.5.1 and incorporates none of its text: no tables, no segment
definitions, no chapter content. It writes the handful of codes a message needs (`ORU^R01`, result status `F`, `N`,
`X`, coding system identifiers such as `LN`, `SCT`, `I10C`, `UCUM`), and names the HL7 tables they come from. The
terms were confirmed on 25 October 2026.

**Validation is independent of the writer.** Every message is parsed and validated by
[hl7apy](https://github.com/crs4/hl7apy) (MIT) at its strict level against its own HL7 v2.5.1 message structures:
segment groups, order and cardinality, required fields and datatypes. A message that does not validate is not
written; the call ends as an error naming what HL7 requires. hl7apy does not check that a coded value is in its HL7
table, and its 2.5.1 definitions give components no maximum lengths: the mapping file's code tables decide the
codes, and see *Lengths* below.

## The messages

**ORU^R01 for both models.** NHANES is a survey: what it holds are observations about the participant, which is what
ORU^R01 carries. For the medication model, HL7 v2.5.1's pharmacy messages describe what a system ordered (RDE),
dispensed (RDS), gave (RGV) or administered (RAS). An NHANES medication row is none of these: it is what the
participant reported taking in the past month. It is sent as observations too, one OBR group: the drug's NHANES code,
its name, the days taken, the number of medicines, and each reason for taking it as an ICD-10-CM code.

- **MSH:** the sending application, facility and processing ID (`T`, training) are the site profile's constants. The
  date and time is the record's creation timestamp and the control ID is the record's identifier, so the same record
  always gives the same bytes.
- **PID:** the participant's NHANES sequence number in PID-3 (`<SEQN>^^^NHANES^PI`), the administrative gender in
  PID-8 (table 0001). NHANES publishes no names; PID-5 is required, so it is the explicit null `""`.
- **OBR:** one group per study section (blood pressure, demographics, laboratory, medical conditions, physical
  functioning, smoking, survey design) and one per blood pressure reading. OBR-4 is the section's LOINC code where
  the model binds one, otherwise the cluster's identifier as a local code. A reading's status is its OBR-25 (table
  0123) and each of its results' OBX-11 (table 0085).
- **OBX:** one per value. OBX-2 follows from the SDC type (NM, ST, CWE, DT, TS, TM). OBX-3 is the LOINC code the
  model binds the component to (`skos:exactMatch`); where the model binds none, it is the component's own identifier
  in the local coding system `99SDC` (`<ct_id>^<label>^99SDC`). A coded answer is a CWE with the code the model binds
  the answer to (LOINC answer codes, SNOMED CT, NCI Thesaurus) and its text, or the text alone where the binding is
  not a code system HL7 names. Units go to OBX-6 in UCUM through the mapping's units table: the Default and FAIR
  libraries' symbols are UCUM already, apart from `mmHg` (UCUM `mm[Hg]`) and counts (UCUM annotations such as
  `{items}`). A code, its display text and its system, held as three values in a coded cluster (a body site, a
  diagnosis), become one CWE in one OBX.
- **Result status:** the site profile states the default (`F`: NHANES is a public release); a reading's own status
  overrides it.

## Where values go: lookup and declared

Where the model binds a component to LOINC, its OBX is a **lookup**: the model says what it is, and the mapping says
only that it is an observation. In the participant sample, 4,694 of the 13,716 values that reach the message are
lookups (laboratory results, blood pressure, heart rate, smoking status). The rest are **declared**: placed by a rule,
coded by the component's own identifier. Each mapping file is a site profile, written with `tools/build_mapping.py`
from a spec in the model's labels (`tools/specs/`), which checks that every value the model can hold reaches a rule.

## Exceptional Values

HL7 v2 has no general null flavor. What it has is a result status for each observation (OBX-11, table 0085), and
notes (NTE). This mapper uses both:

| ISO 21090 code | What the message says | Class |
|---|---|---|
| NASK (not asked) | OBX-11 `N`, "not asked"; OBX-5 empty | preserved |
| every other code (ASKR, ASKU, UNK, NAV, MSK, NA, NI, OTH, INV, UNC, DER, PINF, NINF, TRC, QS) | OBX-11 `X`, "results cannot be obtained for this observation"; OBX-5 empty; an NTE after the OBX carries the ISO 21090 code and name | degraded (each merged with the others) |
| any code, on a value placed in a field rather than an observation (PID-8, OBR-25) | the field is left empty | lost |

When HL7 requires the field the value would go to (PID-3, the participant's identifier), there is no message: the
call ends as an error, `the message does not conform to HL7 v2.5.1: ... Missing required child PID.PID_3`.

## What HL7 v2 cannot say

- A general null flavor: outside an observation's result status, an Exceptional Value can only be left empty.
- Validity windows and the time a value was recorded (act, vtb, vte, tr).
- The definitions the model binds each component to, beyond a code and its coding system.
- The record's provenance and audit clusters: the message names its sending application, not the record's audit.

## Lengths

HL7 v2.5.1 states maximum lengths for coded element components, and an identifier component is shorter than an SDC
component identifier (24 characters). The local codes are written whole, since a shortened identifier would no longer
name the component; a receiver that enforces component lengths needs the local codes mapped in its own profile.

## Tests

```
pip install -e ".[dev]"
python -m pytest
```

200 NHANES Participant and 200 NHANES Medication records (a seeded sample of the FAIR Data Demo's) are mapped, and
every message validated by hl7apy; Exceptional Values and refused mappings are exercised.
