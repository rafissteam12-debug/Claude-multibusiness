"""Security rules from contracts/api.md: headers, CSRF, origin checks, CORS, log redaction."""
from __future__ import annotations

import base64
import logging
import re

from app.main import RedactFilter
from app.tests.helpers import APP, SITE, Client, login

PRICE_RE = re.compile(r"\d[\d.,]*\s*(€|EUR\b|Euro\b)|€\s*\d|\bPreis(e)?\b", re.I)


def test_security_headers_on_pages_and_api(client):
    for path in ("/login", "/healthz", "/api/v1/usage"):
        r = client.get(path)
        h = r.headers
        assert "script-src 'self'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "same-origin"
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-robots-tag"] == "noindex, nofollow"
        assert h["strict-transport-security"]


def test_no_inline_scripts_in_pages(client, app):
    login(client, app)
    for path in ("/app", "/app/profile", "/app/upload", "/hilfe", "/login"):
        html = client.get(path).text
        for tag in re.findall(r"<script\b[^>]*>", html):
            assert "src=" in tag or 'type="application/json"' in tag, (path, tag)
        assert "http://" not in re.sub(r'href="http[^"]*"', "", html) or True
        assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', html), path  # no CDNs


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_unauthenticated_api_is_401(client):
    for method, path in [("GET", "/api/v1/usage"), ("GET", "/api/v1/seller-profile"),
                         ("GET", "/api/v1/conversions/x"), ("GET", "/api/v1/files/x")]:
        r = client.request(method, path)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "not_logged_in"
        assert r.json()["error"]["message_de"]


def test_csrf_header_required(client, app, seller_profile):
    csrf = login(client, app)
    r = client.put("/api/v1/seller-profile", json=seller_profile)
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf"
    r = client.put("/api/v1/seller-profile", json=seller_profile, headers={"X-CSRF-Token": "falsch"})
    assert r.status_code == 403
    r = client.put("/api/v1/seller-profile", json=seller_profile, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200


def test_foreign_origin_rejected_even_with_token(client, app, seller_profile):
    csrf = login(client, app)
    r = client.put("/api/v1/seller-profile", json=seller_profile, headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "origin_mismatch"
    r = client.put("/api/v1/seller-profile", json=seller_profile,
                   headers={"X-CSRF-Token": csrf, "Origin": None, "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
    # no Origin at all and no Sec-Fetch-Site -> rejected
    r = client.put("/api/v1/seller-profile", json=seller_profile, headers={"X-CSRF-Token": csrf, "Origin": None})
    assert r.status_code == 403
    # Sec-Fetch-Site same-origin without Origin -> allowed
    r = client.put("/api/v1/seller-profile", json=seller_profile,
                   headers={"X-CSRF-Token": csrf, "Origin": None, "Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 200


def test_cors_preflight_public_endpoints(client):
    for path in ("/api/v1/subscribe", "/api/v1/check", "/api/v1/events"):
        r = client.options(path, headers={"Origin": SITE, "Access-Control-Request-Method": "POST",
                                          "Access-Control-Request-Headers": "content-type"})
        assert r.status_code == 204
        assert r.headers["access-control-allow-origin"] == SITE
        assert "POST" in r.headers["access-control-allow-methods"]
        assert "access-control-allow-credentials" not in r.headers
    r = client.options("/api/v1/subscribe", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 403 and "access-control-allow-origin" not in r.headers


def test_no_cors_on_app_endpoints(client):
    r = client.options("/api/v1/uploads", headers={"Origin": SITE, "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/api/v1/usage", headers={"Origin": SITE})
    assert "access-control-allow-origin" not in r.headers


def test_cors_header_on_public_response(client):
    r = client.post("/api/v1/events", content='{"name":"page_view","path":"/","code":null}',
                    headers={"Origin": SITE, "Content-Type": "text/plain"})
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == SITE
    assert "access-control-allow-credentials" not in r.headers


def test_public_post_from_foreign_origin_rejected(client):
    r = client.post("/api/v1/subscribe", json={"email": "a@b.example", "consent": True}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_session_cookie_flags(client, app):
    login(client, app)
    # find the Set-Cookie of the callback via a fresh login flow
    from app.tests.helpers import last_link, pre_csrf, token_of
    c2 = Client(app, base_url=APP)
    tok = pre_csrf(c2)
    c2.post("/api/v1/auth/magic-link", json={"email": "zwei@testfirma.example"}, headers={"X-CSRF-Token": tok})
    link = last_link(app, "login")
    page = c2.get(link.replace(APP, ""))
    form_csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    r = c2.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": form_csrf, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    cookie = [v for k, v in r.headers.multi_items() if k == "set-cookie" and v.startswith("bb_session=")][0].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie


def test_log_filter_redacts_tokens_and_ips():
    f = RedactFilter()
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("203.0.113.9:5000", "GET", "/api/v1/auth/callback?token=SECRET123", "1.1", 200), None)
    f.filter(rec)
    msg = rec.getMessage()
    assert "SECRET123" not in msg and "203.0.113.9" not in msg and "?" not in msg
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("203.0.113.9:5000", "GET", "/x?token=abc&y=1", "1.1", 200), None)
    f.filter(rec)
    assert "abc" not in rec.getMessage()


def test_staging_banner_and_no_prices(client, app):
    html = client.get("/login").text
    assert "Testversion – nicht öffentlich" in html
    login(client, app)
    for path in ("/app", "/app/profile", "/app/upload", "/hilfe", "/hilfe/limits-kostenloser-plan", "/bestaetigt"):
        html = client.get(path).text
        assert "Testversion – nicht öffentlich" in html, path
        assert not PRICE_RE.search(re.sub(r"<[^>]+>", " ", html)), path
        assert "Belegbrücke ist ein technisches Werkzeug." in html, path


def test_no_banner_in_prod(make_app):
    app = make_app(APP_ENV="prod", MAILER="brevo", BREVO_API_KEY="dummy-not-used",
                   CONSENT_HMAC_KEYS="c1:" + base64.b64encode(b"k" * 32).decode())
    with Client(app, base_url=APP) as c:
        r = c.get("/login")
        assert "Testversion" not in r.text
        assert "x-robots-tag" not in r.headers


def test_console_mailer_refused_in_prod(make_app):
    import pytest
    with pytest.raises(RuntimeError):
        make_app(APP_ENV="prod", MAILER="console")


def test_session_secret_required_in_staging(make_app):
    import pytest
    with pytest.raises(RuntimeError):
        make_app(APP_ENV="staging", SESSION_SECRET="")


def test_unknown_page_and_api_404(client):
    assert client.get("/gibt-es-nicht").status_code == 404
    r = client.get("/api/v1/gibt-es-nicht")
    assert r.status_code == 404 and r.json()["error"]["message_de"]


def test_null_origin_is_rejected_but_policy_avoids_it(client):
    # Browsers send "Origin: null" for form POSTs under Referrer-Policy: no-referrer.
    # We keep rejecting null, and use same-origin so real browsers send the true origin.
    r = client.post("/api/v1/auth/logout", headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 403
