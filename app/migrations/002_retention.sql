-- Wave 4 fixes: parse-once cache, consent proof after unsubscribe, purge indexes.

-- First non-empty value per column (max 60 chars) for the mapping page. Cell values:
-- deleted together with the raw upload (at conversion or after RETENTION_HOURS).
ALTER TABLE uploads ADD COLUMN samples_json TEXT;

-- Minimal proof of consent kept after unsubscribe (Art. 7(1) DSGVO): no address, only an HMAC of it.
CREATE TABLE consent_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email_hmac      TEXT NOT NULL,         -- HMAC-SHA256(SESSION_SECRET, lowercased e-mail)
    consent_version TEXT NOT NULL,
    requested_at    REAL,
    confirmed_at    REAL,
    unsubscribed_at REAL NOT NULL
);
CREATE INDEX consent_records_hmac ON consent_records(email_hmac);

CREATE INDEX events_created ON events(created_at);
CREATE INDEX users_last_login ON users(last_login_at);
