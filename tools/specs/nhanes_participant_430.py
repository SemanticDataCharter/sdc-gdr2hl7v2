"""The FAIR Data Demo's NHANES Participant 4.3.0 model as an HL7 v2.5.1 ORU^R01 message.

4.3.0 republishes every answer that can be refused or not known under SDCStudio 4.24, so an Exceptional Value can
stand in place of the value: NHANES's refused (7, 77, 777) and don't know (9, 99, 999) are ASKR and ASKU. An observation
whose value is one is sent with OBX-5 empty, OBX-11 `X` and an NTE naming the ISO 21090 code. Every label is the same,
so the rules are the 4.2.0 model's; the mapping is its own, bound to the 4.3.0 model's schema.
"""
from nhanes_participant import *  # noqa: F401,F403
from nhanes_participant import RULES  # noqa: F401

TITLE = "NHANES Participant 4.3.0 (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-participant-4.3.0-hl7v2-2.5.1"
DATE = "2026-10-27"
DESCRIPTION = ("The NHANES Participant 4.3.0 model's values in an HL7 v2.5.1 ORU^R01 message: the participant in PID, "
               "each section an OBR group, each value an OBX. A refused or unknown answer is an OBX with OBX-5 empty, "
               "OBX-11 X and an NTE naming the ISO 21090 code.")
