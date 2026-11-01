"""Remediation release: consent keyring (P0-1), consent purge (P0-2), terms + onboarding gate (P0-3),
AVV acceptance (P0-4), AI transfer guard (P1-7)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
import shutil

import pytest

from app import clock
from app.consent import withdraw
from app.settings import AVV_VERSION, TERMS_VERSION, checkbox_labels, legal_text, load_settings
from app.tests.helpers import APP, FIXTURES, ROOT, Client, last_link, login, pre_csrf

K1 = base64.b64encode(b"1" * 32).decode()
K2 = base64.b64encode(b"2" * 32).decode()
YEAR = 365 * 86400


def _mac(key: bytes, email: str) -> str:
    return hmac.new(key, email.encode(), hashlib.sha256).hexdigest()


def _confirm(client, app, email):
    r = client.post("/api/v1/subscribe", json={"email": email, "consent": True, "source": "check"},
                    headers={"Origin": "https://site.example"})
    assert r.status_code == 202
    client.get(last_link(app, "optin").replace(APP, ""))
    assert client.post("/api/v1/confirm", follow_redirects=False).status_code == 303


def _withdraw(app, email):
    assert withdraw(app.state.db, app.state.security, email, method="reply")
    return app.state.db.all("SELECT * FROM consent_records ORDER BY id")


# ================================================================== P0-1 consent keyring
def test_new_record_stores_current_key_id(make_app):
    app = make_app(CONSENT_HMAC_KEYS=f"c2:{K2},c1:{K1}")
    with Client(app, base_url=APP) as c:
        _confirm(c, app, "leser@testfirma.example")
    rec = app.state.db.one("SELECT * FROM consent_records")
    assert rec["key_id"] == "c2" and rec["email_hmac"] == _mac(b"2" * 32, "leser@testfirma.example")


def test_dev_without_keys_keeps_legacy_session_key(app, client):
    _confirm(client, app, "leser@testfirma.example")
    rec = app.state.db.one("SELECT * FROM consent_records")
    assert rec["key_id"] == "legacy-session" and rec["email_hmac"] == _mac(b"test-secret-not-real", "leser@testfirma.example")


def test_session_secret_rotation_keeps_matching_dedicated_key(make_app):
    app = make_app(SESSION_SECRET="old-session-secret", CONSENT_HMAC_KEYS=f"c1:{K1}")
    with Client(app, base_url=APP) as c:
        _confirm(c, app, "leser@testfirma.example")
    app2 = make_app(SESSION_SECRET="new-session-secret", CONSENT_HMAC_KEYS=f"c1:{K1}")
    rows = _withdraw(app2, "leser@testfirma.example")
    assert len(rows) == 1 and rows[0]["unsubscribed_at"] and rows[0]["method"] == "reply"  # matched, no new record


def test_session_secret_rotation_legacy_records_need_explicit_old_secret(make_app):
    app = make_app(SESSION_SECRET="old-session-secret")  # record from before dedicated keys
    with Client(app, base_url=APP) as c:
        _confirm(c, app, "a@testfirma.example")
        _confirm(c, app, "b@testfirma.example")
    # rotated SESSION_SECRET, old one listed explicitly as legacy-session: the legacy record still matches
    app2 = make_app(SESSION_SECRET="new-session-secret", CONSENT_HMAC_KEYS=f"c1:{K1},legacy-session:old-session-secret")
    rows = _withdraw(app2, "a@testfirma.example")
    assert len(rows) == 2 and rows[0]["unsubscribed_at"] and rows[0]["key_id"] == "legacy-session"
    # without the explicit entry the legacy record is not matchable (a new closed record is written instead)
    app3 = make_app(SESSION_SECRET="new-session-secret", CONSENT_HMAC_KEYS=f"c1:{K1}")
    rows = _withdraw(app3, "b@testfirma.example")
    assert len(rows) == 3 and rows[1]["unsubscribed_at"] is None and rows[2]["key_id"] == "c1"


def test_consent_key_rotation_old_key_kept_second(make_app):
    app = make_app(CONSENT_HMAC_KEYS=f"c1:{K1}")
    with Client(app, base_url=APP) as c:
        _confirm(c, app, "leser@testfirma.example")
    app2 = make_app(CONSENT_HMAC_KEYS=f"c2:{K2},c1:{K1}")
    with Client(app2, base_url=APP) as c:
        _confirm(c, app2, "neu@testfirma.example")
    rows = _withdraw(app2, "leser@testfirma.example")
    assert [r["key_id"] for r in rows] == ["c1", "c2"]
    assert rows[0]["unsubscribed_at"] and rows[1]["unsubscribed_at"] is None


def test_migration_keeps_existing_records_as_legacy(tmp_path, monkeypatch):
    import app.db as dbmod
    old = tmp_path / "migrations"
    old.mkdir()
    for f in sorted(dbmod.MIGRATIONS_DIR.glob("00[1-4]_*.sql")):
        shutil.copy(f, old / f.name)
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", old)
    db = dbmod.Database(tmp_path / "x.db")
    db.migrate()
    db.execute("INSERT INTO consent_records (email_hmac, consent_version, confirmed_at) VALUES ('ab', 'v', 1)")
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", dbmod.Path(dbmod.__file__).parent / "migrations")
    assert db.migrate() == ["005_consent_key_id.sql", "006_avv_acceptance.sql"]
    rec = db.one("SELECT * FROM consent_records")
    assert rec["key_id"] == "legacy-session" and rec["email_hmac"] == "ab"


STAGING = {"APP_ENV": "staging", "SESSION_SECRET": "staging-session-secret"}


@pytest.mark.parametrize("keys, msg", [
    ("", "required"),
    ("c1:" + base64.b64encode(b"staging-session-secret" + b"x" * 10).decode(), None),  # ok (differs)
    ("c1:" + base64.b64encode(b"staging-session-secret").decode(), "at least 32"),
    ("legacy-session:other,c1:" + K1, "dedicated"),
    ("c1:not-base64!", "base64"),
    ("c1:" + K1 + ",c1:" + K2, "duplicate"),
    ("c1", "keyid:base64key"),
])
def test_consent_keys_startup_rules(make_app, keys, msg):
    env = dict(STAGING, CONSENT_HMAC_KEYS=keys)
    if msg is None:
        assert make_app(**env).state.settings.consent_key_id == "c1"
        return
    with pytest.raises(RuntimeError, match=msg):
        make_app(**env)


def test_staging_refuses_current_key_equal_to_session_secret(make_app):
    secret = "s" * 40
    with pytest.raises(RuntimeError, match="differ from SESSION_SECRET"):
        make_app(APP_ENV="staging", SESSION_SECRET=secret, CONSENT_HMAC_KEYS="c1:" + base64.b64encode(secret.encode()).decode())
    with pytest.raises(RuntimeError, match="CONSENT_HMAC_KEYS is required"):
        make_app(APP_ENV="prod", MAILER="brevo", BREVO_API_KEY="dummy-not-used", SESSION_SECRET=secret, CONSENT_HMAC_KEYS="")


# ================================================================== P0-2 consent purge
def test_purge_consent_records_keyring(make_app, caplog):
    app = make_app(CONSENT_HMAC_KEYS=f"c2:{K2},c1:{K1}")
    db, sec, runner = app.state.db, app.state.security, app.state.runner
    now = clock.now()
    k1, k2 = b"1" * 32, b"2" * 32

    def rec(email, key_id, key, confirmed, unsub=None):
        db.execute("INSERT INTO consent_records (email_hmac, key_id, consent_version, confirmed_at, unsubscribed_at) "
                   "VALUES (?,?,?,?,?)", (_mac(key, email), key_id, "2026-10-31-v1", confirmed, unsub))
        return db.one("SELECT MAX(id) AS i FROM consent_records")["i"]

    def sub(email):
        db.execute("INSERT INTO subscribers (email, consent_version, requested_at, confirmed_at) VALUES (?,?,?,?)",
                   (email, "2026-10-31-v1", now - 4 * YEAR, now - 4 * YEAR))

    sub("aktiv@testfirma.example")
    sub("altkey@testfirma.example")
    keep = {
        rec("aktiv@testfirma.example", "c2", k2, now - 4 * YEAR),                     # active, older than 3y
        rec("kurz@testfirma.example", "c2", k2, now - 2 * YEAR, now - 1 * YEAR),       # unsubscribed < 3y
        rec("altkey@testfirma.example", "c1", k1, now - 4 * YEAR),                    # old key, still active
        rec("unbekannt@testfirma.example", "c0", b"0" * 32, now - 4 * YEAR),          # key no longer configured
    }
    gone = {
        rec("weg@testfirma.example", "c2", k2, now - 5 * YEAR, now - 4 * YEAR),        # unsubscribed > 3y
        rec("verschwunden@testfirma.example", "c1", k1, now - 4 * YEAR),              # never unsubscribed, sub gone
    }
    with caplog.at_level(logging.WARNING, logger="app.jobs"):
        assert runner.purge_consent_records(now) == 2
    left = {r["id"] for r in db.all("SELECT id FROM consent_records")}
    assert left == keep and not (left & gone)
    assert "1 records" in caplog.text and "testfirma" not in caplog.text


def test_purge_reads_email_from_subscribers_not_from_consent_query():
    # Audit finding P0-2: the e-mail is read from `SELECT email FROM subscribers` (column exists); consent_records
    # rows are only read as (id, key_id, email_hmac).
    src = (ROOT / "app" / "jobs.py").read_text(encoding="utf-8")
    body = src.split("def purge_consent_records", 1)[1].split("\n    def ", 1)[0]
    assert 'SELECT email FROM subscribers' in body and 'r["email"]' in body
    assert "SELECT id, key_id, email_hmac FROM consent_records" in body


# ================================================================== P0-3 terms + onboarding gate
def test_current_terms_is_agb_draft_2_and_draft_1_kept():
    assert TERMS_VERSION == "agb-draft-2"
    assert "agb-draft-1" in legal_text("terms", "agb-draft-1")
    labels = checkbox_labels("terms", "agb-draft-2")
    assert len(labels) == 2 and "agb-draft-2" in labels[0] and "(B2B)" in labels[1]


def _login_page(client, app, email):
    client.post("/api/v1/auth/magic-link", json={"email": email}, headers={"X-CSRF-Token": pre_csrf(client)})
    link = last_link(app, "login")
    return link, client.get(link.replace(APP, ""))


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def test_login_page_shows_verbatim_terms_labels(client, app):
    _, page = _login_page(client, app, "neu@testfirma.example")
    text = _plain(page.text)
    for label in checkbox_labels("terms", TERMS_VERSION):
        assert label in text
    assert '/agb/" rel="noopener">Allgemeinen Geschäftsbedingungen</a>' in page.text


def test_agb_draft_1_acceptance_is_asked_again(client, app):
    login(client, app)
    db = app.state.db
    db.execute("UPDATE users SET terms_version='agb-draft-1'")
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": re.search(
        r'name="csrf-token" content="([^"]+)"', client.get("/app").text).group(1)})
    _, page = _login_page(client, app, "inhaber@testfirma.example")
    assert 'name="accept_terms"' in page.text


def _prod(make_app, **extra):
    return make_app(APP_ENV="prod", MAILER="brevo", BREVO_API_KEY="dummy-not-used", CONSENT_HMAC_KEYS=f"c1:{K1}", **extra)


def _token_login(c, app, email, accept=True):
    """Login without sending mail (prod uses the Brevo mailer): issue the token directly."""
    tok = app.state.security.issue_token("login", email)
    page = c.get("/api/v1/auth/callback?token=" + tok)
    m = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    data = {"token": tok, "csrf_token": m.group(1) if m else pre_csrf(c)}
    if accept:
        data.update(accept_terms="1", b2b="1")
    return tok, page, c.post("/api/v1/auth/callback", data=data, follow_redirects=False)


@pytest.mark.parametrize("extra", [{}, {"ONBOARDING_OPEN": "1"}])
def test_prod_refuses_new_accounts_while_closed_or_drafts(make_app, extra):
    app = _prod(make_app, **extra)
    with Client(app, base_url=APP) as c:
        tok, page, r = _token_login(c, app, "neu@testfirma.example")
        assert page.status_code == 403 and "noch keine neuen Konten" in page.text
        assert r.status_code == 403 and "noch keine neuen Konten" in r.text
    assert app.state.db.one("SELECT COUNT(*) AS n FROM users")["n"] == 0
    assert app.state.security.peek_token("login", tok) == "neu@testfirma.example"  # not consumed


def test_prod_existing_account_still_logs_in(make_app):
    app = _prod(make_app)
    app.state.db.execute("INSERT INTO users (id, email, plan, created_at, terms_version) VALUES ('u1', ?, 'free', ?, ?)",
                         ("alt@testfirma.example", clock.now(), TERMS_VERSION))
    with Client(app, base_url=APP) as c:
        _, _, r = _token_login(c, app, "alt@testfirma.example", accept=False)
        assert r.status_code == 303 and r.headers["location"] == "/app"


def test_prod_opens_only_with_flag_and_final_versions(make_app, monkeypatch):
    import app.settings as st
    monkeypatch.setattr(st, "TERMS_VERSION", "agb-1")
    monkeypatch.setattr(st, "AVV_VERSION", "avv-1")
    app = _prod(make_app, ONBOARDING_OPEN="1")
    assert app.state.settings.new_accounts_allowed
    with Client(app, base_url=APP) as c:
        _, _, r = _token_login(c, app, "neu@testfirma.example")
        assert r.status_code == 303
    assert not _prod(make_app, ONBOARDING_OPEN="0").state.settings.new_accounts_allowed  # flag off


def test_staging_and_test_keep_onboarding_open(make_app):
    assert make_app(APP_ENV="staging", SESSION_SECRET="s", CONSENT_HMAC_KEYS=f"c1:{K1}").state.settings.new_accounts_allowed
    assert make_app().state.settings.new_accounts_allowed
    with pytest.raises(RuntimeError, match="ONBOARDING_OPEN"):
        make_app(ONBOARDING_OPEN="yes")


# ================================================================== P0-4 AVV acceptance
def _csv():
    return (FIXTURES / "lexware_like.csv").read_bytes()


def test_upload_blocked_until_avv_accepted(client, app):
    csrf = login(client, app, avv=False)
    h = {"X-CSRF-Token": csrf}
    r = client.post("/api/v1/uploads", files={"file": ("r.csv", _csv(), "text/csv")}, headers=h)
    assert r.status_code == 403
    e = r.json()["error"]
    assert e["code"] == "avv_required" and "Auftragsverarbeitungsvertrag" in e["message_de"] and e["avv_version"] == AVV_VERSION
    page = client.get("/app/upload").text
    assert 'name="accept_avv"' in page and 'id="upload-form"' not in page
    assert checkbox_labels("avv", AVV_VERSION)[0] in _plain(page)
    assert '/avv/" rel="noopener">Vertrag über die Auftragsverarbeitung</a>' in page
    # without the tick: refused; without CSRF: refused; stale version: refused
    assert client.post("/api/v1/account/avv", json={"accept": False}, headers=h).status_code == 400
    assert client.post("/api/v1/account/avv", json={"accept": True}).status_code == 403
    assert client.post("/api/v1/account/avv", json={"accept": True, "avv_version": "avv-draft-0"}, headers=h).status_code == 409
    # the upload page form (no JS)
    r = client.post("/api/v1/account/avv", data={"csrf_token": csrf, "accept_avv": "1", "avv_version": AVV_VERSION},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/app/upload"
    u = app.state.db.one("SELECT avv_version, avv_accepted_at FROM users")
    assert u["avv_version"] == AVV_VERSION and u["avv_accepted_at"]
    assert 'id="upload-form"' in client.get("/app/upload").text
    r = client.post("/api/v1/uploads", files={"file": ("r.csv", _csv(), "text/csv")}, headers=h)
    assert r.status_code == 201, r.text
    exp = client.get("/api/v1/account/export").json()["account"]
    assert exp["avv_version"] == AVV_VERSION and exp["avv_accepted_at"]


def test_avv_asked_again_when_version_changes(client, app):
    csrf = login(client, app)
    app.state.db.execute("UPDATE users SET avv_version='avv-draft-0'")
    r = client.post("/api/v1/uploads", files={"file": ("r.csv", _csv(), "text/csv")}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 403 and r.json()["error"]["code"] == "avv_required"
    assert 'name="accept_avv"' in client.get("/app/upload").text


def test_avv_text_pinned():
    import app.settings as st
    assert "avv-draft-1" in legal_text("avv", "avv-draft-1")
    assert set(st.LEGAL_PINS) == {"consent", "terms", "avv"}


# ================================================================== P1-7 AI transfer guard
@pytest.mark.parametrize("env", ["staging", "prod"])
def test_anthropic_needs_transfer_clearance_outside_dev(make_app, env):
    extra = dict(APP_ENV=env, SESSION_SECRET="s", CONSENT_HMAC_KEYS=f"c1:{K1}", AI_PROVIDER="anthropic")
    if env == "prod":
        extra.update(MAILER="brevo", BREVO_API_KEY="dummy-not-used")
    with pytest.raises(RuntimeError, match="AI_TRANSFER_CLEARED=1"):
        make_app(**extra)
    assert make_app(AI_TRANSFER_CLEARED="1", **extra).state.settings.ai_provider == "anthropic"


def test_anthropic_in_dev_unaffected_and_default_heuristic(make_app, monkeypatch):
    assert make_app(AI_PROVIDER="anthropic").state.settings.ai_provider == "anthropic"
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    assert load_settings().ai_provider == "heuristic"


def test_no_inference_geo_set():
    # Anthropic's default inference geography is "global" (docs/legal/LAUNCH_COMPLIANCE.md); we do not set it.
    for f in list((ROOT / "app").glob("*.py")) + list((ROOT / "mapping").glob("*.py")):
        assert "inference_geo" not in f.read_text(encoding="utf-8"), f


def _content_blocks(path, heading: str) -> list[str]:
    """```text blocks between the "Checkbox-Text ..." line and the next Checkbox/section reference."""
    text = (ROOT / path).read_text(encoding="utf-8")
    section = text.split("\n" + heading + "\n", 1)[1]
    section = re.split(r"\n#+ |\nDer Text für den AVV|\nZugehöriger AGB-Text", section, maxsplit=1)[0]
    return [b.strip() for b in re.findall(r"```text\n(.*?)\n```", section, re.S)]


@pytest.mark.integration
def test_app_checkbox_texts_equal_content_blocks():
    agb = _content_blocks("content/legal/agb-entwurf.md", "Checkbox-Text agb-draft-2")
    avv = _content_blocks("content/legal/avv-entwurf.md", "Checkbox-Text avv-draft-1")
    assert agb == checkbox_labels("terms", "agb-draft-2")
    assert avv == checkbox_labels("avv", "avv-draft-1")
    for kind, v in (("terms", "agb-draft-2"), ("avv", "avv-draft-1")):
        assert "Platzhalter" not in legal_text(kind, v)
