"""PUBLIC endpoints: /check, /subscribe + double opt-in, /confirm, /unsubscribe, /events."""
from __future__ import annotations

import json
import re

import pytest

from app import clock
from app.tests.helpers import APP, SAMPLES, SITE, last_link, token_of

pytestmark = []


@pytest.fixture(scope="module")
def sample_xml():
    import engine
    inv = json.loads((SAMPLES / "schreinerei.json").read_text(encoding="utf-8"))
    return engine.build_cii(inv)


def _check(client, data, name="r.xml", ctype="application/xml", **kw):
    return client.post("/api/v1/check", files={"file": (name, data, ctype)}, headers={"Origin": SITE}, **kw)


@pytest.mark.integration
def test_check_valid_sample(client, sample_xml):
    r = _check(client, sample_xml)
    assert r.status_code == 200
    rep = r.json()
    assert rep["valid"] is True and rep["format"] == "XRechnung-CII" and rep["profile"] == "xrechnung"
    kosit = [l for l in rep["layers"] if l["name"] == "KoSIT"][0]
    assert kosit["ran"] is False and kosit["skipped_reason"]
    assert "Übersprungen" in rep["summary_de"] and rep["summary_de"].startswith("Gültig")
    assert r.headers["access-control-allow-origin"] == SITE


@pytest.mark.integration
def test_check_broken_xml(client, sample_xml):
    broken = sample_xml.replace(b"<ram:BuyerReference>", b"<ram:BuyerReferenceX>", 1)
    rep = _check(client, broken).json()
    assert rep["valid"] is False and rep["summary_de"].startswith("Nicht gültig")


@pytest.mark.integration
def test_check_invoice_with_rule_errors(client):
    import engine
    inv = json.loads((SAMPLES / "schreinerei.json").read_text(encoding="utf-8"))
    xml = engine.build_cii(inv)
    xml = re.sub(rb"<ram:BuyerReference>[^<]*</ram:BuyerReference>", b"", xml)
    rep = _check(client, xml).json()
    assert rep["valid"] is False
    ids = [e["id"] for l in rep["layers"] for e in l["errors"]]
    assert "BR-DE-15" in ids


@pytest.mark.integration
def test_check_xxe_payload_is_not_resolved(client):
    xxe = (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
           b'<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">&x;</rsm:CrossIndustryInvoice>')
    r = _check(client, xxe)
    assert r.status_code == 200
    body = r.text
    assert "root:" not in body
    rep = r.json()
    assert rep["valid"] is False and rep["format"] == "unknown"
    assert any(e["id"] == "XML-DOCTYPE" for l in rep["layers"] for e in l["errors"])


def test_check_billion_laughs_not_expanded(client):
    bomb = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]><l>&b;</l>'
    rep = _check(client, bomb).json()
    assert rep["valid"] is False and rep["format"] == "unknown"


def test_check_too_large(client):
    r = _check(client, b"<a>" + b" " * (5 * 1024 * 1024 + 10) + b"</a>")
    assert r.status_code == 413 and r.json()["error"]["message_de"]


def test_check_wrong_type_and_missing_file(client):
    r = _check(client, b"hello world", name="notiz.txt", ctype="text/plain")
    assert r.status_code == 415
    r = client.post("/api/v1/check", data={"x": "1"}, headers={"Origin": SITE})
    assert r.status_code == 400 and r.json()["error"]["code"] == "file_missing"


def test_check_rate_limit(client):
    for _ in range(20):
        assert _check(client, b"<a/>").status_code == 200
    r = _check(client, b"<a/>")
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"
    clock.travel(3601)
    assert _check(client, b"<a/>").status_code == 200


def test_check_does_not_store_file(client, app):
    _check(client, b"<a/>")
    for t in ("uploads", "files", "jobs"):
        assert app.state.db.one(f"SELECT COUNT(*) AS n FROM {t}")["n"] == 0


# ------------------------------------------------------------------ subscribe / double opt-in
def _sub(client, **body):
    payload = {"email": "leser@testfirma.example", "consent": True, "consent_version": "2026-10-31-v1", "source": "check"}
    payload.update(body)
    return client.post("/api/v1/subscribe", json=payload, headers={"Origin": SITE})


