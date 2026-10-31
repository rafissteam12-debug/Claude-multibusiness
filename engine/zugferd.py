"""build_zugferd(invoice) -> ZUGFeRD 2 / Factur-X EN16931 PDF/A-3 via Mustang.

Spike result (31 Oct 2026, see docs/progress/engine.md): the visual PDF can be
made PDF/A-3b and approved locally (reportlab + pikepdf.pdfa), but the hybrid
with the embedded XML cannot be verified locally (no veraPDF/Mustang here;
pikepdf's allowlist validator does not support embedded files or XMP extension
schemas). An unverified file must not be offered, so:

- MUSTANG_JAR set:   Mustang CLI combines the PDF/A-3b base with the EN16931 XML
                     and then validates the result; only a "valid" result is returned.
- MUSTANG_JAR unset: FeatureUnavailable.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from contracts.types import FeatureUnavailable

from .cii import build_cii
from .inputcheck import check_invoice
from .pdf import render_pdfa3b

UNAVAILABLE = "ZUGFeRD (PDF/A-3) ist in dieser Installation nicht verfügbar: Mustang fehlt (MUSTANG_JAR)."


def _run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, timeout=300, check=False)


def build_zugferd(invoice: dict) -> bytes:
    check_invoice(invoice, "zugferd")  # input errors first, independent of installed tools
    jar = os.environ.get("MUSTANG_JAR")
    if not jar or not Path(jar).is_file():
        raise FeatureUnavailable(UNAVAILABLE)
    try:
        base = render_pdfa3b(invoice)
    except ImportError as exc:
        raise FeatureUnavailable("PDF/A-Basis nicht möglich: pikepdf[pdfa] fehlt.") from exc
    xml = build_cii(invoice, profile="zugferd")
    with tempfile.TemporaryDirectory(prefix="zf-") as tmp:
        (Path(tmp) / "base.pdf").write_bytes(base)
        (Path(tmp) / "factur-x.xml").write_bytes(xml)
        out = Path(tmp) / "out.pdf"
        r = _run(["java", "-jar", jar, "--action", "combine", "--source", "base.pdf", "--source-xml", "factur-x.xml",
                  "--out", "out.pdf", "--format", "zf", "--version", "2", "--profile", "E",
                  "--no-additional-attachments"], tmp)
        if r.returncode != 0 or not out.is_file():
            raise FeatureUnavailable("ZUGFeRD-Erzeugung mit Mustang fehlgeschlagen.")
        v = _run(["java", "-jar", jar, "--action", "validate", "--source", "out.pdf"], tmp)
        if not re.search(rb'<summary\s+status="valid"', v.stdout or b""):
            raise FeatureUnavailable("ZUGFeRD-Datei hat die Mustang-Prüfung (PDF/A-3 und XML) nicht bestanden.")
        return out.read_bytes()
