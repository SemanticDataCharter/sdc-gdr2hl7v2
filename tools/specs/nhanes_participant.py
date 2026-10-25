"""The FAIR Data Demo's NHANES Participant model as an HL7 v2.5.1 ORU^R01 message.

Each study section is an order group (OBR), each answer and measurement an observation (OBX); the blood pressure
readings are a group each, their status the group's result status. The participant identifier is PID-3, the
administrative gender PID-8; everything the person answered or was measured for is an OBX, coded by LOINC where the
model binds the component to LOINC, and otherwise by the component's own identifier.
"""
from common import UCUM, C, QTY, V, coded_cluster, record

TITLE = "NHANES Participant (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-participant-hl7v2-2.5.1"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The NHANES Participant model's values in an HL7 v2.5.1 ORU^R01 message: the participant in PID, each "
               "section an OBR group, each value an OBX. OBX-3 is the LOINC code the model binds where it binds one.")

#: FHIR observation status (the Blood Pressure component's list) as HL7 v2 result status: OBR-25 (table 0123) and
#: OBX-11 (table 0085). A status with no counterpart is left out, with the reason.
OBR_STATUS = {"registered": "I", "preliminary": "P", "final": "F", "amended": "C", "corrected": "C", "cancelled": "X"}
OBX_STATUS = {"registered": "I", "preliminary": "P", "final": "F", "amended": "C", "corrected": "C",
              "cancelled": "X", "entered-in-error": "W"}
SEX = {"female": "F", "male": "M", "other": "O", "unknown": "U"}   # HL7 table 0001

GROUPS = ["NHANES Blood Pressure", "NHANES Demographics", "NHANES Laboratory Results", "NHANES Medical Conditions",
          "NHANES Physical Functioning", "NHANES Smoking", "NHANES Survey Design"]

QUANTITIES = ["Diastolic Blood Pressure", "Systolic Blood Pressure", "Maximum Inflation Level (BPXML1)", "Heart Rate",
              "Age in Months at Screening (RIDAGEMN)", "Total Number of People in the Household (DMDHHSIZ)", "Age",
              "Ratio of Family Income to Poverty (INDFMPIR)", "Age Started Smoking Cigarettes Regularly (SMD030)",
              "Average Cigarettes per Day, Past 30 Days (SMD650)", "Masked Variance Pseudo-PSU (SDMVPSU)",
              "Masked Variance Pseudo-Stratum (SDMVSTRA)", "Full Sample 2 Year Interview Weight (WTINT2YR)",
              "Full Sample 2 Year MEC Exam Weight (WTMEC2YR)"]

RULES = [
    *record("NHANES Participant Governed Record"),
    C("NHANES Participant", "."),
    *[C(g, "OBR") for g in GROUPS],
    *[C(f"Blood Pressure Reading {n}", "OBR", order=n) for n in (1, 2, 3)],
    C("Blood Pressure", "."),
    C("Chronic Condition Indicators", "."),
    *coded_cluster("Body Site (SNOMED CT)", "SCT", "Body Site Code (SNOMED CT)", "Code System: SNOMED CT",
                   "http://snomed.info/sct"),
    V("Observation Status", "OBR-25", "code", table=OBR_STATUS, on_miss="omit",
      also=[{"to": "OBX*-11", "transform": "code", "table": OBX_STATUS, "on_miss": "omit"}]),
    V("Observation Date Time", "OBR-7", also=[{"to": "OBX*-14", "transform": "copy"}]),
    V("Administrative Gender", "PID-8", "code", table=SEX),
    # every other value: an observation (the builder's completeness check names any left out)
    *[QTY(q) for q in QUANTITIES],
    {"sdc_type": "XdQuantity", "to": "OBX", "transform": "copy", "units": {"to": "@6", "transform": "code",
                                                                           "table": UCUM}},
    {"sdc_type": "XdCount", "to": "OBX", "transform": "copy", "units": {"to": "@6", "transform": "code",
                                                                        "table": UCUM}},
    {"sdc_type": "XdToken", "to": "OBX", "transform": "copy"},
    {"sdc_type": "XdString", "to": "OBX", "transform": "copy"},
    {"sdc_type": "XdTemporal", "to": "OBX", "transform": "copy"},
]