def test_subscribe_double_opt_in_and_unsubscribe(client, app):
    r = _sub(client)
    assert r.status_code == 202
    row = app.state.db.one("SELECT * FROM subscribers")
    assert row["consent_version"] == "2026-10-31-v1" and row["requested_at"] and row["confirmed_at"] is None
    link = last_link(app, "optin")
    assert "über den E-Rechnung-Check" in app.state.mailer.outbox[-1].text
    # GET shows button and does not confirm
    page = client.get(link.replace(APP, ""))
    assert page.status_code == 200 and "Anmeldung bestätigen" in page.text
    assert app.state.db.one("SELECT confirmed_at FROM subscribers")["confirmed_at"] is None
    r = client.post("/api/v1/confirm", data={"token": token_of(link)}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/bestaetigt"
    assert app.state.db.one("SELECT confirmed_at FROM subscribers")["confirmed_at"]
    assert client.get("/bestaetigt").status_code == 200
    # second use fails
    assert client.post("/api/v1/confirm", data={"token": token_of(link)}).status_code == 400
    # welcome mail 1 carries an unsubscribe link
    welcome = [m for m in app.state.mailer.outbox if m.kind == "welcome1"][-1]
    assert welcome.link and "/api/v1/unsubscribe?token=" in welcome.link and welcome.link in welcome.text
    page = client.get(welcome.link.replace(APP, ""))
    assert page.status_code == 200 and "abmelden" in page.text.lower()
    assert app.state.db.one("SELECT COUNT(*) AS n FROM subscribers")["n"] == 1
    r = client.post("/api/v1/unsubscribe", data={"token": token_of(welcome.link)})
    assert r.status_code == 200
    assert app.state.db.one("SELECT COUNT(*) AS n FROM subscribers")["n"] == 0


def test_welcome2_after_three_days(client, app):
    _sub(client)
    link = last_link(app, "optin")
    client.post("/api/v1/confirm", data={"token": token_of(link)})
    app.state.send_welcome2_due()
    assert not [m for m in app.state.mailer.outbox if m.kind == "welcome2"]
    clock.travel(3 * 86400 + 10)
    app.state.send_welcome2_due()
    app.state.send_welcome2_due()
    assert len([m for m in app.state.mailer.outbox if m.kind == "welcome2"]) == 1


def test_optin_token_expires(client, app):
    _sub(client)
    link = last_link(app, "optin")
    clock.travel(16 * 60)
    assert client.get(link.replace(APP, "")).status_code == 400
    assert client.post("/api/v1/confirm", data={"token": token_of(link)}).status_code == 400


def test_subscribe_validation(client):
    assert _sub(client, email="kaputt").status_code == 400
    assert _sub(client, consent=False).json()["error"]["code"] == "consent_missing"
    assert _sub(client, consent_version="2020-01-01-v0").json()["error"]["code"] == "unknown_consent_version"
    assert _sub(client, source="<script>").status_code == 400
    assert _sub(client, source="ig-001", email="ig@testfirma.example").status_code == 202
    r = client.post("/api/v1/subscribe", content="nicht json", headers={"Origin": SITE, "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_json"


def test_subscribe_rate_limit_per_ip(client):
    codes = [_sub(client, email=f"l{i}@testfirma.example").status_code for i in range(11)]
    assert codes[:10] == [202] * 10 and codes[10] == 429


def test_confirm_invalid_token(client):
    assert client.get("/api/v1/confirm?token=unsinn").status_code == 400
    assert client.post("/api/v1/confirm", data={"token": "unsinn"}).status_code == 400
    assert client.get("/api/v1/unsubscribe").status_code == 400


# ------------------------------------------------------------------ events
def test_events_text_plain_and_whitelist(client, app):
    r = client.post("/api/v1/events", content=json.dumps({"name": "page_view", "path": "/ratgeber/?a=1", "code": "ig-001"}),
                    headers={"Origin": SITE, "Content-Type": "text/plain;charset=UTF-8"})
    assert r.status_code == 204
    row = app.state.db.one("SELECT * FROM events WHERE name='page_view'")
    assert row["path"] == "/ratgeber/" and row["code"] == "ig-001"
    assert client.post("/api/v1/events", content='{"name":"page_view","path":"/","code":null}',
                       headers={"Origin": SITE, "Content-Type": "text/plain"}).status_code == 204
    assert client.post("/api/v1/events", content='{"name":"hack","path":"/"}', headers={"Origin": SITE}).status_code == 400
    assert client.post("/api/v1/events", content='{"name":"page_view","path":"/","code":"BAD CODE"}',
                       headers={"Origin": SITE}).status_code == 400
    assert client.post("/api/v1/events", content="x" * 5000, headers={"Origin": SITE}).status_code == 413


def test_events_allowed_from_env(make_app):
    from app.tests.helpers import Client
    app = make_app(EVENTS_ALLOWED="page_view")
    with Client(app, base_url=APP) as c:
        assert c.post("/api/v1/events", content='{"name":"subscribe","path":"/"}', headers={"Origin": SITE}).status_code == 400
