-- AGB acceptance and B2B statement per user (legal pre-review 8.1/9.10). Asked before the account exists and again
-- at the next login when the stored version differs from the current one. Exact texts: app/legal_texts/terms-<version>.txt
ALTER TABLE users ADD COLUMN terms_version TEXT;
ALTER TABLE users ADD COLUMN terms_accepted_at REAL;
ALTER TABLE users ADD COLUMN b2b_confirmed_at REAL;
-- Withdrawal method may now also be 'reply' (manual unsubscribe by e-mail reply, `python -m app.admin`).
