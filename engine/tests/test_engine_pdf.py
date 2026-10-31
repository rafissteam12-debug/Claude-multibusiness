"""render_pdf, PDF/A-3b base, build_zugferd (Mustang optional), CLI wrappers."""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import engine
from engine import FeatureUnavailable, InvoiceInputError, build_zugferd, render_pdf
from engine import zugferd as Z

ROOT = Path(__file__).resolve().parents[2]


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_render_pdf_readable_german(sample):
    pdf = render_pdf(sample())
    assert pdf.startswith(b"%PDF-")
    text = _text(pdf)
    for needle in ("Rechnung", "RE-2026-0418", "Käuferreferenz", "Einzelpreis", "Gesamtbetrag", "7.207,50 €",
                   "IBAN DE89370400440532013000", "Zahlbar bis 09.11.2026"):
        assert needle in text, needle


def test_render_pdf_credit_note_and_long_invoice(sample):
    inv = sample()
    inv["type_code"] = "381"
    inv["preceding_invoice"] = {"number": "RE-2026-0400"}
    inv["lines"] = inv["lines"] * 40  # forces several pages
    text = _text(render_pdf(inv))
    assert "Gutschrift" in text and "RE-2026-0400" in text and "Seite 2" in text


def test_render_pdf_rejects_bad_input(sample):
    inv = sample()
    del inv["lines"]
    with pytest.raises(InvoiceInputError):
        render_pdf(inv)


def test_pdfa3b_base_passes_allowlist_validator(sample):
    pdfa = pytest.importorskip("pikepdf.pdfa")
    from engine.pdf import render_pdfa3b
    data = render_pdfa3b(sample())
    assert pdfa.validate_written(io.BytesIO(data), "3b").passed


def test_zugferd_unavailable_without_mustang(sample):
    with pytest.raises(FeatureUnavailable):
        build_zugferd(sample())


def test_zugferd_input_errors_before_feature_check(sample):
    inv = sample()
    del inv["payment"]
    with pytest.raises(InvoiceInputError):
        build_zugferd(inv)


def test_zugferd_with_mustang_commands(sample, tmp_path, monkeypatch):
    pytest.importorskip("pikepdf.pdfa")
    jar = tmp_path / "Mustang-CLI.jar"
    jar.write_bytes(b"fake")
    monkeypatch.setenv("MUSTANG_JAR", str(jar))
    calls = []

    def fake_run(cmd, cwd):
        calls.append(cmd)
        if "combine" in cmd:
            assert (Path(cwd) / "base.pdf").read_bytes().startswith(b"%PDF-")
            assert b"urn:cen.eu:en16931:2017<" in (Path(cwd) / "factur-x.xml").read_bytes()
            (Path(cwd) / "out.pdf").write_bytes(b"%PDF-1.7 fake")
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        return subprocess.CompletedProcess(cmd, 0, b'<validation><summary status="valid"/></validation>', b"")

    monkeypatch.setattr(Z, "_run", fake_run)
    assert build_zugferd(sample()) == b"%PDF-1.7 fake"
    assert [c[4] for c in calls] == ["combine", "validate"]
    assert {"--format", "zf", "--profile", "E"} <= set(calls[0])

    monkeypatch.setattr(Z, "_run", lambda cmd, cwd: fake_run(cmd, cwd) if "combine" in cmd
                        else subprocess.CompletedProcess(cmd, 1, b'<summary status="invalid"/>', b""))
    with pytest.raises(FeatureUnavailable):
        build_zugferd(sample())


def test_cli_generate_and_validate(tmp_path):
    out = tmp_path / "r.xml"
    sample = ROOT / "engine/samples/schreinerei.json"
    r = subprocess.run([sys.executable, str(ROOT / "engine/generate.py"), str(sample), str(out), "--pdf"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.is_file() and out.with_suffix(".pdf").is_file()
    r = subprocess.run([sys.executable, str(ROOT / "engine/validate.py"), str(out), "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["valid"] is True
    bad = tmp_path / "bad.json"
    inv = json.loads(sample.read_text(encoding="utf-8"))
    del inv["buyer_reference"]
    bad.write_text(json.dumps(inv), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "engine/generate.py"), str(bad), str(tmp_path / "b.xml")],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "/buyer_reference" in r.stdout


def test_package_attribute_validate_is_function():
    assert callable(engine.validate)
