"""Hashing, single-use tokens, sessions, rate limits, CSRF and origin checks (contracts/api.md, Security rules)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid

from . import clock
from .db import Database
from .settings import SESSION_TTL_SECONDS, TOKEN_TTL_SECONDS, Settings

SESSION_COOKIE = "bb_session"
PRE_COOKIE = "bb_pre"  # anonymous CSRF cookie (login, confirm pages)


class Security:
    def __init__(self, settings: Settings, db: Database):
        self.s = settings
        self.db = db
        self._key = settings.session_secret.encode()

    # ------------------------------------------------------------- hashing
    def hmac_hex(self, purpose: str, value: str) -> str:
        return hmac.new(self._key, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()

    def ip_hash(self, ip: str | None) -> str:
        """Salted hash of the client IP; raw IPs are never stored."""
        return self.hmac_hex("ip", ip or "unknown")[:32]

    def email_hash(self, email: str) -> str:
        return self.hmac_hex("email", email.lower())[:32]

    # ------------------------------------------------------------- tokens
    def issue_token(self, purpose: str, email: str, ttl: float = TOKEN_TTL_SECONDS) -> str:
        raw = secrets.token_urlsafe(32)
        now = clock.now()
        self.db.execute(
            "INSERT INTO tokens (token_hash, purpose, email, created_at, expires_at) VALUES (?,?,?,?,?)",
            (self.hmac_hex("token", raw), purpose, email, now, now + ttl))
        return raw

    def peek_token(self, purpose: str, raw: str | None) -> str | None:
        """Return the e-mail of a usable token without consuming it (GET pages)."""
        if not raw or len(raw) > 200:
            return None
        row = self.db.one("SELECT email, expires_at, used_at FROM tokens WHERE token_hash=? AND purpose=?",
                          (self.hmac_hex("token", raw), purpose))
        if not row or row["used_at"] is not None or row["expires_at"] < clock.now():
            return None
        return row["email"]

    def consume_token(self, purpose: str, raw: str | None) -> str | None:
        """Single use: atomically mark the token used. Returns the e-mail or None."""
        if not raw or len(raw) > 200:
            return None
        h = self.hmac_hex("token", raw)
        now = clock.now()
        with self.db.tx() as conn:
            row = conn.execute("SELECT email FROM tokens WHERE token_hash=? AND purpose=? AND used_at IS NULL AND expires_at>=?",
                               (h, purpose, now)).fetchone()
            if not row:
                return None
            conn.execute("UPDATE tokens SET used_at=? WHERE token_hash=?", (now, h))
            return row["email"]

    # ------------------------------------------------------------- sessions
    def create_session(self, user_id: str) -> str:
        raw = secrets.token_urlsafe(32)
        now = clock.now()
        self.db.execute("INSERT INTO sessions (id_hash, user_id, csrf_token, created_at, expires_at) VALUES (?,?,?,?,?)",
                        (self.hmac_hex("session", raw), user_id, secrets.token_urlsafe(32), now, now + SESSION_TTL_SECONDS))
        return raw

    def session(self, raw: str | None):
        if not raw or len(raw) > 200:
            return None
        row = self.db.one(
            "SELECT s.user_id, s.csrf_token, s.expires_at, u.email, u.plan FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.id_hash=?", (self.hmac_hex("session", raw),))
        if not row or row["expires_at"] < clock.now():
            return None
        return row

    def end_session(self, raw: str | None) -> None:
        if raw:
            self.db.execute("DELETE FROM sessions WHERE id_hash=?", (self.hmac_hex("session", raw),))

    def pre_csrf(self, pre_cookie: str | None) -> str | None:
        """CSRF token for anonymous forms: bound to the bb_pre cookie (double submit, signed)."""
        if not pre_cookie or len(pre_cookie) > 200:
            return None
        return self.hmac_hex("pre-csrf", pre_cookie)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    # ------------------------------------------------------------- rate limits
    def rate_limited(self, bucket: str, limit: int, window: float = 3600, record: bool = True) -> bool:
        """True if `bucket` already has `limit` hits in the window. Records a hit otherwise."""
        now = clock.now()
        with self.db.tx() as conn:
            n = conn.execute("SELECT COUNT(*) FROM rate_hits WHERE bucket=? AND created_at>?", (bucket, now - window)).fetchone()[0]
            if n >= limit:
                return True
            if record:
                conn.execute("INSERT INTO rate_hits (bucket, created_at) VALUES (?,?)", (bucket, now))
            return False

    # ------------------------------------------------------------- origin
    def same_origin(self, headers) -> bool:
        """Origin must equal APP_PUBLIC_URL's origin; without Origin, Sec-Fetch-Site must be same-origin."""
        origin = headers.get("origin")
        sfs = headers.get("sec-fetch-site")
        if sfs and sfs != "same-origin":
            return False
        if origin:
            return origin.lower().rstrip("/") == self.s.app_origin
        return headers.get("sec-fetch-site") == "same-origin"

    @staticmethod
    def equal(a: str | None, b: str | None) -> bool:
        return bool(a) and bool(b) and hmac.compare_digest(a, b)
