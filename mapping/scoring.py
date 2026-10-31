"""Score a proposed Mapping against a ground-truth expected_mapping.json.

A field counts as correct when the proposal has the same target with the same source column
(or the same constant) and the same transform list. Grouping mode counts as one extra item
of the required score.

    python -m mapping.scoring            # per-fixture table for the heuristic provider
"""
from __future__ import annotations

import json
from pathlib import Path

from .targets import REQUIRED_TARGETS

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _key(f: dict) -> tuple:
    if "constant" in f and f.get("source_column") is None:
        return ("const", str(f["constant"]))
    return ("col", f.get("source_column"), tuple(f.get("transform") or []))


def score(proposal: dict, expected: dict) -> dict:
    got = {f["target"]: _key(f) for f in proposal.get("fields", [])}
    exp = {f["target"]: _key(f) for f in expected["fields"]}
    required = [t for t in REQUIRED_TARGETS if t in exp]
    req_ok = [t for t in required if got.get(t) == exp[t]]
    mode_ok = proposal.get("grouping", {}).get("mode") == expected["grouping"]["mode"]
    all_ok = [t for t in exp if got.get(t) == exp[t]]
    extra = sorted(t for t in got if t not in exp)
    return {
        "required_score": (len(req_ok) + mode_ok) / (len(required) + 1),
        "all_score": len(all_ok) / len(exp) if exp else 1.0,
        "required_wrong": [t for t in required if t not in req_ok] + ([] if mode_ok else ["grouping.mode"]),
        "all_wrong": [t for t in exp if t not in all_ok],
        "extra_targets": extra,
    }


def expected_for(fixture: str) -> dict:
    return json.loads((FIXTURES_DIR / (Path(fixture).stem + ".expected_mapping.json")).read_text(encoding="utf-8"))


def seller_profile() -> dict:
    return json.loads((FIXTURES_DIR / "seller_profile.json").read_text(encoding="utf-8"))


def main() -> None:
    from . import propose, read_table
    from .fixtures.make_fixtures import FIXTURES
    print(f"{'fixture':24} {'required':>9} {'all fields':>11}  wrong")
    for name in FIXTURES:
        table = read_table((FIXTURES_DIR / name).read_bytes(), name)
        s = score(propose(table, seller_profile()), expected_for(name))
        print(f"{name:24} {s['required_score']:>8.0%} {s['all_score']:>10.0%}  {', '.join(s['all_wrong']) or '-'}")


if __name__ == "__main__":
    main()
