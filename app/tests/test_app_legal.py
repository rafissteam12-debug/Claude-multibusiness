"""Legal pre-review items owned by the app: footer links, AGB + B2B acceptance, verbatim consent text, reply withdrawal."""
from __future__ import annotations

import re
import subprocess
import sys

import pytest

from app.settings import CONSENT_VERSIONS, TERMS_VERSION, legal_text
from app.tests.helpers import APP, ROOT, SITE, last_link, login, pre_csrf, token_of


def _request_link(client, app, email):
    client.post("/api/v1/auth/magic-link", json={"email": email}, headers={"X-CSRF-Token": pre_csrf(client)})
    link = last_link(app, "login")
    page = client.get(link.replace(APP, ""))
    return link, page, re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)


def test_new_account_needs_agb_and_b2b(client, app):
    email = "neu@testfirma.example"
    link, page, csrf = _request_link(client, app, email)
    assert 'name="accept_terms"' in page.text and 'name="b2b"' in page.text
    assert "ausschließlich für mein Unternehmen (B2B)" in page.text and f"{SITE}/agb/" in page.text
    for data in ({}, {"accept_terms": "1"}, {"b2b": "1"}):
        r = client.post("/api/v1/auth/callback", data=dict(data, token=token_of(link), csrf_token=csrf), follow_redirects=False)
        assert r.status_code == 400 and "beide Punkte" in r.text
        assert app.state.db.one("SELECT COUNT(*) AS n FROM users")["n"] == 0  # no account without acceptance
    r = client.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf, "accept_terms": "1", "b2b": "1"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/app"
    u = app.state.db.one("SELECT * FROM users WHERE email=?", (email,))
    assert u["terms_version"] == TERMS_VERSION and u["terms_accepted_at"] and u["b2b_confirmed_at"]
    exp = client.get("/api/v1/account/export").json()["account"]
    assert exp["terms_version"] == TERMS_VERSION and exp["b2b_confirmed_at"]


def test_existing_user_asked_once(client, app):
    email = "alt@testfirma.example"
    login(client, app, email)
    db = app.state.db
    db.execute("UPDATE users SET terms_version=NULL, terms_accepted_at=NULL, b2b_confirmed_at=NULL")  # account from before
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": re.search(r'name="csrf-token" content="([^"]+)"',
                                                                            client.get("/app").text).group(1)})
    _, page, _ = _request_link(client, app, email)
    assert 'name="accept_terms"' in page.text
    login(client, app, email)  # helper accepts both
    assert db.one("SELECT terms_version FROM users")["terms_version"] == TERMS_VERSION
    client.cookies.clear()
    _, page, _ = _request_link(client, app, email)
    assert 'name="accept_terms"' not in page.text  # asked only once


def test_footer_and_login_links(client, app):
    html = client.get("/login").text
    for p in ("/impressum/", "/datenschutz/", "/agb/"):
        assert f'href="{SITE}{p}"' in html
    assert "nur für Unternehmen (B2B)" in html
    login(client, app)
    for page in ("/app", "/app/profile", "/app/upload", "/hilfe"):
        html = client.get(page).text
        assert all(f'href="{SITE}{p}"' in html for p in ("/impressum/", "/datenschutz/", "/agb/")), page
    assert "Auftragsverarbeitungsvertrag (Entwurf)" in client.get("/app/profile").text


def test_consent_texts_stored_verbatim_and_pinned(tmp_path, monkeypatch):
    for v in CONSENT_VERSIONS:
        assert "Ja, ich möchte E-Mails von Ablaufwerk" in legal_text("consent", v)
    assert "ausschließlich für mein Unternehmen (B2B)" in legal_text("terms", TERMS_VERSION)
    import app.settings as st
    (tmp_path / f"consent-{CONSENT_VERSIONS[-1]}.txt").write_text("geändert", encoding="utf-8")
    monkeypatch.setattr(st, "LEGAL_TEXTS_DIR", tmp_path)
    with pytest.raises(RuntimeError):
        st.legal_text("consent", CONSENT_VERSIONS[-1])
    with pytest.raises(RuntimeError):
        st.legal_text("consent", "2099-01-01-v9")


@pytest.mark.integration
def test_site_checkbox_label_matches_stored_text():
    """The site's subscribe label (brand names filled in, tags removed) must equal the stored v1 text."""
    from app.settings import brand
    html = (ROOT / "site" / "templates" / "partials" / "subscribe.html").read_text(encoding="utf-8")
    assert f'data-consent-version="{CONSENT_VERSIONS[-1]}"' in html
    label = re.search(r'<label for="subscribe-consent-[^>]*>(.*?)</label>', html, re.S).group(1)
    label = label.replace("{{ brand.umbrella }}", brand()["umbrella"]).replace("{{ brand.product }}", brand()["product"])
    label = re.sub(r"<[^>]+>", "", label).strip()
    assert "[Kontrollkästchen] " + label in legal_text("consent", CONSENT_VERSIONS[-1])


def test_admin_unsubscribe_by_reply(client, app, tmp_path):
    from app.consent import withdraw
    client.post("/api/v1/subscribe", json={"email": "antwort@testfirma.example", "consent": True, "source": "guide"},
                headers={"Origin": SITE})
    client.get(last_link(app, "optin").replace(APP, ""))
    client.post("/api/v1/confirm")
    assert withdraw(app.state.db, app.state.security, "Antwort@Testfirma.example", method="reply")
    rec = app.state.db.one("SELECT * FROM consent_records")
    assert rec["method"] == "reply" and rec["unsubscribed_at"]
    assert app.state.db.one("SELECT COUNT(*) AS n FROM subscribers")["n"] == 0
    env = {"APP_ENV": "test", "DATABASE_PATH": str(tmp_path / "a.db"), "TEMP_DIR": str(tmp_path / "t"),
           "SESSION_SECRET": "x", "PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", "app.admin", "unsubscribe", "x@testfirma.example"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "not found" in r.stdout and "testfirma" not in r.stdout
