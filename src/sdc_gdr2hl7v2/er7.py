"""ER7, HL7 v2's pipe-and-hat encoding: segments of fields, fields of components, components of subcomponents.

A field address is `n`, `n.m` or `n.m.s` (field, component, subcomponent), 1-based as HL7 numbers them. Values are
escaped on the way in; constants a mapping file declares (`^^^NHANES^PI`) are written as given, so a profile can state
a structured field.
"""
from __future__ import annotations

FIELD, COMPONENT, REPETITION, ESCAPE, SUBCOMPONENT = "|", "^", "~", "\\", "&"
ENCODING = COMPONENT + REPETITION + ESCAPE + SUBCOMPONENT


def escape(text: str) -> str:
    """A value as ER7 text: the delimiters it contains written as HL7's escape sequences."""
    out = text.replace(ESCAPE, "\\E\\")
    for ch, seq in ((FIELD, "\\F\\"), (COMPONENT, "\\S\\"), (SUBCOMPONENT, "\\T\\"), (REPETITION, "\\R\\")):
        out = out.replace(ch, seq)
    return out.replace("\r", "\\X0D\\").replace("\n", "\\X0A\\")


def address(addr: str) -> tuple[int, int | None, int | None]:
    parts = [int(p) for p in addr.split(".")]
    if not 1 <= len(parts) <= 3 or any(p < 1 for p in parts):
        raise ValueError(f"not a field address: {addr!r}")
    return parts[0], parts[1] if len(parts) > 1 else None, parts[2] if len(parts) > 2 else None


class Segment:
    """One segment: its fields by number, each held as raw ER7 text or as components set one by one."""

    def __init__(self, name: str):
        self.name = name
        self.fields: dict[int, list[list[str]]] = {}     # field -> components -> subcomponents

    def has(self, addr: str) -> bool:
        f, c, s = address(addr)
        comps = self.fields.get(f)
        if comps is None:
            return False
        if c is None:
            return any(any(sub) for sub in comps)
        if c > len(comps):
            return False
        if s is None:
            return any(comps[c - 1])
        return s <= len(comps[c - 1]) and comps[c - 1][s - 1] != ""

    def set(self, addr: str, raw: str) -> None:
        """Set ER7 text (already escaped, or a declared structure) at a field address. Setting a field replaces it."""
        f, c, s = address(addr)
        if c is None:
            self.fields[f] = [comp.split(SUBCOMPONENT) for comp in raw.split(COMPONENT)]
            return
        comps = self.fields.setdefault(f, [[""]])
        while len(comps) < c:
            comps.append([""])
        if s is None:
            comps[c - 1] = raw.split(SUBCOMPONENT)
            return
        subs = comps[c - 1]
        while len(subs) < s:
            subs.append("")
        subs[s - 1] = raw

    def er7(self) -> str:
        if self.name == "MSH":                 # MSH-1 is the field separator itself, MSH-2 the encoding characters
            rest = {k: v for k, v in self.fields.items() if k > 2}
            return "MSH" + FIELD + ENCODING + self._join(rest, start=3)
        return self.name + self._join(self.fields, start=1)

    @staticmethod
    def _join(fields: dict, start: int) -> str:
        if not fields:
            return ""
        out = []
        for n in range(start, max(fields) + 1):
            comps = fields.get(n, [[""]])
            text = COMPONENT.join(SUBCOMPONENT.join(subs).rstrip(SUBCOMPONENT) for subs in comps).rstrip(COMPONENT)
            out.append(text)
        return FIELD + FIELD.join(out)


def message(segments: list[Segment]) -> str:
    return "\r".join(s.er7() for s in segments) + "\r"
