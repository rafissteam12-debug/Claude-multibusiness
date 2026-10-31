"""Validate a CII e-invoice against the official rule sets used for XRechnung.

Three layers, mirroring what the KoSIT validator checks for XRechnung CII:
  1. XML Schema: UN/CEFACT CII D16B (from the CEN eInvoicing-EN16931 repo)
  2. CEN EN 16931 business rules (official compiled XSLT, run with Saxon HE)
  3. KoSIT XRechnung national rules (BR-DE-*, Schematron source, run with pyschematron)

Usage: python validate.py invoice.xml [--json]
Exit code 0 = no errors in any layer.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from lxml import etree

VENDOR = Path(os.environ.get("EINV_VENDOR", "/home/claude/vendor"))
KOSIT = Path(os.environ.get("EINV_KOSIT", "/home/claude/itplr-kosit/xrechnung-schematron"))

CII_XSD = VENDOR / "en16931/cii/schema/D16B SCRDM (Subset)/uncoupled clm/CII/uncefact/data/standard/CrossIndustryInvoice_100pD16B.xsd"
CEN_XSLT = VENDOR / "en16931/cii/xslt/EN16931-CII-validation.xslt"
XR_SCH = KOSIT / "src/validation/schematron/cii/XRechnung-CII-validation.sch"
XR_XSLT = Path(__file__).parent / "rules/XRechnung-CII-validation.xslt"

SVRL = "{http://purl.oclc.org/dsdl/svrl}"


def check_xsd(path: Path) -> list[dict]:
    schema = etree.XMLSchema(etree.parse(str(CII_XSD)))
    doc = etree.parse(str(path))
    if schema.validate(doc):
        return []
    return [{"layer": "XSD", "id": "XSD", "flag": "fatal", "text": str(e.message), "line": e.line}
            for e in schema.error_log]


def check_cen(path: Path) -> list[dict]:
    svrl = _run_xslt(CEN_XSLT, path)
    if not any(True for _ in svrl.iter(f"{SVRL}fired-rule")):
        raise RuntimeError("CEN rules fired on no element - stylesheet did not run against this document")
    issues = []
    for fa in svrl.iter(f"{SVRL}failed-assert"):
        text = " ".join("".join(fa.itertext()).split())
        issues.append({"layer": "EN16931", "id": fa.get("id"), "flag": fa.get("flag") or "fatal",
                       "text": text[:300], "location": fa.get("location")})
    return issues


def _run_xslt(xslt_path: Path, path: Path) -> etree._Element:
    from saxonche import PySaxonProcessor

    with PySaxonProcessor(license=False) as proc:
        exe = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(xslt_path))
        out = exe.transform_to_string(source_file=str(path))
    if not out:
        raise RuntimeError(f"{xslt_path.name} produced no output")
    root = etree.fromstring(out.encode("utf-8"))
    return root


def check_xrechnung(path: Path) -> list[dict]:
    if not XR_XSLT.exists():
        from sch2xslt import compile_schema
        XR_XSLT.parent.mkdir(exist_ok=True)
        XR_XSLT.write_text(compile_schema(XR_SCH), encoding="utf-8")
    root = _run_xslt(XR_XSLT, path)
    issues = []
    for fa in root.iter(f"{SVRL}failed-assert"):
        text = " ".join("".join(fa.itertext()).split())
        issues.append({"layer": "XRechnung", "id": fa.get("id"), "flag": fa.get("flag") or "fatal",
                       "text": text[:300], "location": fa.get("location")})
    return issues


def validate(path: Path) -> dict:
    report = {"file": str(path), "layers": {}}
    for name, fn in (("XSD", check_xsd), ("EN16931", check_cen), ("XRechnung", check_xrechnung)):
        try:
            issues = fn(path)
            report["layers"][name] = {"ran": True, "issues": issues}
        except Exception as exc:  # a layer that cannot run is reported, never silently passed
            report["layers"][name] = {"ran": False, "error": f"{type(exc).__name__}: {exc}"[:500], "issues": []}
    for layer in report["layers"].values():
        seen, unique = set(), []
        for i in layer["issues"]:
            key = (i.get("id"), i.get("location"))
            if key not in seen:
                seen.add(key); unique.append(i)
        layer["issues"] = unique
    errors = [i for layer in report["layers"].values() for i in layer["issues"]
              if (i.get("flag") or "fatal").lower() in ("fatal", "error")]
    warnings = [i for layer in report["layers"].values() for i in layer["issues"]
                if (i.get("flag") or "").lower() == "warning"]
    all_ran = all(layer["ran"] for layer in report["layers"].values())
    report["errors"] = len(errors)
    report["warnings"] = len(warnings)
    report["valid"] = all_ran and not errors
    return report


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    report = validate(Path(sys.argv[1]))
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for name, layer in report["layers"].items():
            if not layer["ran"]:
                print(f"[{name}] DID NOT RUN: {layer['error']}")
                continue
            print(f"[{name}] {len(layer['issues'])} issue(s)")
            for i in layer["issues"][:20]:
                print(f"   - {i['id']} ({i['flag']}): {i['text'][:160]}")
        print("RESULT:", "VALID" if report["valid"] else "NOT VALID",
              f"({report['errors']} errors, {report['warnings']} warnings)")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
