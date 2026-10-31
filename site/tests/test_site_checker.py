"""The checker's bundled mock report matches the Report contract, and checker.js renders it honestly."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1]
MOCK = SITE / "static" / "mock-report.json"
CHECKER = SITE / "static" / "checker.js"
LAYER_NAMES = {"XSD", "EN16931", "XRechnung", "KoSIT"}  # contracts/mapping.md


def test_mock_report_matches_contract():
    r = json.loads(MOCK.read_text(encoding="utf-8"))
    assert isinstance(r["valid"], bool)
    assert r["profile"] in ("xrechnung", "zugferd", "unknown")  # mapping.md
    assert r["format"] in ("XRechnung-CII", "XRechnung-UBL", "ZUGFeRD", "unknown")  # api.md
    assert isinstance(r["summary_de"], str)
    assert "totals_warning" in r
    assert r["layers"]
    for layer in r["layers"]:
        assert set(layer) >= {"name", "ran", "skipped_reason", "errors", "warnings"}
        assert layer["name"] in LAYER_NAMES
        assert isinstance(layer["ran"], bool)
        if not layer["ran"]:
            assert layer["skipped_reason"], "a skipped layer must carry its reason"
        for e in layer["errors"] + layer["warnings"]:
            assert set(e) >= {"id", "message_de", "location"}
    # The mock must exercise every UI state: pass, fail and skip.
    states = {("skip" if not l["ran"] else "fail" if l["errors"] else "pass") for l in r["layers"]}
    assert states == {"pass", "fail", "skip"}
    assert r["valid"] is False


def test_checker_js_reads_contract_keys():
    js = CHECKER.read_text(encoding="utf-8")
    for key in ("valid", "layers", "ran", "skipped_reason", "errors", "warnings", "message_de",
                "location", "summary_de", "totals_warning", "format", "profile"):
        assert f".{key}" in js, key
    assert "innerHTML" not in js, "report texts are untrusted; use textContent"
    assert "übersprungen" in js


NODE_SCRIPT = r"""
const c = require(process.argv[2]);
const fs = require("fs");
const out = {};
out.mock = c.normalizeReport(JSON.parse(fs.readFileSync(process.argv[3], "utf8")));
out.lyingValid = c.normalizeReport({valid: true, layers: [{name: "XSD", ran: true, errors: [{id: "X", message_de: "m", location: "/a"}]}]});
out.allSkipped = c.normalizeReport({valid: true, layers: [{name: "KoSIT", ran: false, skipped_reason: null, errors: []}]});
out.validWithSkip = c.normalizeReport({valid: true, format: "XRechnung-CII", layers: [
  {name: "XSD", ran: true, errors: [], warnings: []}, {name: "KoSIT", ran: false, skipped_reason: "nicht installiert"}]});
out.garbage = c.normalizeReport(null);
out.files = [c.validateFile(null, 5242880), c.validateFile({name: "a.csv", size: 10}, 5242880),
             c.validateFile({name: "a.XML", size: 6000000}, 5242880), c.validateFile({name: "a.pdf", size: 10}, 5242880)];
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def node_out(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed; JS behaviour tests skipped")
    script = tmp_path_factory.mktemp("node") / "run.js"
    script.write_text(NODE_SCRIPT, encoding="utf-8")
    res = subprocess.run([node, str(script), str(CHECKER), str(MOCK)], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_js_renders_mock_states(node_out):
    v = node_out["mock"]
    assert v["valid"] is False and "keine gültige" in v["overall"]
    by_name = {l["name"]: l for l in v["layers"]}
    assert by_name["XSD"]["state"] == "pass" and by_name["XSD"]["status"] == "bestanden"
    assert by_name["EN16931"]["state"] == "fail"
    assert by_name["XRechnung"]["errors"][0]["id"] == "BR-DE-15"
    assert by_name["XRechnung"]["errors"][0]["location"].startswith("/rsm:")
    kosit = by_name["KoSIT"]
    assert kosit["state"] == "skip"
    assert kosit["status"].startswith("übersprungen – ") and "nicht installiert" in kosit["status"]
    assert "bestanden" not in kosit["status"]
    assert "Erkanntes Format: XRechnung (Syntax CII)" == v["format"]


def test_js_never_shows_skipped_as_passed(node_out):
    assert node_out["lyingValid"]["valid"] is False  # errors override a wrong valid flag
    a = node_out["allSkipped"]
    assert a["valid"] is False and a["layers"][0]["status"] == "übersprungen – kein Grund angegeben"
    w = node_out["validWithSkip"]
    assert w["valid"] is True and "nicht als bestanden" in w["skippedNote"]
    assert node_out["garbage"]["valid"] is False and node_out["garbage"]["layers"] == []


def test_js_validates_files(node_out):
    none, wrong_type, too_big, ok = node_out["files"]
    assert none and "XML- oder PDF" in wrong_type and "5 MB" in too_big and ok == ""
