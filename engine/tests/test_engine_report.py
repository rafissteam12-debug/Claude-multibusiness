"""Report shape (contracts/mapping.md), validity rule, KoSIT layer, German messages."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from engine import build_cii, validate
from engine import validation as V
from engine.messages_de import MESSAGES_DE

RULES = Path(V.__file__).parent / "rules"


def _check_shape(report):
    assert set(report) == {"valid", "profile", "guideline_id", "layers", "totals_warning"}
    assert isinstance(report["valid"], bool)
    assert report["profile"] in ("xrechnung", "zugferd", "unknown")
    assert report["guideline_id"] is None or isinstance(report["guideline_id"], str)
    names = [l["name"] for l in report["layers"]]
    assert names in (["XSD", "EN16931", "XRechnung", "KoSIT"], ["XSD", "EN16931", "XRechnung", "KoSIT", "PDF/A"])
    for layer in report["layers"]:
        assert set(layer) == {"name", "ran", "skipped_reason", "errors", "warnings"}
        assert isinstance(layer["ran"], bool)
        assert (layer["skipped_reason"] is None) == layer["ran"]
        for issue in layer["errors"] + layer["warnings"]:
            assert set(issue) == {"id", "message_de", "text_en", "location"}
            assert issue["message_de"] and issue["text_en"] is not None
    tw = report["totals_warning"]
    assert tw is None or set(tw) == {"expected", "computed"}


def test_shape_valid_and_invalid(sample):
    xml = build_cii(sample())
    good = validate(xml, "a.xml")
    _check_shape(good)
    kosit = good["layers"][3]
    assert kosit["ran"] is False and kosit["skipped_reason"] == "KoSIT-Prüfer nicht installiert"
    for bad in (xml.replace(b"<ram:BuyerReference>KD-10234</ram:BuyerReference>", b""), b"<x", b""):
        _check_shape(validate(bad))


@pytest.mark.parametrize("env,valid", [("dev", True), ("test", True), ("staging", False), ("prod", False)])
def test_validity_rule_requires_kosit_on_staging_prod(sample, monkeypatch, env, valid):
    monkeypatch.setenv("APP_ENV", env)
    assert validate(build_cii(sample()))["valid"] is valid


def test_skipped_layer_never_counts_as_passed():
    layers = [V._layer("XSD"), V._layer("EN16931", ran=False, skipped_reason="x"), V._layer("XRechnung"),
              V._layer("KoSIT", ran=False, skipped_reason="y")]
    assert V.is_valid(layers, "xrechnung", "dev") is False
    layers[1] = V._layer("EN16931")
    assert V.is_valid(layers, "xrechnung", "dev") is True
    assert V.is_valid(layers, "xrechnung", "prod") is False
    layers[2] = V._layer("XRechnung", ran=False, skipped_reason="kein Profil")
    assert V.is_valid(layers, "zugferd", "dev") is True
    assert V.is_valid(layers, "xrechnung", "dev") is False


VARL_REJECT = b"""<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">
 <rep:scenarioMatched><rep:validationStepResult id="val-sch.1" valid="false">
  <rep:message id="m1" level="error" code="BR-DE-15" xpathLocation="/rsm:CrossIndustryInvoice[1]">[BR-DE-15] Das Element ...</rep:message>
  <rep:message id="m2" level="warning" code="BR-DE-21" xpathLocation="/x">[BR-DE-21] ...</rep:message>
 </rep:validationStepResult></rep:scenarioMatched>
 <rep:assessment><rep:reject/></rep:assessment></rep:report>"""

VARL_ACCEPT = b"""<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">
 <rep:assessment><rep:accept/></rep:assessment></rep:report>"""


def _fake_reports(cmd, report_for):
    """Write `<stem>-report.xml` for every input file of a KoSIT command line, like the real CLI."""
    out = Path(cmd[cmd.index("-o") + 1])
    for src in cmd[cmd.index("-o") + 2:]:
        body = report_for(Path(src))
        if body is not None:
            (out / f"{Path(src).stem}-report.xml").write_bytes(body)


def test_kosit_report_parser():
    errors, warnings, accepted = V.parse_kosit_report(VARL_REJECT)
    assert [e["id"] for e in errors] == ["BR-DE-15"] and [w["id"] for w in warnings] == ["BR-DE-21"]
    assert accepted is False
    assert V.parse_kosit_report(VARL_ACCEPT) == ([], [], True)
    errors, _, _ = V.parse_kosit_report(VARL_ACCEPT.replace(b"accept", b"reject"))
    assert [e["id"] for e in errors] == ["KOSIT-REJECT"]


def test_kosit_layer_runs_java_when_configured(sample, tmp_path, monkeypatch):
    jar = tmp_path / "validator.jar"
    jar.write_bytes(b"fake")
    (tmp_path / "scenarios.xml").write_text("<scenarios/>")
    monkeypatch.setenv("KOSIT_VALIDATOR_JAR", str(jar))
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        _fake_reports(cmd, lambda _src: VARL_ACCEPT)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(V.subprocess, "run", fake_run)
    monkeypatch.setenv("APP_ENV", "prod")
    r = validate(build_cii(sample()))
    assert calls and calls[0][:3] == ["java", "-jar", str(jar)] and "-s" in calls[0] and "-r" in calls[0]
    kosit = r["layers"][3]
    assert kosit["ran"] is True and kosit["errors"] == [] and r["valid"] is True


def test_kosit_configured_but_incomplete(sample, tmp_path, monkeypatch):
    monkeypatch.setenv("KOSIT_VALIDATOR_JAR", str(tmp_path / "missing.jar"))
    kosit = validate(build_cii(sample()))["layers"][3]
    assert kosit["ran"] is False and kosit["skipped_reason"]


def test_german_messages_exist_in_pinned_rules():
    cen = (RULES / "cen/EN16931-CII-validation.xslt").read_text(encoding="utf-8")
    xr = (RULES / "xrechnung/XRechnung-CII-validation.sch").read_text(encoding="utf-8")
    supplements = {"BR-CO-25"}  # checked by the engine, absent from the pinned CEN CII stylesheet
    assert len(MESSAGES_DE) >= 20
    for rule_id in MESSAGES_DE:
        if rule_id in supplements:
            continue
        in_cen = f'<xsl:attribute name="id">{rule_id}</xsl:attribute>' in cen
        in_xr = re.search(rf'id="{re.escape(rule_id)}"', xr) is not None
        assert in_cen or in_xr, rule_id
    assert '<xsl:attribute name="id">BR-CO-25</xsl:attribute>' not in cen  # revisit supplement when CEN adds it


def test_unknown_rule_gets_german_frame_with_original():
    from engine.messages_de import message_for
    assert message_for("BR-XYZ", "orig").startswith("Regel BR-XYZ nicht erfüllt") and "orig" in message_for("BR-XYZ", "orig")


# ---------------------------------------------------------------- M1: bounded, batched KoSIT

def _kosit_env(tmp_path, monkeypatch):
    jar = tmp_path / "validator.jar"
    jar.write_bytes(b"fake")
    (tmp_path / "scenarios.xml").write_text("<scenarios/>")
    monkeypatch.setenv("KOSIT_VALIDATOR_JAR", str(jar))


def test_validate_many_uses_one_jvm(sample, tmp_path, monkeypatch):
    _kosit_env(tmp_path, monkeypatch)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        # second file rejected, third gets no report
        _fake_reports(cmd, lambda src: {"invoice-0000": VARL_ACCEPT, "invoice-0001": VARL_REJECT}.get(src.stem))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(V.subprocess, "run", fake_run)
    xml = build_cii(sample())
    reps = V.validate_many([(xml, "a.xml"), (b"<x", "broken.xml"), (xml, "b.xml"), (xml, "c.xml")])
    assert len(calls) == 1 and len(calls[0][calls[0].index("-o") + 2:]) == 3
    assert [r["layers"][3]["ran"] for r in reps] == [True, False, True, False]
    assert reps[0]["layers"][3]["errors"] == []
    assert [e["id"] for e in reps[2]["layers"][3]["errors"]] == ["BR-DE-15"]
    assert reps[3]["layers"][3]["skipped_reason"] == "KoSIT-Prüfer lieferte keinen Bericht"
    assert "XML-NOT-WELLFORMED" in {e["id"] for e in reps[1]["layers"][0]["errors"]}
    for r in reps:
        _check_shape(r)


def test_validate_many_without_kosit_matches_validate(sample):
    xml = build_cii(sample())
    assert V.validate_many([(xml, "a.xml"), (b"", "e.xml")]) == [validate(xml), validate(b"")]
    assert V.validate_many([]) == []


def test_kosit_batches_are_chunked(sample, tmp_path, monkeypatch):
    _kosit_env(tmp_path, monkeypatch)
    monkeypatch.setattr(V, "KOSIT_BATCH_MAX", 2)
    calls = []
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, **kw: (calls.append(cmd), _fake_reports(cmd, lambda s: VARL_ACCEPT),
                                                               subprocess.CompletedProcess(cmd, 0))[2])
    layers = V.layer_kosit_many([b"<a/>"] * 5)
    assert [len(c[c.index("-o") + 2:]) for c in calls] == [2, 2, 1]
    assert all(l["ran"] and not l["errors"] for l in layers)


def test_kosit_parallel_runs_are_bounded(tmp_path, monkeypatch):
    import threading
    import time

    _kosit_env(tmp_path, monkeypatch)
    monkeypatch.setenv("KOSIT_MAX_PARALLEL", "2")
    monkeypatch.setattr(V, "_kosit_sem", {})
    state = {"now": 0, "max": 0}
    lock = threading.Lock()

    def fake_run(cmd, **kw):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        _fake_reports(cmd, lambda s: VARL_ACCEPT)
        with lock:
            state["now"] -= 1
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(V.subprocess, "run", fake_run)
    threads = [threading.Thread(target=V.layer_kosit, args=(b"<a/>",)) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["max"] == 2
    assert V.kosit_semaphore()._initial_value == 2
    monkeypatch.setattr(V, "_kosit_sem", {})
    monkeypatch.setenv("KOSIT_MAX_PARALLEL", "kaputt")
    assert V.kosit_semaphore()._initial_value == V.KOSIT_MAX_PARALLEL_DEFAULT


def test_kosit_timeout_scales_and_is_capped():
    assert V._kosit_timeout(1) == V.KOSIT_TIMEOUT_BASE + V.KOSIT_TIMEOUT_PER_FILE
    assert V._kosit_timeout(10_000) == V.KOSIT_TIMEOUT_MAX


# ---------------------------------------------------------------- M11: PDF/A layer for PDF input

def _zugferd_pdf(sample):
    from facturx import generate_from_binary
    from engine import render_pdf
    inv = sample()
    del inv["buyer_reference"]
    return generate_from_binary(render_pdf(inv), build_cii(inv, profile="zugferd"), flavor="factur-x",
                                level="en16931", check_xsd=False)


def test_pdf_input_shows_pdfa_skipped(sample):
    r = validate(_zugferd_pdf(sample), "rechnung.pdf")
    _check_shape(r)
    pdfa = r["layers"][-1]
    assert pdfa["name"] == "PDF/A" and pdfa["ran"] is False
    assert pdfa["skipped_reason"] == "PDF/A-3-Konformität nicht geprüft" and pdfa["errors"] == []
    # XML inside is fine; the skipped PDF/A check is visible but does not claim a pass
    assert r["valid"] is True
    assert "PDF/A" not in [l["name"] for l in validate(build_cii(sample()))["layers"]]


def test_pdf_without_xml_still_lists_pdfa(sample):
    from engine import render_pdf
    r = validate(render_pdf(sample()), "x.pdf")
    _check_shape(r)
    assert r["layers"][-1]["name"] == "PDF/A" and not r["layers"][-1]["ran"] and not r["valid"]


MUSTANG_OK = b'<validation><pdf><summary status="valid"/></pdf><xml><summary status="valid"/></xml><summary status="valid"/></validation>'
MUSTANG_BAD = (b'<validation><pdf><error type="7">PDF/A-3: OutputIntent fehlt</error><summary status="invalid"/></pdf>'
               b'<summary status="invalid"/></validation>')


@pytest.mark.parametrize("stdout,ran,valid,err", [
    (MUSTANG_OK, True, True, []),
    (MUSTANG_BAD, True, False, ["PDFA-3"]),
    (b"Exception in thread main", False, True, []),
])
def test_pdfa_layer_with_mustang(sample, tmp_path, monkeypatch, stdout, ran, valid, err):
    pdf = _zugferd_pdf(sample)
    jar = tmp_path / "Mustang-CLI.jar"
    jar.write_bytes(b"fake")
    monkeypatch.setenv("MUSTANG_JAR", str(jar))
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        assert (Path(kw["cwd"]) / "in.pdf").read_bytes() == pdf
        return subprocess.CompletedProcess(cmd, 0, stdout, b"")

    monkeypatch.setattr(V.subprocess, "run", fake_run)
    r = validate(pdf, "rechnung.pdf")
    _check_shape(r)
    pdfa = r["layers"][-1]
    assert calls[0][-4:] == ["--action", "validate", "--source", "in.pdf"]
    assert pdfa["ran"] is ran and [e["id"] for e in pdfa["errors"]] == err and r["valid"] is valid
    if err:
        assert "OutputIntent" in pdfa["errors"][0]["text_en"] and "PDF/A-3" in pdfa["errors"][0]["message_de"]
