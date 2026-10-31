"""CLI: validate an e-invoice (CII XML or PDF with embedded CII).

usage: python engine/validate.py invoice.xml [--json]
Exit code 0 = valid per the validity rule in contracts/mapping.md.
Thin wrapper around `engine.validate`. Do not import this file as a module.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

import engine  # noqa: E402


def main(argv: list[str]) -> int:
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    path = Path(files[0])
    report = engine.validate(path.read_bytes(), path.name)
    if "--json" in argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for layer in report["layers"]:
            if not layer["ran"]:
                print(f"[{layer['name']}] NICHT GELAUFEN: {layer['skipped_reason']}")
                continue
            print(f"[{layer['name']}] {len(layer['errors'])} Fehler, {len(layer['warnings'])} Warnungen")
            for i in layer["errors"][:20]:
                print(f"   - {i['id']}: {i['message_de'][:160]}")
        print("ERGEBNIS:", "GÜLTIG" if report["valid"] else "NICHT GÜLTIG", f"(Profil {report['profile']})")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
