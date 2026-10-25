"""The FAIR Data Demo's NHANES Participant 4.2.3 model as an HL7 v2.5.1 ORU^R01 message.

The 4.2.3 model is a revision of NHANES Participant (4.2.0) whose only change is the NIH CDE "Are you pregnant now?"
it composes: the NIH CDE library's correction E-2026-10-01, whose answers carry the right LOINC codes (Yes LA15173-0,
No LA26683-5, Unknown LA4489-6). Every label is the same, so the rules are the 4.2.0 model's; the mapping is its own,
bound to the 4.2.3 model's schema.
"""
from nhanes_participant import *  # noqa: F401,F403
from nhanes_participant import RULES  # noqa: F401

TITLE = "NHANES Participant 4.2.3 (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-participant-4.2.3-hl7v2-2.5.1"
DESCRIPTION = ("The NHANES Participant 4.2.3 model's values in an HL7 v2.5.1 ORU^R01 message: the participant in PID, "
               "each section an OBR group, each value an OBX. OBX-3 is the LOINC code the model binds where it binds one.")
