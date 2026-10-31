"""Value shapes for the AI data rule: letters -> X/x, digits -> d, everything else kept."""
from __future__ import annotations


def value_shape(value: str) -> str:
    """'Müller GmbH' -> 'Xxxxxx XxxX', '31.10.2026' -> 'dd.dd.dddd'."""
    out = []
    for ch in value:
        if ch.isdigit():
            out.append("d")
        elif ch.isalpha():
            out.append("X" if ch.isupper() else "x")
        else:
            out.append(ch)
    return "".join(out)
