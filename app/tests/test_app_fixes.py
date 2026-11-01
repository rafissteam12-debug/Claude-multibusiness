"""Wave 4 review fixes: H1 event loop, H2 markers, H3 format, H4 account, M2/M3/M4/M7/M9/M12, L1/L2/L4/L9."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path

import pytest

from app import clock
from app.tests.helpers import APP, FIXTURES, ROOT, SAMPLES, SITE, Client, last_link, login, wait_job

BT10 = {"target": "/buyer_reference", "constant": "04011000-12345-67", "confidence": 1.0, "reason_de": "Von Ihnen festgelegt"}


def _upload(client, h, fixture="lexware_like.csv"):
    r = client.post("/api/v1/uploads", files={"file": (fixture, (FIXTURES / fixture).read_bytes(), "text/csv")}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _setup(client, app, seller_profile, email="inhaber@testfirma.example"):
    h = {"X-CSRF-Token": login(client, app, email)}
    assert client.put("/api/v1/seller-profile", json=seller_profile, headers=h).status_code == 200
    return h, _upload(client, h)


# ------------------------------------------------------------------ H1
def test_healthz_answers_while_slow_parse_runs(client, app, monkeypatch):
    import mapping
    real = mapping.read_table

    def slow(data, name):
        time.sleep(2.0)
        return real(data, name)

    monkeypatch.setattr(mapping, "read_table", slow)
    h = {"X-CSRF-Token": login(client, app)}
    done = {}
    t = threading.Thread(target=lambda: done.setdefault("r", client.post(
        "/api/v1/uploads", files={"file": ("l.csv", (FIXTURES / "lexware_like.csv").read_bytes(), "text/csv")}, headers=h)))
    t.start()
    time.sleep(0.3)
    t0 = time.monotonic()
    assert client.get("/healthz").json() == {"status": "ok"}
    assert time.monotonic() - t0 < 1.0
    t.join(10)
    assert done["r"].status_code == 201


def test_upload_parsed_once_and_unreadable_is_400(client, app, monkeypatch):
    import mapping
    calls = []
    real = mapping.read_table
    monkeypatch.setattr(mapping, "read_table", lambda d, n: calls.append(n) or real(d, n))
    h = {"X-CSRF-Token": login(client, app)}
    up = _upload(client, h)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    assert client.get(f"/app/mapping/{m['mapping_id']}").status_code == 200
    assert client.get(f"/app/mapping/{m['mapping_id']}").status_code == 200
    assert len(calls) == 1
    r = client.post("/api/v1/uploads", files={"file": ("k.xlsx", b"PK\x03\x04kaputt", "application/octet-stream")}, headers=h)
    assert r.status_code == 400 and r.json()["error"]["code"] == "unreadable_file" and r.json()["error"]["message_de"]


# ------------------------------------------------------------------ H2
def test_loaders_refuse_markers(tmp_path):
    from app.helptexts import UnverifiedContent, load_articles
    from app.mailer import TEMPLATES, MailTemplates
    help_dir = tmp_path / "help"
    help_dir.mkdir()
    (help_dir / "a.md").write_text('---\ntitle: "A"\nslug: "a"\n---\n# A\nText. [prüfen: Quelle]\n', encoding="utf-8")
    with pytest.raises(UnverifiedContent):
        load_articles(help_dir)
    assert "a" in load_articles(help_dir, strict=False)
    mail_dir = tmp_path / "mail"
    mail_dir.mkdir()
    for name in TEMPLATES.values():
        (mail_dir / name).write_text("Betreff: B\nVorschautext: V\n\nHallo\n{% include \"_footer.md\" %}\n", encoding="utf-8")
    (mail_dir / "_footer.md").write_text("Fuß [Prüfen: Adresse]\n", encoding="utf-8")
    with pytest.raises(UnverifiedContent):
        MailTemplates(mail_dir)
    (mail_dir / "_footer.md").write_text("Fuß\n", encoding="utf-8")
    assert MailTemplates(mail_dir).render("login", "x@testfirma.example").subject == "B"


@pytest.mark.integration
def test_real_content_rendered_by_app_has_no_markers():
    """Fails until the content agent's fix (no `[prüfen` in content/emails and content/help) is merged."""
    from app.helptexts import load_articles
    from app.mailer import MailTemplates
    MailTemplates(strict=True)
    load_articles(strict=True)
    for tpl in (ROOT / "app" / "templates").glob("*.html"):
        assert "[prüfen" not in tpl.read_text(encoding="utf-8").lower(), tpl.name


