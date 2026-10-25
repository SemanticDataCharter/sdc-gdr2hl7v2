"""The FAIR Data Demo's NHANES Medication model as an HL7 v2.5.1 ORU^R01 message.

HL7 v2.5.1's pharmacy messages describe what a system ordered (RDE), dispensed (RDS), gave (RGV) or administered
(RAS). An NHANES medication row is none of these: it is what the participant reported taking in the past month, a
survey observation, so it is an ORU^R01 with one OBR group of observations: the drug's NHANES code (CWE, the code
system local to NHANES), its name, the days taken, the count of medicines, and each reason as an ICD-10-CM CWE.
"""
from common import C, OBS, QTY, V, coded_cluster, record

TITLE = "NHANES Medication (FAIR Data Demo) to HL7 v2.5.1 ORU^R01"
ID = "nhanes-medication-hl7v2-2.5.1"
VERSION = 1
AUTHOR = "Axius SDC, Inc."
DATE = "2026-10-25"
DESCRIPTION = ("The NHANES Medication model's values in an HL7 v2.5.1 ORU^R01 message: the participant in PID, the "
               "reported medicine as an OBR group of observations, each reason an ICD-10-CM CWE.")

RULES = [
    *record("NHANES Medication Governed Record"),
    C("NHANES Medication", "OBR"),
    # the NHANES generic drug code (Cerner Multum Lexicon, as NCHS publishes it): a code in a local system
    V("Generic Drug Code (RXDDRGID)", "OBX", "format", format="{}^^99RXD", attributes={"OBX-2": "CWE"}),
    OBS("Generic Drug Name (RXDDRUG)"),
    OBS("Taken Prescription Medicine, Past Month (RXDUSE)"),
    QTY("Number of Days Taken Medicine (RXDDAYS)"),
    QTY("Number of Prescription Medicines Taken (RXDCOUNT)"),
    *[C(f"Medication Reason {n}", ".", order=n) for n in (1, 2, 3)],
    *coded_cluster("Diagnosis (ICD-10-CM)", "I10C", "Diagnosis Code (ICD-10-CM)", "Code System: ICD-10-CM",
                   "http://hl7.org/fhir/sid/icd-10-cm"),
]
