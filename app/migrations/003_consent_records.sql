-- Consent proof in three parts (owner decision, 1 Nov 2026; kept 3 years, minimum data):
--   consent evidence:    email_hmac, consent_version, source, requested_at, confirmed_at   (written at confirmation)
--   withdrawal evidence: unsubscribed_at, method ('link')                                    (written at unsubscribe)
--   suppression use:     a later /subscribe for the same HMAC still needs the full double opt-in and creates a NEW row.
-- No plain e-mail, no IP, no user agent.
CREATE TABLE consent_records_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email_hmac      TEXT NOT NULL,         -- HMAC-SHA256(SESSION_SECRET, lowercased e-mail)
    consent_version TEXT NOT NULL,
    source          TEXT,                  -- /subscribe "source": check | guide | ig-...
    requested_at    REAL,
    confirmed_at    REAL NOT NULL,
    unsubscribed_at REAL,
    method          TEXT                   -- withdrawal method: 'link'
);
INSERT INTO consent_records_new (id, email_hmac, consent_version, requested_at, confirmed_at, unsubscribed_at, method)
    SELECT id, email_hmac, consent_version, requested_at, COALESCE(confirmed_at, requested_at, unsubscribed_at), unsubscribed_at, 'link'
    FROM consent_records;
DROP TABLE consent_records;
ALTER TABLE consent_records_new RENAME TO consent_records;
CREATE INDEX consent_records_hmac ON consent_records(email_hmac);