# ------------------------------------------------------------------ H3
def _check(client, data):
    return client.post("/api/v1/check", files={"file": ("r.xml", data, "application/xml")}, headers={"Origin": SITE}).json()


@pytest.fixture(scope="module")
def sample_xml():
    import engine
    return engine.build_cii(json.loads((SAMPLES / "schreinerei.json").read_text(encoding="utf-8")))


def _with_gid(xml: bytes, gid: str) -> bytes:
    return re.sub(rb"(<ram:GuidelineSpecifiedDocumentContextParameter>\s*<ram:ID>)[^<]*", rb"\g<1>" + gid.encode(), xml, count=1)


@pytest.mark.integration
def test_format_from_guideline(client, sample_xml):
    rep = _check(client, sample_xml)
    assert rep["format"] == "XRechnung-CII"
    rep = _check(client, _with_gid(sample_xml, "urn:factur-x.eu:1p0:basicwl"))
    assert rep["format"] == "ZUGFeRD"
    rep = _check(client, _with_gid(sample_xml, "urn:beliebig:irgendwas"))
    assert rep["format"] == "unknown" and rep["valid"] is False
    assert not rep["summary_de"].startswith("Gültig")


def test_detect_format_unit():
    from app.check import detect_format, enforce_known_profile, summary_de
    cii = (b'<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" '
           b'xmlns:ram="x"><rsm:ExchangedDocumentContext><ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>%s</ram:ID>'
           b'</ram:GuidelineSpecifiedDocumentContextParameter></rsm:ExchangedDocumentContext></rsm:CrossIndustryInvoice>')
    xr = cii % b"urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
    assert detect_format(xr, "xml", {"profile": "xrechnung"}) == "XRechnung-CII"
    assert detect_format(cii % b"urn:cen.eu:en16931:2017", "xml", {"profile": "zugferd"}) == "ZUGFeRD"
    assert detect_format(xr, "xml", {"profile": "unknown"}) == "unknown"
    assert detect_format(xr, "xml", {"profile": "zugferd", "guideline_id": "urn:cen.eu:en16931:2017"}) == "ZUGFeRD"
    assert detect_format(b"%PDF", "pdf", {"profile": "unknown"}) == "unknown"
    rep = enforce_known_profile({"valid": True, "profile": "unknown", "layers": []}, "unknown")
    assert rep["valid"] is False and "Gültig" not in summary_de(rep, "unknown")


