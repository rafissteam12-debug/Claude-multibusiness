"""Offline tests for ops/scripts and the CI/compose files. No network, no Docker, no Java."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import re
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "ops"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"ops_{name}", OPS / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetch = load("fetch_tools")
site = load("check_site")
suite = load("validate_testsuite")


# ---------------------------------------------------------------- pins / fetch

def test_checked_in_pins_parse_and_are_all_pinned():
    pins = fetch.parse_pins((OPS / "pins.txt").read_text(encoding="utf-8"))
    assert set(pins) == fetch.KNOWN
    assert all(sha for sha, _url in pins.values()), "every tool should carry an official hash"
    assert all(url.startswith("https://github.com/") for _sha, url in pins.values())


@pytest.mark.parametrize("text", [
    "kosit-validator abc https://x",                       # bad hash
    "kosit-validator - http://insecure",                   # not https
    "kosit-validator - https://a extra",                   # too many fields
])
def test_bad_pins_rejected(text):
    with pytest.raises(ValueError):
        fetch.parse_pins(text)


def _zip_bytes(top: str = "") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{top}scenarios.xml", "<scenarios/>")
        z.writestr(f"{top}resources/a.xsl", "<x/>")
    return buf.getvalue()


@pytest.mark.parametrize("top", ["", "xrechnung-config/"])
def test_fetch_verifies_extracts_and_writes_env(tmp_path, monkeypatch, top, capsys):
    blobs = {"https://e.invalid/kosit.jar": b"jar", "https://e.invalid/cfg.zip": _zip_bytes(top),
             "https://e.invalid/m.jar": b"mustang"}
    sha = {u: hashlib.sha256(b).hexdigest() for u, b in blobs.items()}
    pins = tmp_path / "pins.txt"
    pins.write_text(
        f"kosit-validator {sha['https://e.invalid/kosit.jar']} https://e.invalid/kosit.jar\n"
        f"kosit-config {sha['https://e.invalid/cfg.zip']} https://e.invalid/cfg.zip\n"
        "mustang-cli - https://e.invalid/m.jar\n", encoding="utf-8")
    monkeypatch.setattr(fetch, "download", lambda url, target: target.write_bytes(blobs[url]))
    env_file = tmp_path / "env"
    assert fetch.main(["--dest", str(tmp_path / "tools"), "--pins", str(pins), "--env-file", str(env_file)]) == 0
    out = capsys.readouterr().out
    assert f"PIN-ON-FIRST-RUN mustang-cli {hashlib.sha256(b'mustang').hexdigest()}" in out
    assert (tmp_path / "tools/kosit-config/scenarios.xml").is_file()
    env = dict(line.split("=", 1) for line in env_file.read_text().splitlines())
    assert env["KOSIT_CONFIG_DIR"].endswith("kosit-config")
    assert set(env) == {"KOSIT_VALIDATOR_JAR", "KOSIT_CONFIG_DIR", "MUSTANG_JAR"}
    # --strict refuses the unpinned file
    with pytest.raises(SystemExit):
        fetch.main(["--dest", str(tmp_path / "t2"), "--pins", str(pins), "--strict"])


def test_fetch_hash_mismatch_fails(tmp_path, monkeypatch):
    pins = tmp_path / "pins.txt"
    pins.write_text("\n".join(f"{n} {'0' * 64} https://e.invalid/{n}" for n in sorted(fetch.KNOWN)), encoding="utf-8")
    monkeypatch.setattr(fetch, "download", lambda url, target: target.write_bytes(b"tampered"))
    with pytest.raises(SystemExit) as exc:
        fetch.main(["--dest", str(tmp_path / "tools"), "--pins", str(pins)])
    assert exc.value.code == 2


def test_zip_slip_rejected(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../escape.txt", "x")
    with pytest.raises(SystemExit):
        fetch.safe_extract(z, tmp_path / "out")


# ---------------------------------------------------------------- site check

@pytest.mark.parametrize("text", ["Start: 9,90 € pro Monat", "nur € 19", "Business 29 Euro monatlich",
                                  "Preis: 49 EUR"])
def test_prices_detected(text):
    assert site.price_findings(text)


@pytest.mark.parametrize("text", ["Vorjahresumsatz von höchstens 800.000 Euro.",
                                  "Kleinbetragsrechnungen bis 250 Euro Gesamtbetrag",
                                  "Verordnung (EU) 2016/679 (DSGVO), EUR-Lex"])
def test_legal_amounts_are_not_prices(text):
    assert not site.price_findings(text)


def _mini_dist(tmp_path: Path, legal_text: str = "[[BUSINESS_ID_PENDING]]", extra: str = "") -> Path:
    page = ('<html><head><meta name="robots" content="noindex, nofollow"></head>'
            f'<body><div>Testversion – nicht öffentlich</div>{legal_text}{extra}</body></html>')
    for rel in ("index.html", *site.LEGAL_PAGES):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(page, encoding="utf-8")
    (tmp_path / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n", encoding="utf-8")
    (tmp_path / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    return tmp_path


def test_site_check_staging_ok_and_release_blocked(tmp_path):
    dist = _mini_dist(tmp_path)
    assert site.check(dist, "staging") == []
    assert site.check(dist, "release")  # placeholder + banner still present


def test_site_check_flags_price_and_filled_identity(tmp_path):
    dist = _mini_dist(tmp_path, legal_text="Muster GmbH", extra="<p>Start 9,90 €</p>")
    problems = site.check(dist, "staging")
    assert any("price-like" in p for p in problems)
    assert any("BUSINESS_ID_PENDING" in p for p in problems)


def test_site_check_missing_noindex_header(tmp_path):
    dist = _mini_dist(tmp_path)
    (dist / "_headers").write_text("/*\n  X-Frame-Options: DENY\n", encoding="utf-8")
    assert any("_headers" in p for p in site.check(dist, "staging"))


def test_site_check_flags_unverified_note_in_both_modes(tmp_path):
    dist = _mini_dist(tmp_path, extra="<p>Text. [prüfen: Quelle nachtragen]</p>")
    for mode in ("staging", "release"):
        assert any("[prüfen" in p for p in site.check(dist, mode)), mode


def test_site_check_localhost_only_blocks_release(tmp_path):
    dist = _mini_dist(tmp_path)
    (dist / "_headers").write_text(
        "/*\n  X-Robots-Tag: noindex, nofollow\n  Content-Security-Policy: connect-src 'self' http://localhost:8000\n",
        encoding="utf-8")
    assert not any("localhost" in p for p in site.check(dist, "staging"))
    assert any(p.startswith("_headers:") and "localhost" in p for p in site.check(dist, "release"))
    (dist / "index.html").write_text('<a href="http://127.0.0.1:8000/login">x</a>', encoding="utf-8")
    assert any(p.startswith("index.html:") and "localhost" in p for p in site.check(dist, "release"))


@pytest.mark.parametrize("value,mode", [("0", "release"), ("1", "staging"), (None, "staging")])
def test_site_check_mode_follows_site_staging(tmp_path, monkeypatch, value, mode, capsys):
    if value is None:
        monkeypatch.delenv("SITE_STAGING", raising=False)
    else:
        monkeypatch.setenv("SITE_STAGING", value)
    site.main(["--dist", str(_mini_dist(tmp_path))])
    assert f"check_site ({mode})" in capsys.readouterr().out


# ---------------------------------------------------------------- suite comparison

def _row(name, ours_valid, kosit_ok, ran=True, ours_err=("BR-X",), kosit_err=("BR-Y",)):
    return {"name": name, "ours": {"valid": ours_valid, "errors": [] if ours_valid else sorted(ours_err)},
            "kosit": {"ran": ran, "accepted": kosit_ok, "errors": [] if kosit_ok else sorted(kosit_err)}}


KNOWN = {"bad.xml": frozenset({"BR-CL-10", "BR-CL-21"})}
CL = ("BR-CL-10", "BR-CL-21")


def test_compare_accepts_listed_file_rejected_by_both_with_listed_rules():
    rows = [_row("a/ok.xml", True, True), _row("t/bad.xml", False, False, ours_err=CL, kosit_err=CL)]
    assert suite.compare(rows, KNOWN) == []


def test_compare_fails_on_disagreement_both_directions():
    listed = _row("t/bad.xml", False, False, ours_err=CL, kosit_err=CL)
    assert any("FALSE VALID" in p for p in suite.compare([_row("x.xml", True, False), listed], KNOWN))
    assert any("disagreement" in p for p in suite.compare([_row("x.xml", False, True), listed], KNOWN))
    # a listed file that only one side rejects is a disagreement too, and its entry becomes stale
    problems = suite.compare([_row("t/bad.xml", True, False, kosit_err=CL)], KNOWN)
    assert any("FALSE VALID" in p for p in problems) and any("stale" in p for p in problems)


def test_compare_fails_on_unlisted_rejection_and_wrong_rules():
    unlisted = suite.compare([_row("new.xml", False, False), _row("t/bad.xml", False, False, ours_err=CL, kosit_err=CL)], KNOWN)
    assert any("configuration mismatch" in p for p in unlisted)
    wrong = suite.compare([_row("t/bad.xml", False, False, ours_err=CL, kosit_err=("BR-CL-10", "BR-CL-99"))], KNOWN)
    assert any("known invalid with" in p for p in wrong)


def test_compare_fails_on_stale_entry_and_missing_report():
    assert any("stale" in p for p in suite.compare([_row("t/bad.xml", True, True)], KNOWN))
    assert any("no report" in p for p in suite.compare([_row("x.xml", True, True, ran=False)], {}))


def test_known_invalid_file_matches_first_ci_run(tmp_path):
    assert suite.load_known() == {"04.05a-INVOICE_uncefact.xml": frozenset({"BR-CL-10", "BR-CL-21"}),
                                  "02.01a-cvd_INVOICE_uncefact.xml": frozenset({"BR-CL-13"})}
    bad = tmp_path / "k.txt"
    bad.write_text("only-a-name.xml\n", encoding="utf-8")
    with pytest.raises(ValueError):
        suite.load_known(bad)


# ---------------------------------------------------------------- CI / compose / docker files

def test_ci_workflow_shape():
    wf = yaml.safe_load((OPS / "ci" / "ci.yml").read_text(encoding="utf-8"))
    assert set(wf["jobs"]) == {"test", "validators", "docker", "network"}
    text = (OPS / "ci" / "ci.yml").read_text(encoding="utf-8")
    for uses in re.findall(r"uses:\s*(\S+)", text):
        assert re.search(r"@v\d+\.\d+\.\d+$", uses) or re.search(r"@[0-9a-f]{40}$", uses), uses
    assert "echo $ANTHROPIC_API_KEY" not in text and "echo \"$ANTHROPIC_API_KEY\"" not in text
    for forbidden in ("docker push", "wrangler", "gh release", "docker login", "ssh "):
        assert forbidden not in text, forbidden


def test_paths_referenced_by_ci_and_dockerfile_exist():
    text = (OPS / "ci" / "ci.yml").read_text(encoding="utf-8") + (OPS / "Dockerfile").read_text(encoding="utf-8")
    refs = set(re.findall(r"(?<![/\w])((?:ops|site|engine|mapping|app|contracts|content)/[\w./-]+)", text))
    missing = [r for r in sorted(refs) if not (ROOT / r.rstrip("/.")).exists()]
    assert not missing, missing


def test_compose_and_caddy():
    compose = yaml.safe_load((OPS / "docker-compose.yml").read_text(encoding="utf-8"))
    assert {"app", "purge", "caddy"} <= set(compose["services"])
    assert "ports" not in compose["services"]["app"], "app port must not be published"
    caddy = (OPS / "Caddyfile").read_text(encoding="utf-8")
    assert "{$APP_DOMAIN:[[BUSINESS_ID_PENDING_DOMAIN]]} {" in caddy
    assert "max_size" in caddy and "delete token" in caddy and "ip_mask" in caddy
    docker = (OPS / "Dockerfile").read_text(encoding="utf-8")
    assert "USER app" in docker and "--strict" in docker and "HEALTHCHECK" in docker


def _caddy_log_filter_fields() -> list[str]:
    """Lines inside log { format filter { fields { ... } } } of the Caddyfile, comments stripped."""
    text = (OPS / "Caddyfile").read_text(encoding="utf-8")
    m = re.search(r"format filter \{.*?fields \{(.*?)\n\t\t\t\}", text, re.S)
    assert m, "log filter fields block not found"
    return [ln.split("#")[0].strip() for ln in m.group(1).splitlines() if ln.split("#")[0].strip()]


def test_caddy_log_filter_deletes_sensitive_headers():
    fields = _caddy_log_filter_fields()
    for header in ("Referer", "Cookie", "Authorization", "X-Csrf-Token", "X-Forwarded-For"):
        assert f"request>headers>{header} delete" in fields, header
    assert "resp_headers>Set-Cookie delete" in fields
    assert "request>remote_ip ip_mask 16 32" in fields and "request>client_ip ip_mask 16 32" in fields
    assert "request>uri query {" in fields and "delete token" in fields


def test_forwarded_headers_trusted_only_from_caddy():
    compose = yaml.safe_load((OPS / "docker-compose.yml").read_text(encoding="utf-8"))
    svc = compose["services"]
    caddy_ip = svc["caddy"]["networks"]["edge"]["ipv4_address"]
    assert svc["app"]["environment"]["FORWARDED_ALLOW_IPS"] == caddy_ip
    assert "ports" not in svc["app"] and "ports" not in svc["purge"]
    assert svc["caddy"]["environment"] == {"APP_DOMAIN": "${APP_DOMAIN:-}"}, "caddy gets the domain only"
    assert "env_file" not in svc["caddy"]
    docker = (OPS / "Dockerfile").read_text(encoding="utf-8")
    assert '"--forwarded-allow-ips", "*"' not in docker and "FORWARDED_ALLOW_IPS=127.0.0.1" in docker
