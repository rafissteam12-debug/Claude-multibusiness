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


# Minimal fake DOM: drives the real submit handler with fetch rejecting (app unreachable)
# and records which URLs were fetched and what the status line says.
DOM_SCRIPT = r"""
const vm = require("vm");
const fs = require("fs");
const mockMode = process.argv[3] === "1";
const els = {};
function node(id) {
  return els[id] || (els[id] = {id, hidden: id === "report", textContent: "", className: "",
    firstChild: null, appendChild() {}, removeChild() {}, focus() {},
    getAttribute: () => null, addEventListener(t, f) { this["on" + t] = f; },
    querySelector: () => ({disabled: false})});
}
const fetched = [];
const ctx = {
  console, setTimeout: () => 0, clearTimeout() {}, AbortController: undefined,
  FormData: function () { this.append = function () {}; },
  document: {readyState: "complete", getElementById: node,
             body: {getAttribute: () => "https://app.example.invalid/api/v1"},
             createElement: () => node("x" + Math.random()), createTextNode: () => ({})},
  fetch: function (url) {
    fetched.push(String(url));
    if (String(url).indexOf("mock-report.json") >= 0) {
      return Promise.resolve({json: () => Promise.resolve(JSON.parse(fs.readFileSync(process.argv[4], "utf8")))});
    }
    return Promise.reject(new TypeError("Failed to fetch"));
  },
};
ctx.window = ctx;
ctx.Belegbruecke = {mock: mockMode, track() {}};
node("check-file").files = [{name: "a.xml", size: 100}];
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx);
els["check-form"].onsubmit({preventDefault() {}});
setTimeout(() => {}, 0);
setImmediate(() => setImmediate(() => setImmediate(() => {
  process.stdout.write(JSON.stringify({fetched, status: els["check-status"].textContent,
    statusClass: els["check-status"].className, reportHidden: els["report"].hidden,
    notice: (els["report-notice"] || {}).textContent || ""}));
})));
"""


def _run_dom(tmp_path, mock: bool) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed; JS behaviour tests skipped")
    script = tmp_path / "dom.js"
    script.write_text(DOM_SCRIPT, encoding="utf-8")
    res = subprocess.run([node, str(script), str(CHECKER), "1" if mock else "0", str(MOCK)],
                         capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_unreachable_app_shows_error_not_mock(tmp_path):
    out = _run_dom(tmp_path, mock=False)
    assert out["fetched"] == ["https://app.example.invalid/api/v1/check"]
    assert not any("mock-report" in u for u in out["fetched"]), "no automatic mock fallback"
    assert out["status"] == "Der Prüfdienst ist gerade nicht erreichbar. Bitte später erneut versuchen."
    assert "is-error" in out["statusClass"]
    assert out["reportHidden"] is True


def test_mock_only_with_query_flag_and_labelled(tmp_path):
    out = _run_dom(tmp_path, mock=True)
    assert out["fetched"] == ["/static/mock-report.json"], "mock mode must not send the file"
    assert "Beispielbericht" in out["notice"] and "erfundenen Daten" in out["notice"]
    assert out["reportHidden"] is False


def test_mock_flag_comes_only_from_query_string():
    site_js = (SITE / "static" / "site.js").read_text(encoding="utf-8")
    assert "mock=1" in site_js
    js = CHECKER.read_text(encoding="utf-8")
    # loadMock is defined once and called once (inside the `if (mock)` branch).
    assert js.count("loadMock(") == 2
