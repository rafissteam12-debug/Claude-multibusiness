"""CLI: invoice JSON -> XRechnung 3.0 CII XML (and optionally a readable PDF).

usage: python engine/generate.py input.json output.xml [--pdf] [--profile xrechnung|zugferd]

Thin wrapper around the `engine` package (build_cii, render_pdf). The tool is a
technical converter: VAT category and rate come from the input and must be
confirmed by the customer or their tax adviser.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for `engine` and `contracts`

from engine import InvoiceInputError, build_cii, compute_totals, render_pdf  # noqa: E402
from engine.inputcheck import check_invoice  # noqa: E402


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    profile = argv[argv.index("--profile") + 1] if "--profile" in argv else "xrechnung"
    args = [a for a in args if a != profile]
    inv = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    try:
        xml = build_cii(inv, profile=profile)
    except InvoiceInputError as exc:
        for e in exc.errors:
            print(f"  {e.field}: {e.message_de} [{e.code}]")
        return 1
    out = Path(args[1])
    out.write_bytes(xml)
    t = compute_totals(check_invoice(inv, profile))
    print(f"wrote {out}  net {t['net']}  VAT {t['vat']}  gross {t['gross']}")
    if "--pdf" in argv:
        out.with_suffix(".pdf").write_bytes(render_pdf(inv))
        print(f"wrote {out.with_suffix('.pdf')} (readable PDF, not an e-invoice)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
