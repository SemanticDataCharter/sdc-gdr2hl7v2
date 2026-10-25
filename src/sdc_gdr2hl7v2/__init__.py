"""sdc-gdr2hl7v2: Governed Data Records as HL7 v2.5.1 messages (ER7), through sdc-mapper.

    from sdc_mapper import Engine, load_mapping
    from sdc_gdr2hl7v2 import HL7v2Mapper, mapping_path
    result = Engine().map_record(xml, HL7v2Mapper(), load_mapping(mapping_path("xy8upneajsb8vdcmnve01g6g")))

One mapping file (a site profile) per model, in `mappings/`. Registered with sdc-mapper as the target `hl7v2`.
"""
from pathlib import Path

__version__ = "4.0.3"

MAPPINGS = Path(__file__).with_name("mappings")


def mapping_path(ct_id: str) -> Path:
    """The mapping file this package publishes for a model, by the model's identifier."""
    found = sorted(MAPPINGS.glob(f"*-{ct_id}.yaml"))
    if not found:
        raise FileNotFoundError(f"sdc-gdr2hl7v2 has no mapping for model {ct_id}")
    return found[-1]


from .mapper import HL7v2Mapper  # noqa: E402

__all__ = ["HL7v2Mapper", "mapping_path", "MAPPINGS", "__version__"]