# ------------------------------------------------------------------ H4
def test_account_export_and_delete(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    fields = [f for f in m["fields"] if f["target"] != "/buyer_reference"] + [BT10]
    client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields}, headers=h)
    up2 = _upload(client, h)
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}, headers=h)
    wait_job(client, h["X-CSRF-Token"], r.json()["job_id"])
    ex = client.get("/api/v1/account/export")
    assert ex.status_code == 200 and "attachment" in ex.headers["content-disposition"]
    data = ex.json()
    assert data["account"]["email"] == "inhaber@testfirma.example" and data["seller_profile"]["seller"]
    assert data["mappings"] and "RE-2026-0101" not in ex.text and "Bäckerei" not in ex.text
    assert "Konto löschen" in client.get("/app/profile").text
    db = app.state.db
    uid = db.one("SELECT id FROM users")["id"]
    raw2 = Path(db.one("SELECT path FROM uploads WHERE id=?", (up2["upload_id"],))["path"])
    outs = [Path(r["path"]) for r in db.all("SELECT path FROM files WHERE path IS NOT NULL")]
    assert raw2.exists() and outs
    # CSRF and same-origin like any other write
    assert client.delete("/api/v1/account").status_code == 403
    assert client.delete("/api/v1/account", headers=dict(h, Origin="https://evil.example")).status_code == 403
    r = client.delete("/api/v1/account", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "deleted"
    for t in ("users", "sessions", "seller_profiles", "mappings", "uploads", "jobs", "files", "usage"):
        assert db.one(f"SELECT COUNT(*) AS n FROM {t}")["n"] == 0, t
    assert db.one("SELECT COUNT(*) AS n FROM tokens WHERE purpose='login'")["n"] == 0
    assert not raw2.exists() and not any(p.exists() for p in outs)
    assert client.get("/api/v1/usage").status_code == 401
    assert "gelöscht" in client.get("/login?geloescht=1").text
    assert uid


def test_inactive_accounts_purged_after_12_months(client, app, seller_profile):
    _setup(client, app, seller_profile)
    clock.travel(364 * 86400)
    assert app.state.runner.purge()["accounts"] == 0
    clock.travel(2 * 86400)
    assert app.state.runner.purge()["accounts"] == 1
    assert app.state.db.one("SELECT COUNT(*) AS n FROM users")["n"] == 0


# ------------------------------------------------------------------ M2
def test_token_link_redirects_without_token(client, app):
    from app.tests.helpers import pre_csrf
    tok = pre_csrf(client)
    client.post("/api/v1/auth/magic-link", json={"email": "a@testfirma.example"}, headers={"X-CSRF-Token": tok})
    link = last_link(app, "login")
    path = link.replace(APP, "")
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/api/v1/auth/callback"
    assert r.headers["referrer-policy"] == "no-referrer"
    page = client.get("/api/v1/auth/callback")
    assert page.status_code == 200 and "Jetzt anmelden" in page.text
    assert page.headers["referrer-policy"] == "same-origin"
    token = re.search(r"token=([^&]+)", link).group(1)
    assert token not in page.text
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    r = client.post("/api/v1/auth/callback", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/app"


# ------------------------------------------------------------------ M3, M4/M6
def test_mapping_page_warnings_required_and_vat_select(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    html = client.get(f"/app/mapping/{m['mapping_id']}").text
    data = json.loads(re.search(r'<script type="application/json" id="mapping-data">(.*?)</script>', html, re.S).group(1))
    for t in ("/number", "/issue_date", "/buyer/name", "/lines/*/description", "/lines/*/quantity", "/lines/*/net_price"):
        assert t in data["required"]
    assert data["required_xrechnung"] == ["/buyer_reference"]
    assert 'class="field-error missing"' in html and "Reverse Charge" in html and "innergemeinschaftlich" in html
    has_delivery = any(f["target"] in ("/delivery_date", "/period/start") for f in m["fields"])
    if not has_delivery:
        assert "Kein Leistungsdatum gefunden" in html and "Leistungsdatum = Rechnungsdatum" in html
    # VAT category and buyer reference as constants are accepted
    fields = [f for f in m["fields"] if f["target"] not in ("/buyer_reference", "/lines/*/vat_category")]
    fields += [BT10, {"target": "/lines/*/vat_category", "constant": "S", "transform": []}]
    issue = next(f for f in m["fields"] if f["target"] == "/issue_date")
    if not has_delivery:
        fields.append({"target": "/delivery_date", "source_column": issue["source_column"], "transform": issue.get("transform", [])})
    assert client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields}, headers=h).status_code == 200
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}, headers=h)
    job = wait_job(client, h["X-CSRF-Token"], r.json()["job_id"])
    assert job["invoices"] and all(not i["notes_de"] for i in job["invoices"])


def test_mapping_warnings_from_propose(client, app, seller_profile, monkeypatch):
    import mapping
    real = mapping.propose

    def with_warn(*a, **k):
        m = real(*a, **k)
        m["warnings"] = [{"target": "/lines/*/vat_category", "reason_de": "0 % ohne Steuerkategorie – bitte wählen"}]
        m["unmapped_required"] = ["/buyer/city"]
        return m

    monkeypatch.setattr(mapping, "propose", with_warn)
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    html = client.get(f"/app/mapping/{m['mapping_id']}").text
    assert "0 % ohne Steuerkategorie – bitte wählen" in html
    assert '"/buyer/city"' in html


# ------------------------------------------------------------------ M7, M12, L2
def test_upload_kept_when_nothing_valid_and_deleted_on_success(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    fields = [f for f in m["fields"] if f["target"] != "/buyer_reference"]
    client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields}, headers=h)
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}, headers=h)
    job = wait_job(client, h["X-CSRF-Token"], r.json()["job_id"])
    assert job["zip_url"] is None and job["upload_available"] is True and job["mapping_id"] == m["mapping_id"]
    assert re.match(r"\d{1,2}\. \w+, \d\d:\d\d Uhr$", job["expires_de"])
    page = client.get(f"/app/jobs/{job['job_id']}").text
    assert "deutsche Zeit" in page and "UTC" not in page
    # fix the mapping and convert again without re-uploading
    client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields + [BT10]}, headers=h)
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}, headers=h)
    job = wait_job(client, h["X-CSRF-Token"], r.json()["job_id"])
    assert job["zip_url"] and job["upload_available"] is False
    row = app.state.db.one("SELECT * FROM uploads WHERE id=?", (up["upload_id"],))
    assert row["path"] is None and row["columns_json"] == "[]" and row["samples_json"] is None and row["size"] == 0
    assert row["row_count"] == 5


