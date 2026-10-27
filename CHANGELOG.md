# Changelog

## 4.0.6 (2026-10-27)

- **FAIR Data Demo 4.3.1:** NHANES Participant 4.3.1 (`fafj69kdii37997sy7dpsz13`): its mapping and a sample of the
  same 200 participants as the 4.3.0 sample. 4.3.1's four NIH CDE answers carry their compound concept as
  `dcterms:subject` parts, with no exact-match claim (NIH CDE library R-2026-10-27). OBX-3 reads only a component's
  LOINC exact match, and those concepts are NCI Thesaurus, so no message changes: a new test holds that every 4.3.1
  message is the 4.3.0 one apart from identifiers. Every message passes strict hl7apy validation. The 4.3.0 mapping
  stays, for records made on that model.

## 4.0.5 (2026-10-27)

Site profiles for the FAIR Data Demo 4.3.0 models, NHANES Participant 4.3.0 (`drjvqb171q9pqwcdq6nxxrr4`) and NHANES
Medication 4.3.0 (`plc9gto1kzy244g1r2op257f`), whose refused and don't-know answers are Exceptional Values (ASKR, ASKU;
the medication file's 55555, 77777 and 99999 are UNK, ASKR and ASKU).

- **An Exceptional Value is never sent as an answer.** An observation whose answer is one goes out with OBX-5 empty,
  OBX-11 `X` (table 0085, "results cannot be obtained") and an NTE naming the ISO 21090 code; Not Asked is OBX-11 `N`.
- **Fix: a coded cluster's answer.** A cluster held as one CWE (a code, its text and its system) whose code was an
  Exceptional Value went out as a partial CWE: a medication reason NHANES records as unknown was `^^I10C` with status
  `F`, an empty ICD-10-CM answer presented as final (27 in the 200-record sample). It is now OBX-5 empty, OBX-11 `X`
  and the NTE, as any exceptional answer.
- **NHANES's prevention reason codes are not ICD-10-CM.** `I21.P` (prevent heart attack) goes out as a CWE in a coding
  system local to NHANES, `99NHANES` (table 0396's 99zzz), never `I10C`.
- Samples: the 4.2.4 sample's 200 participants on 4.3.0 (16 with an Exceptional Value), and 200 medication records
  (47 with a prevention code, 44 with an Exceptional Value). Every message passes strict hl7apy validation. The earlier
  mappings and samples stay: records made on the retired models still map.

## 4.0.4 (2026-10-26)

A site profile for NHANES Participant 4.2.4 (`tp5pg0u4dasqarie0b3ujn2u`), the FAIR Data Demo's revision whose value
bindings name codes their terminologies confirm (its E-2026-10-03). For the same participant, OBX-5 now carries:

| Observation | 4.2.3 | 4.2.4 |
|---|---|---|
| Difficulty scale (PFQ061B to PFQ061M), "No difficulty" | `C17998` (NCIt Unknown) | `C121736` Can Do Without Any Difficulty |
| Pregnancy Status at Exam, "Not pregnant at exam" | `C25191` (NCIt Person Name) | `C82475` Not Pregnant |
| Citizenship Status, "Citizen by birth or naturalization" | `C41130` (NCIt Significant) | `C90516` Citizen |
| Race/Hispanic Origin, "Mexican American" | `C67175` (NCIt DBVE-PC Regimen) | `C67114` Mexican American |
| Education, "College graduate or above" | `C39303` (NCIt Active Funded Research Project) | `C159746` College Completion |

Where no concept says exactly what a value says ("Not a citizen of the US", "Less than 9th grade", "Do not do this
activity"), the 4.2.4 model defines the value by the NHANES codebook page, and OBX-5 carries its text with no identifier
and no coding system: a codebook page is not a code. A new test holds every participant sample to that, and to every
coded OBX-5 being a LOINC, SNOMED CT or NCIt code under its own system.

- `nhanes_participant_424-tp5pg0u4dasqarie0b3ujn2u.yaml`, 44 rules, from `tools/specs/nhanes_participant_424.py`
  (the 4.2.0 spec's rules: every label is the same).
- `samples/nhanes-participant-4.2.4/`: the model's schema and 200 records, the same participants as the 4.2.3 sample.
- The 4.2.0 and 4.2.3 mappings and samples stay, for records made on those models; both models are retired.

## 4.0.3 (2026-10-25)

A site profile for NHANES Participant 4.2.3 (`eehpfapwgvxtzdrofgstdcfs`), the FAIR Data Demo's revision of NHANES
Participant that composes the NIH CDE library's correction E-2026-10-01. The NIH CDE Repository's record for "Are you
pregnant now?" (`LiUWCWluP`) bound each answer to the next one's LOINC code; on the 4.2.3 model the OBX-5 for that
question is Yes `LA15173-0`, No `LA26683-5`, Unknown `LA4489-6`, where the 4.2.0 model's records send `LA26683-5` for
Yes, `LA4489-6` for No and `LA15173-0` for Unknown.

- `nhanes_participant_423-eehpfapwgvxtzdrofgstdcfs.yaml`, 44 rules, written by `tools/build_mapping.py` from
  `tools/specs/nhanes_participant_423.py` (the 4.2.0 spec's rules: every label is the same).
- A sample of 200 records on the 4.2.3 model, the same participants as the 4.2.0 sample; all map and validate.
- The 4.2.0 model's site profile and sample stay: its records are published and keep their meaning as written.

## 4.0.2 (2026-10-25)

Uses sdc-mapper 4.3.0's code reading (`sdc_mapper.codes`): the LOINC code a component links to and the code an
enumerated value is defined by are read by the core, and this package keeps only HL7 table 0396's names for the code
systems (LN, SCT, NCIT). No change to any output: every sample message is byte-identical, and every value's class in
the report is the same. Requires sdc-mapper 4.3.

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
