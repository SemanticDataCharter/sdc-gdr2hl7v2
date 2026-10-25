"""Every message is checked by an implementation independent of the writer: hl7apy (MIT), parsing the message as
HL7 v2.5.1 at its strict validation level and validating it against its own 2.5.1 message structures (segment groups,
order and cardinality, required fields, datatypes and lengths). hl7apy does not check that a coded value is in its
HL7 table; the mapping file's code tables and the writer's own small tables are where that is decided."""
from __future__ import annotations


def errors(er7: str) -> list[str]:
    from hl7apy.consts import VALIDATION_LEVEL
    from hl7apy.parser import parse_message
    try:
        msg = parse_message(er7.replace("\n", "\r"), validation_level=VALIDATION_LEVEL.STRICT, find_groups=True)
        msg.validate()
    except Exception as e:  # hl7apy reports a nonconforming message by raising
        return [f"{type(e).__name__}: {e}"]
    return []
