#!/usr/bin/env python3
"""Compare our 3-layer validation (XSD + EN16931 + XRechnung) with the official KoSIT validator
over every CII file of the official XRechnung test suite (github.com/itplr-kosit/xrechnung-testsuite).

    python ops/scripts/validate_testsuite.py --suite <checkout>/src/test [--json out.json] [--engine-kosit 3]

Needs KOSIT_VALIDATOR_JAR and KOSIT_CONFIG_DIR (see ops/scripts/fetch_tools.py) and `java` on PATH.
All suite files are official examples that are expected to be valid.

Steps:
  1. KoSIT once, as a batch over all files (direct CLI call, independent of the engine wrapper).
  2. Our 3 layers via engine.validate() with the KoSIT layer switched off.
  3. For the first N files, engine.validate() with the KoSIT layer on, to check the engine's own
     KoSIT wrapper actually runs (ran=True) and agrees with step 1.

Fails (exit 1) when:
  - KoSIT produced no report for a file, or rejected an official suite file (configuration mismatch);
  - we say valid but KoSIT says invalid (false "valid": the dangerous direction; never allowed);
  - we say invalid but KoSIT valid, unless the file is listed in ops/scripts/suite_known_diffs.txt;
  - a listed known difference no longer occurs (so the list stays honest);
  - the engine's KoSIT layer did not run or disagrees with the batch run.
Only file names and rule ids are printed; the suite files are public examples.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

KNOWN_DIFFS = Path(__file__).with_name("suite_known_diffs.txt")
OUR_LAYERS = ("XSD", "EN16931", "XRechnung")


def load_known(path: Path = KNOWN_DIFFS) -> set[str]:
    if not path.is_file():
        return set()
    return {ln.split("#", 1)[0].strip() for ln in path.read_text(encoding="utf-8").splitlines()} - {""}


def cii_files(suite: Path) -> list[Path]:
    return sorted(suite.rglob("*uncefact*.xml"))


def run_kosit_batch(files: list[Path], jar: str, config: Path) -> dict[str, dict]:
    """Run KoSIT once over all files. Returns {suite-relative name: {"ran", "errors", "accepted"}}."""
    from engine.validation import parse_kosit_report

    out: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="kosit-suite-") as tmp:
        inp, rep = Path(tmp) / "in", Path(tmp) / "out"
        inp.mkdir()
        rep.mkdir()
        alias = {}
        for i, f in enumerate(files):  # unique names: the same file name can occur in two folders
            name = f"f{i:03d}.xml"
            shutil.copyfile(f, inp / name)
            alias[name] = f
        cmd = ["java", "-jar", jar, "-s", str(config / "scenarios.xml"), "-r", str(config), "-o", str(rep),
               *[str(inp / n) for n in alias]]
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=1800, check=False)
        print(f"KoSIT batch exit code {proc.returncode} ({len(files)} files)")
        for name, f in alias.items():
            report = rep / (Path(name).stem + "-report.xml")
            if not report.is_file():
                out[str(f)] = {"ran": False, "errors": [], "accepted": False}
                continue
            errors, _warnings, accepted = parse_kosit_report(report.read_bytes())
            out[str(f)] = {"ran": True, "errors": sorted({e["id"] or "?" for e in errors}), "accepted": accepted}
        if not any(v["ran"] for v in out.values()):
            tail = (proc.stderr or b"")[-2000:].decode("utf-8", "replace")
            print("KoSIT wrote no reports. stderr tail:\n" + tail)
    return out


def ours(data: bytes, name: str) -> dict:
    from engine import validate

    saved = {k: os.environ.pop(k) for k in ("KOSIT_VALIDATOR_JAR",) if k in os.environ}
    try:
        report = validate(data, name)
    finally:
        os.environ.update(saved)
    by = {layer["name"]: layer for layer in report["layers"]}
    needed = [n for n in OUR_LAYERS if not (n == "XRechnung" and report["profile"] != "xrechnung")]
    ran = all(by.get(n, {}).get("ran") for n in needed)
    errors = sorted({e["id"] or "?" for n in needed for e in by.get(n, {}).get("errors", [])})
    return {"ran": ran, "valid": ran and not errors, "errors": errors, "profile": report["profile"]}


def engine_kosit_layer(data: bytes, name: str) -> dict:
    from engine import validate

    layer = next(lay for lay in validate(data, name)["layers"] if lay["name"] == "KoSIT")
    return {"ran": layer["ran"], "skipped_reason": layer["skipped_reason"], "errors": len(layer["errors"])}


def compare(rows: list[dict], known: set[str]) -> list[str]:
    problems = []
    seen_known = set()
    for r in rows:
        k, o, name = r["kosit"], r["ours"], r["name"]
        kosit_valid = k["ran"] and k["accepted"] and not k["errors"]
        if not k["ran"]:
            problems.append(f"{name}: KoSIT produced no report")
            continue
        if not kosit_valid:
            problems.append(f"{name}: KoSIT rejects an official suite file {k['errors']} (configuration mismatch?)")
        if o["valid"] and not kosit_valid:
            problems.append(f"{name}: FALSE VALID - we accept, KoSIT rejects")
        if not o["valid"] and kosit_valid:
            if Path(name).name in known:
                seen_known.add(Path(name).name)
            else:
                problems.append(f"{name}: we reject, KoSIT accepts; our errors {o['errors']}")
    for stale in sorted(known - seen_known):
        problems.append(f"{stale}: listed in suite_known_diffs.txt but no longer differs - remove it")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", type=Path, required=True, help="xrechnung-testsuite/src/test")
    ap.add_argument("--json", type=Path, help="write the comparison table as JSON")
    ap.add_argument("--engine-kosit", type=int, default=3, help="files to cross-check via the engine's KoSIT layer")
    ap.add_argument("--min-files", type=int, default=41)
    args = ap.parse_args(argv)

    jar = os.environ.get("KOSIT_VALIDATOR_JAR")
    cfg = os.environ.get("KOSIT_CONFIG_DIR")
    if not jar or not cfg or not Path(jar).is_file() or not (Path(cfg) / "scenarios.xml").is_file():
        print("KOSIT_VALIDATOR_JAR / KOSIT_CONFIG_DIR not set or incomplete - cannot compare (this is a failure in CI)")
        return 1
    files = cii_files(args.suite)
    if len(files) < args.min_files:
        print(f"only {len(files)} CII files found under {args.suite} (expected >= {args.min_files})")
        return 1

    kosit = run_kosit_batch(files, jar, Path(cfg))
    rows = []
    for f in files:
        name = f.relative_to(args.suite).as_posix()
        rows.append({"name": name, "kosit": kosit[str(f)], "ours": ours(f.read_bytes(), f.name)})

    problems = compare(rows, load_known())
    for r, f in list(zip(rows, files))[: max(0, args.engine_kosit)]:
        layer = engine_kosit_layer(f.read_bytes(), f.name)
        r["engine_kosit"] = layer
        kosit_ok = r["kosit"]["ran"] and r["kosit"]["accepted"] and not r["kosit"]["errors"]
        if not layer["ran"]:
            problems.append(f"{r['name']}: engine KoSIT layer did not run ({layer['skipped_reason']})")
        elif (layer["errors"] == 0) != kosit_ok:
            problems.append(f"{r['name']}: engine KoSIT layer disagrees with the batch run")

    agree = sum(1 for r in rows if r["ours"]["valid"] == (r["kosit"]["ran"] and r["kosit"]["accepted"]
                                                         and not r["kosit"]["errors"]))
    print(f"{'file':70} {'ours':8} {'KoSIT':8}")
    for r in rows:
        k = r["kosit"]
        kv = "n/a" if not k["ran"] else ("valid" if k["accepted"] and not k["errors"] else "invalid")
        print(f"{r['name'][:70]:70} {'valid' if r['ours']['valid'] else 'invalid':8} {kv:8}")
    print(f"agreement: {agree}/{len(rows)}")
    if args.json:
        args.json.write_text(json.dumps({"agreement": agree, "total": len(rows), "rows": rows,
                                         "problems": problems}, indent=2), encoding="utf-8")
    for p in problems:
        print("PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