# ------------------------------------------------------------------ M9
def test_interrupted_jobs_failed_on_startup(make_app, seller_profile):
    app = make_app()
    with Client(app, base_url=APP) as c:
        h, up = _setup(c, app, seller_profile)
        m = c.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
        uid = app.state.db.one("SELECT id FROM users")["id"]
        for i in range(3):
            app.state.db.execute("INSERT INTO jobs (id, user_id, upload_id, mapping_id, formats, profile, status, created_at) "
                                 "VALUES (?,?,?,?,'[]','xrechnung','running',?)", (f"j{i}", uid, up["upload_id"], m["mapping_id"], clock.now()))
    app2 = make_app()  # same DB: a restart
    with Client(app2, base_url=APP):
        rows = app2.state.db.all("SELECT status, error_de FROM jobs")
        assert all(r["status"] == "failed" and "Server neu gestartet" in r["error_de"] for r in rows)
        clock.travel(24 * 3600 + 60)
        app2.state.runner.purge()
        assert all(r["status"] == "expired" and r["error_de"] is None for r in app2.state.db.all("SELECT * FROM jobs"))


# ------------------------------------------------------------------ L1
def test_malformed_mapping_put_is_400(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    for bad in ([{"target": {"a": 1}, "constant": "x"}], [{"target": "/number", "source_column": ["x"]}],
                [{"target": "/number", "source_column": "Rechnungsnr.", "transform": "de_decimal"}]):
        r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": bad}, headers=h)
        assert r.status_code == 400 and "ungültig" in r.json()["error"]["message_de"]


def test_unexpected_error_logs_class_only(client, app, monkeypatch, caplog):
    import mapping

    def boom(*a, **k):
        raise KeyError("Geheimer Zellinhalt")

    h = {"X-CSRF-Token": login(client, app)}
    up = _upload(client, h)
    monkeypatch.setattr(mapping, "propose", boom)
    with caplog.at_level(logging.ERROR, logger="app"):
        r = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h)
    assert r.status_code == 500 and r.json()["error"]["message_de"]
    assert "KeyError" in caplog.text and "Geheimer" not in caplog.text


# ------------------------------------------------------------------ L4, L9
def test_unsubscribe_keeps_hashed_consent_record(client, app):
    import hashlib
    import hmac
    client.post("/api/v1/subscribe", json={"email": "Leser@Testfirma.example", "consent": True}, headers={"Origin": SITE})
    link = last_link(app, "optin").replace(APP, "")
    client.get(link)
    assert client.post("/api/v1/confirm", follow_redirects=False).status_code == 303
    unsub = last_link(app, "welcome1")
    unsub = [m for m in app.state.mailer.outbox if m.kind == "welcome1"][-1].text
    url = re.search(r"https://testserver(/api/v1/unsubscribe\?token=[^\s)>\"]+)", unsub).group(1)
    client.get(url)
    assert client.post("/api/v1/unsubscribe").status_code == 200
    db = app.state.db
    assert db.one("SELECT COUNT(*) AS n FROM subscribers")["n"] == 0
    rec = db.one("SELECT * FROM consent_records")
    expected = hmac.new(b"test-secret-not-real", b"leser@testfirma.example", hashlib.sha256).hexdigest()
    assert rec["email_hmac"] == expected and rec["consent_version"] and rec["requested_at"] and rec["confirmed_at"]
    assert "testfirma" not in json.dumps(dict(rec)).lower()


def test_events_purged_after_13_months_and_secure_delete(client, app):
    db = app.state.db
    db.execute("INSERT INTO events (name, path, code, created_at) VALUES ('page_view','/',NULL,?)", (clock.now(),))
    clock.travel(397 * 86400)
    app.state.runner.purge()
    assert db.one("SELECT COUNT(*) AS n FROM events")["n"] == 0
    conn = db.connect()
    try:
        assert conn.execute("PRAGMA secure_delete").fetchone()[0] == 1
    finally:
        conn.close()


# ------------------------------------------------------------------ M1
def test_validate_batch_prefers_validate_many():
    from app import validation

    class Eng:
        calls = []

        def validate(self, d, n):
            self.calls.append("one")
            return {"valid": True}

        def validate_many(self, items):
            self.calls.append("many")
            return [{"valid": True} for _ in items]

    e = Eng()
    assert len(validation.validate_batch([(b"a", "a.xml"), (b"b", "b.xml")], e)) == 2 and e.calls == ["many"]

    class Plain:
        def validate(self, d, n):
            return {"valid": False}

    assert validation.validate_batch([(b"a", "a.xml")], Plain()) == [{"valid": False}]
