"""The FAIR Data Demo's NHANES Medication 4.3.0 model as an HL7 v2.5.1 ORU^R01 message.

4.3.0 adds two things to the medication record. A reason is either an ICD-10-CM diagnosis or one of NHANES's
prevention reason codes, an ICD-10-CM code with "P" appended (I21.P, prevent heart attack), which is not ICD-10-CM: it
goes out as a CWE in a coding system local to NHANES (99NHANES, HL7 table 0396's 99zzz), never I10C. And NHANES's
55555 (unknown), 77777 (refused) and 99999 (don't know) are Exceptional Values: the drug name, the days taken or a
reason's code that is one is sent with OBX-5 empty, OBX-11 X and an NTE naming the ISO 21090 code.
"""
from common import coded_cluster
from nhanes_medication import AUTHOR, VERSION  # noqa: F401
from nhanes_medication import RULES as _RULES

TITLE = "NHANES Medication 4.3.0 (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-medication-4.3.0-hl7v2-2.5.1"
DATE = "2026-10-27"
DESCRIPTION = ("The NHANES Medication 4.3.0 model's values in an HL7 v2.5.1 ORU^R01 message: the reported medicine as an "
               "OBR group of observations; each reason an ICD-10-CM CWE (I10C) or an NHANES prevention reason CWE "
               "(99NHANES, not ICD-10-CM); an unknown, refused or don't-know value as OBX-5 empty with OBX-11 X.")
NHANES_RX = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/RXQ_RX_J.htm"
RULES = _RULES + coded_cluster("Prevention Reason (NHANES)", "99NHANES", "Prevention Reason Code (NHANES)",
                               "Code System: NHANES Prevention Reason", NHANES_RX)
