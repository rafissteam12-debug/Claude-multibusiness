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
    assert set(report) == {"valid", "profile", "layers", "totals_warning"}
    assert isinstance(report["valid"], bool)
    assert report["profile"] in ("xrechnung", "zugferd", "unknown")
    assert [l["name"] for l in report["layers"]] == ["XSD", "EN16931", "XRechnung", "KoSIT"]
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
        out = Path(cmd[cmd.index("-o") + 1])
        (out / "invoice-report.xml").write_bytes(VARL_ACCEPT)
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
