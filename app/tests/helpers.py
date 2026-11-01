"""Test helpers (importable in importlib mode as app.tests.helpers)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app import clock

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "mapping" / "fixtures"
SAMPLES = ROOT / "engine" / "samples"
APP = "https://testserver"
SITE = "https://site.example"


class Client(TestClient):
    """TestClient that sends a same-origin Origin header on writes unless told otherwise."""

    def request(self, method, url, *args, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        if method.upper() not in ("GET", "HEAD", "OPTIONS") and "Origin" not in headers and "origin" not in headers:
            headers["Origin"] = APP
        headers = {k: v for k, v in headers.items() if v is not None}
        return super().request(method, url, *args, headers=headers, **kwargs)


def pre_csrf(c: TestClient) -> str:
    html = c.get("/login").text
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def last_link(app, kind: str) -> str:
    mails = [m for m in app.state.mailer.outbox if m.kind == kind]
    assert mails, f"no {kind} mail"
    return mails[-1].link


def token_of(link: str) -> str:
    return parse_qs(urlsplit(link).query)["token"][0]


def login(c: TestClient, app, email="inhaber@testfirma.example", avv: bool = True) -> str:
    """Magic link -> GET confirm page -> POST consume (-> accept the AVV). Returns the session CSRF token."""
    tok = pre_csrf(c)
    r = c.post("/api/v1/auth/magic-link", json={"email": email}, headers={"X-CSRF-Token": tok})
    assert r.status_code == 202, r.text
    link = last_link(app, "login")
    path = urlsplit(link).path + "?" + urlsplit(link).query
    page = c.get(path)
    assert page.status_code == 200
    form_csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    r = c.post("/api/v1/auth/callback", data={"token": token_of(link), "csrf_token": form_csrf, "accept_terms": "1", "b2b": "1"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/app", r.text
    html = c.get("/app").text
    csrf = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
    if avv:
        r = c.post("/api/v1/account/avv", json={"accept": True}, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200, r.text
    return csrf


def wait_job(c: TestClient, csrf: str, job_id: str, timeout=60) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"/api/v1/conversions/{job_id}").json()
        if j["status"] not in ("queued", "running"):
            return j
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def real_content_has_markers() -> bool:
    """True while content/emails or content/help still contain `[prüfen` (before the content fix is merged)."""
    from app.helptexts import MARKER_RE
    for sub in ("emails", "help"):
        for f in (ROOT / "content" / sub).glob("*.md"):
            if MARKER_RE.search(f.read_text(encoding="utf-8")):
                return True
    return False
