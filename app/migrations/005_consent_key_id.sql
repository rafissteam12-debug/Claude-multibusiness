-- Dedicated consent HMAC keys (CONSENT_HMAC_KEYS). Every record names the key its email_hmac was made with.
-- Records from before this migration were made with SESSION_SECRET: key id 'legacy-session'.
ALTER TABLE consent_records ADD COLUMN key_id TEXT NOT NULL DEFAULT 'legacy-session';
CREATE INDEX consent_records_key_hmac ON consent_records(key_id, email_hmac);
