"""Migrations, mail templates, Brevo adapter (not called), purge CLI, help pages, pages render."""
from __future__ import annotations

import json
import subprocess
import sys

from app.db import Database
from app.mailer import BrevoMailer, MailTemplates
from app.tests.helpers import ROOT, login


def test_migrations_idempotent(tmp_path):
    db = Database(tmp_path / "x.db")
    assert db.migrate() == ["001_init.sql", "002_retention.sql", "003_consent_records.sql"]
    assert db.migrate() == []
    tables = {r["name"] for r in db.all("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("users", "sessions", "tokens", "seller_profiles", "uploads", "mappings", "jobs", "files",
              "subscribers", "events", "usage", "rate_hits", "schema_migrations"):
        assert t in tables


def test_no_raw_ip_stored(client, app):
    client.post("/api/v1/check", files={"file": ("a.xml", b"<a/>", "application/xml")})
    dump = "\n".join(app.state.db.connect().iterdump())
    assert "testclient" not in dump and "127.0.0.1" not in dump


def test_mail_templates_render_all():
    t = MailTemplates(strict=False)
    vals = dict(confirm_url="https://a.example/c", login_url="https://a.example/l", unsubscribe_url="https://a.example/u",
                source_label="über den E-Rechnung-Check", requested_at="01.11.2026", check_url="https://s.example/c",
                site_url="https://s.example", app_url="https://a.example")
    for kind in ("optin", "login", "welcome1", "welcome2"):
        m = t.render(kind, "x@testfirma.example", **vals)
        assert m.subject and "[[BUSINESS_ID_PENDING]]" in m.text and "<html" in m.html
        assert "{{" not in m.text and "{%" not in m.text


def test_brevo_payload_and_send_with_fake_opener():
    sent = {}

    class Resp:
        status = 201
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def opener(req, timeout):
        sent["url"], sent["headers"], sent["body"] = req.full_url, dict(req.headers), json.loads(req.data)
        return Resp()

    m = MailTemplates(strict=False).render("login", "x@testfirma.example", login_url="https://a.example/l", requested_at="heute",
                               site_url="s", check_url="c", app_url="a")
    BrevoMailer("dummy-key", "absender@testfirma.example", opener=opener).send(m)
    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["body"]["to"] == [{"email": "x@testfirma.example"}] and sent["body"]["subject"] == m.subject


def test_purge_cli(tmp_path):
    env = {"APP_ENV": "test", "DATABASE_PATH": str(tmp_path / "p.db"), "TEMP_DIR": str(tmp_path / "t"),
           "SESSION_SECRET": "x", "PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", "app.purge"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("purge:")


def test_help_pages(client):
    idx = client.get("/hilfe").text
    for slug in ("dateien-hochladen", "spaltenzuordnung-pruefen", "fehlermeldungen-verstehen", "ihre-daten", "limits-kostenloser-plan"):
        assert f"/hilfe/{slug}" in idx
        r = client.get(f"/hilfe/{slug}")
        assert r.status_code == 200 and "<h1>" in r.text
    assert "Quellen" in client.get("/hilfe/fehlermeldungen-verstehen").text
    assert client.get("/hilfe/../etc").status_code == 404


def test_pages_require_login(client):
    for path in ("/app", "/app/profile", "/app/upload", "/app/mapping/x", "/app/jobs/x"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login", path


def test_dashboard_prompts_for_profile_and_viewport(client, app):
    login(client, app)
    html = client.get("/app").text
    assert "Profil anlegen" in html and 'name="viewport" content="width=device-width' in html
    assert 'lang="de"' in html and "0</span> von 3" in html


def test_root_redirect(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_static_assets_served(client):
    for f in ("app.css", "app.js", "mapping.js", "job.js", "profile.js", "upload.js", "login.js"):
        assert client.get(f"/static/{f}").status_code == 200
