"""Consent proof (owner decision 1 Nov 2026): evidence, withdrawal, suppression. HMAC only, no plain address."""
from __future__ import annotations

from . import clock

WITHDRAWAL_METHODS = ("link", "reply")


def withdraw(db, sec, email: str, method: str = "link", now: float | None = None) -> bool:
    """Remove the subscription and record the withdrawal on the open consent record. True if anything was found."""
    if method not in WITHDRAWAL_METHODS:
        raise ValueError("unknown withdrawal method")
    email = email.strip().lower()
    now = clock.now() if now is None else now
    h = sec.consent_hmac(email)
    with db.tx() as conn:
        sub = conn.execute("SELECT consent_version, source, requested_at, confirmed_at FROM subscribers WHERE email=?",
                           (email,)).fetchone()
        n = conn.execute("UPDATE consent_records SET unsubscribed_at=?, method=? WHERE id=(SELECT MAX(id) FROM "
                         "consent_records WHERE email_hmac=? AND unsubscribed_at IS NULL)", (now, method, h)).rowcount
        if not n and sub and sub["confirmed_at"]:  # confirmed before consent records existed
            conn.execute("INSERT INTO consent_records (email_hmac, consent_version, source, requested_at, confirmed_at, "
                         "unsubscribed_at, method) VALUES (?,?,?,?,?,?,?)",
                         (h, sub["consent_version"], sub["source"], sub["requested_at"], sub["confirmed_at"], now, method))
            n = 1
        d = conn.execute("DELETE FROM subscribers WHERE email=?", (email,)).rowcount
        conn.execute("DELETE FROM tokens WHERE email=? AND purpose IN ('optin','unsubscribe')", (email,))
    return bool(n or d)
