#!/usr/bin/env python3
"""Verify the engine's Mustang path (engine request 6) with the pinned Mustang CLI.

    python ops/scripts/check_mustang.py [--out DIR]

Needs MUSTANG_JAR and `java`. For each fictional sample in engine/samples/*.json:
  1. engine.build_zugferd(invoice) must return a PDF (the engine only returns it when Mustang's
     validate step says status="valid");
  2. on failure, the same Mustang commands the engine uses are re-run here with output captured,
     so the CI log shows which flag or step failed (samples are fictional, so printing is allowed).
Exit 0 = all samples produced a validated ZUGFeRD file.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def diagnose(invoice: dict, jar: str) -> None:
    from engine import build_cii
    from engine.pdf import render_pdfa3b

    with tempfile.TemporaryDirectory(prefix="zf-diag-") as tmp:
        (Path(tmp) / "base.pdf").write_bytes(render_pdfa3b(invoice))
        (Path(tmp) / "factur-x.xml").write_bytes(build_cii(invoice, profile="zugferd"))
        steps = [
            ["java", "-jar", jar, "--action", "combine", "--source", "base.pdf", "--source-xml", "factur-x.xml",
             "--out", "out.pdf", "--format", "zf", "--version", "2", "--profile", "E", "--no-additional-attachments"],
            ["java", "-jar", jar, "--action", "validate", "--source", "out.pdf"],
        ]
        for cmd in steps:
            r = subprocess.run(cmd, cwd=tmp, stdin=subprocess.DEVNULL, capture_output=True, timeout=300, check=False)
            print(f"  $ {' '.join(cmd[3:])}\n  exit {r.returncode}")
            for label, stream in (("stdout", r.stdout), ("stderr", r.stderr)):
                text = (stream or b"")[-1500:].decode("utf-8", "replace").strip()
                if text:
                    print(f"  --- {label} (tail)\n" + "\n".join("  " + ln for ln in text.splitlines()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, help="keep the generated PDFs here (CI artifact)")
    args = ap.parse_args(argv)
    jar = os.environ.get("MUSTANG_JAR")
    if not jar or not Path(jar).is_file():
        print("MUSTANG_JAR not set or missing - cannot check (this is a failure in CI)")
        return 1
    from engine import FeatureUnavailable, build_zugferd

    samples = sorted((ROOT / "engine" / "samples").glob("*.json"))
    if not samples:
        print("no samples in engine/samples")
        return 1
    failed = 0
    for s in samples:
        invoice = json.loads(s.read_text(encoding="utf-8"))
        try:
            pdf = build_zugferd(invoice)
        except FeatureUnavailable as exc:
            failed += 1
            print(f"FAIL {s.name}: {exc}")
            diagnose(invoice, jar)
            continue
        print(f"ok   {s.name}: {len(pdf)} bytes, Mustang status valid")
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / (s.stem + ".zugferd.pdf")).write_bytes(pdf)
    print(f"check_mustang: {len(samples) - failed}/{len(samples)} ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
