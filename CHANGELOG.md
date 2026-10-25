# Changelog

## 4.0.1 (2026-10-25)

Rebuilt with the release job's pip pinned by hash: CI and the release workflow install pip 26.2.2 from a hash-pinned
wheel before anything else is fetched (the eMudhra/emSign CA compromise: pip before 26.2.2 trusts the compromised root
through its vendored certifi). No change to the package.

## 4.0.0 (2026-10-25)

A target mapper of the sdc-mapper line: Governed Data Records as HL7 v2.5.1 messages in ER7.

- **The writer and the mapper.** ORU^R01: MSH from the site profile and the record (date from the record's creation
  timestamp, control ID the record's identifier, so the same record gives the same bytes); PID; one OBR group per
  section; one OBX per value, LOINC in OBX-3 where the model binds it (a lookup), the component's identifier as a
  local code otherwise; CWE for coded values with the code the model binds; UCUM units; a coded cluster as one CWE.
- **Validation independent of the writer:** every message parsed and validated by hl7apy (MIT) at its strict level
  as HL7 v2.5.1; a message that does not conform is not written.
- **Exceptional Values:** Not Asked is OBX-11 `N` (preserved); every other code OBX-11 `X` with an NTE carrying the
  ISO 21090 code (degraded); in any other field, lost.
- **Site profiles** for the FAIR Data Demo's NHANES Participant (44 rules) and NHANES Medication (18 rules) models,
  written by `tools/build_mapping.py` from specs in the models' labels. All 400 sample records map and validate.
