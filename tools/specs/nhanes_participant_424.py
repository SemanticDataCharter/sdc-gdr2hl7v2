"""The FAIR Data Demo's NHANES Participant 4.2.4 model as an HL7 v2.5.1 ORU^R01 message.

The 4.2.4 model is a revision of NHANES Participant 4.2.3 whose value bindings and concept links name codes their
terminologies confirm (the FAIR Data Demo's E-2026-10-03): the difficulty scale, pregnancy at exam, citizenship,
education, race and the SI cholesterol link, among others. Where no concept says exactly what a value says, the value is
defined by the NHANES codebook page instead, and carries no code. Every label is the same, so the rules are the 4.2.0
model's; the mapping is its own, bound to the 4.2.4 model's schema.
"""
from nhanes_participant import *  # noqa: F401,F403
from nhanes_participant import RULES  # noqa: F401

TITLE = "NHANES Participant 4.2.4 (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-participant-4.2.4-hl7v2-2.5.1"
DESCRIPTION = ("The NHANES Participant 4.2.4 model's values in an HL7 v2.5.1 ORU^R01 message: the participant in PID, "
               "each section an OBR group, each value an OBX. OBX-3 is the LOINC code the model binds where it binds one.")
