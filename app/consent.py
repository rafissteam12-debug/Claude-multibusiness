"""Consent proof (owner decision 1 Nov 2026): evidence, withdrawal, suppression. HMAC only, no plain address.

Records carry the id of the consent key their HMAC was made with (CONSENT_HMAC_KEYS, plus `legacy-session`).
Matching an address computes its HMAC under every configured key and matches by (key_id, email_hmac).
"""
from __future__ import annotations

from . import clock

WITHDRAWAL_METHODS = ("link", "reply")


def match_clause(sec, email: str) -> tuple[str, list]:
    """SQL condition and params matching consent records of `email` under every configured key."""
    pairs = sec.consent_hmacs(email)
    cond = "(" + " OR ".join("(key_id=? AND email_hmac=?)" for _ in pairs) + ")"
    return cond, [v for pair in pairs for v in pair]


def insert_record(conn, sec, email: str, consent_version, source, requested_at, confirmed_at,
                  unsubscribed_at=None, method=None) -> None:
    """A new consent record, signed with the current consent key."""
    conn.execute("INSERT INTO consent_records (email_hmac, key_id, consent_version, source, requested_at, confirmed_at, "
                 "unsubscribed_at, method) VALUES (?,?,?,?,?,?,?,?)",
                 (sec.consent_hmac(email), sec.consent_key_id, consent_version, source, requested_at, confirmed_at,
                  unsubscribed_at, method))


def withdraw(db, sec, email: str, method: str = "link", now: float | None = None) -> bool:
    """Remove the subscription and record the withdrawal on the open consent record. True if anything was found."""
    if method not in WITHDRAWAL_METHODS:
        raise ValueError("unknown withdrawal method")
    email = email.strip().lower()
    now = clock.now() if now is None else now
    cond, params = match_clause(sec, email)
    with db.tx() as conn:
        sub = conn.execute("SELECT consent_version, source, requested_at, confirmed_at FROM subscribers WHERE email=?",
                           (email,)).fetchone()
        n = conn.execute("UPDATE consent_records SET unsubscribed_at=?, method=? WHERE id=(SELECT MAX(id) FROM "
                         f"consent_records WHERE {cond} AND unsubscribed_at IS NULL)", (now, method, *params)).rowcount
        if not n and sub and sub["confirmed_at"]:  # confirmed before consent records existed
            insert_record(conn, sec, email, sub["consent_version"], sub["source"], sub["requested_at"], sub["confirmed_at"],
                          now, method)
            n = 1
        d = conn.execute("DELETE FROM subscribers WHERE email=?", (email,)).rowcount
        conn.execute("DELETE FROM tokens WHERE email=? AND purpose IN ('optin','unsubscribe')", (email,))
    return bool(n or d)
