"""Magic-link login: GET shows a button, POST consumes; single use, hashed, 15 min TTL, rate limits."""
from __future__ import annotations

import re

from app import clock
from app.tests.helpers import APP, Client, last_link, login, pre_csrf, token_of


def _request(c, app, email="inhaber@testfirma.example"):
    tok = pre_csrf(c)
    r = c.post("/api/v1/auth/magic-link", json={"email": email}, headers={"X-CSRF-Token": tok})
    return r


def _form_csrf(c, link):
    page = c.get(link.replace(APP, ""))
    m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    return page, (m.group(1) if m else None)


def test_login_flow_and_logout(client, app):
    csrf = login(client, app)
    assert client.get("/api/v1/usage").status_code == 200
    assert client.get("/app").status_code == 200
    r = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert client.get("/api/v1/usage").status_code == 401
    r = client.get("/app", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_magic_link_needs_csrf(client):
    client.get("/login")
    r = client.post("/api/v1/auth/magic-link", json={"email": "a@testfirma.example"})
    assert r.status_code == 403


def test_magic_link_invalid_email(client, app):
    tok = pre_csrf(client)
    r = client.post("/api/v1/auth/magic-link", json={"email": "keine-adresse"}, headers={"X-CSRF-Token": tok})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_email"


def test_get_does_not_consume_token(client, app):
    _request(client, app)
    link = last_link(app, "login")
    for _ in range(3):  # mail scanners
        page, csrf = _form_csrf(client, link)
        assert page.status_code == 200 and "Jetzt anmelden" in page.text
    r = client.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    assert r.status_code == 303


def test_token_single_use(client, app):
    _request(client, app)
    link = last_link(app, "login")
    _, csrf = _form_csrf(client, link)
    r1 = client.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    assert r1.status_code == 303
    c2 = Client(app, base_url=APP)
    page, csrf2 = _form_csrf(c2, link)
    assert page.status_code == 400  # GET shows "abgelaufen"
    c2.get("/login")
    csrf2 = pre_csrf(c2)
    r2 = c2.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf2, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    assert r2.status_code == 400


def test_token_expires_after_15_minutes(client, app):
    _request(client, app)
    link = last_link(app, "login")
    _, csrf = _form_csrf(client, link)
    clock.travel(15 * 60 + 5)
    r = client.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    assert r.status_code == 400


def test_callback_needs_pre_csrf_and_origin(client, app):
    _request(client, app)
    link = last_link(app, "login")
    _form_csrf(client, link)
    r = client.post("/api/v1/auth/callback", data={"token": token_of(link)}, follow_redirects=False)
    assert r.status_code == 403
    _, csrf = _form_csrf(client, link)
    r = client.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": csrf},
                    headers={"Origin": "https://evil.example"}, follow_redirects=False)
    assert r.status_code == 403


def test_tokens_stored_hashed(client, app):
    _request(client, app)
    raw = token_of(last_link(app, "login"))
    rows = app.state.db.all("SELECT token_hash FROM tokens")
    assert rows and all(raw not in r["token_hash"] for r in rows)
    sess = app.state.db.all("SELECT * FROM sessions")
    login(client, app)
    cookie = client.cookies.get("bb_session")
    assert all(cookie != r["id_hash"] for r in app.state.db.all("SELECT id_hash FROM sessions"))


def test_magic_link_rate_limit_per_email(client, app):
    for i in range(5):
        assert _request(client, app, "viel@testfirma.example").status_code == 202
    r = _request(client, app, "viel@testfirma.example")
    assert r.status_code == 429 and "Stunde" in r.json()["error"]["message_de"]
    assert _request(client, app, "andere@testfirma.example").status_code == 202
    clock.travel(3601)
    assert _request(client, app, "viel@testfirma.example").status_code == 202


def test_magic_link_rate_limit_per_ip(client, app):
    codes = [_request(client, app, f"nutzer{i}@testfirma.example").status_code for i in range(21)]
    assert codes[:20] == [202] * 20 and codes[20] == 429


def test_login_form_without_js(client, app):
    tok = pre_csrf(client)
    r = client.post("/api/v1/auth/magic-link", data={"email": "form@testfirma.example", "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login?gesendet=1"


def test_mail_uses_content_texts(client, app):
    _request(client, app)
    mail = app.state.mailer.outbox[-1]
    assert mail.subject == "Ihr Anmeldelink für Belegbrücke"
    assert "[[BUSINESS_ID_PENDING]]" in mail.text
    assert "Keine Steuer- oder Rechtsberatung." in mail.text
    assert mail.link in mail.text and "<a href=" in mail.html
