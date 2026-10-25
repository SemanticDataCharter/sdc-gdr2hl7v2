"""Rules both NHANES models share: the record's own clusters, the participant identifier, units, coded clusters.

Labels are the model's; `to` is HL7 v2: a cluster to MSH, OBR, OBX, '.' or omit; a component to OBX (an observation
of its own) or to a field (PID-3, OBR-25, OBX-5.1, OBX*-11 for every OBX in the group).
"""

#: The Default and FAIR libraries' unit symbols in UCUM (HL7 table 0396 "UCUM"), for OBX-6. Most are UCUM already;
#: the rest are written as UCUM writes them (mm[Hg]) or as UCUM annotations ({items}).
UCUM = {"%": "%", "/100{WBCs}": "/100{WBCs}", "/min": "/min", "1": "1", "10*3/uL": "10*3/uL", "10*6/uL": "10*6/uL",
        "cigarettes": "{cigarettes}", "fL": "fL", "g/dL": "g/dL", "items": "{items}", "mg/dL": "mg/dL",
        "mmHg": "mm[Hg]", "mmol/L": "mmol/L", "months": "mo", "pg": "pg", "years": "a", "days": "d"}
UNITS = {"units": {"to": "@6", "transform": "code", "table": UCUM}}

#: The site profile: what the sending side states once, as constants, on the record's MSH rule.
SITE = {
    "MSH-3": "SDC-GDR2HL7V2",            # sending application
    "MSH-4": "FAIR Data Demo",           # sending facility
    "MSH-11": "T",                       # processing ID (table 0103): T, training; the demo's data is not clinical care
    "PID-5": '""',                       # patient name, required; NHANES publishes none, so an explicit null
    "OBX-11": "F",                       # result status (table 0085) where the record states none: a public release
}


def C(label, to, **kw):
    return {"cluster": label, "to": to, **kw}


def V(label, to="OBX", transform="copy", **kw):
    return {"component": label, "to": to, "transform": transform, **kw}


def OMIT_C(label, reason, **kw):
    return {"cluster": label, "to": "-", "transform": "omit", "reason": reason, **kw}


def OBS(label, **kw):
    """An observation of its own: OBX-3 is the LOINC code the model binds, or the component's identifier."""
    return V(label, "OBX", **kw)


def QTY(label, **kw):
    return V(label, "OBX", **UNITS, **kw)


def record(governed: str):
    return [
        C(governed, "MSH", attributes=SITE),
        OMIT_C("Audit Event", "the record's audit event: an HL7 v2 message names its sending application, not the "
                              "audit of the record"),
        OMIT_C("PROV Activity", "the record's provenance: HL7 v2 has no place for it"),
        OMIT_C("PROV Agent", "the record's provenance: HL7 v2 has no place for it"),
        OMIT_C("PROV Entity", "the record's provenance: HL7 v2 has no place for it"),
        V("Respondent Sequence Number (SEQN)", "PID-3", "format", format="{}^^^NHANES^PI"),
    ]


def coded_cluster(cluster: str, system: str, code: str, system_label: str, system_iri: str):
    """A code, its display text and its system, held by the record as three values: one CWE in one OBX."""
    return [
        C(cluster, "OBX", attributes={"OBX-2": "CWE", "OBX-5.3": system}),
        V(code, "OBX-5.1"),
        V("Code Display Text", "OBX-5.2", within=[cluster]),
        V(system_label, "OBX-5.3", "code", table={system_iri: system}, on_miss="omit"),
    ]
