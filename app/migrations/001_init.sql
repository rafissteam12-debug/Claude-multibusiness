-- Belegbrücke app schema v1. Timestamps are epoch seconds (UTC). No raw IPs, no cell values
-- outside jobs.result_json / jobs.error_de / files (both purged after RETENTION_HOURS).

CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    plan          TEXT NOT NULL DEFAULT 'free',
    created_at    REAL NOT NULL,
    last_login_at REAL
);

CREATE TABLE sessions (
    id_hash    TEXT PRIMARY KEY,           -- sha256 of the cookie value
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE tokens (
    token_hash TEXT PRIMARY KEY,           -- HMAC-SHA256 of the token; raw tokens are never stored
    purpose    TEXT NOT NULL,              -- login | optin | unsubscribe
    email      TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    used_at    REAL
);
CREATE INDEX tokens_email ON tokens(email, purpose);

CREATE TABLE seller_profiles (
    user_id      TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    profile_json TEXT NOT NULL,
    updated_at   REAL NOT NULL
);

CREATE TABLE uploads (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT,                     -- NULL once the raw file is deleted
    ext          TEXT NOT NULL,
    size         INTEGER NOT NULL,
    row_count    INTEGER NOT NULL,
    columns_json TEXT NOT NULL,            -- column names only
    path         TEXT,
    created_at   REAL NOT NULL,
    deleted_at   REAL
);

CREATE TABLE mappings (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upload_id       TEXT,
    provider        TEXT NOT NULL,
    model           TEXT,
    mapping_json    TEXT NOT NULL,         -- column names, constants, transforms; never cell values
    columns_json    TEXT NOT NULL,
    save_for_reuse  INTEGER NOT NULL DEFAULT 0,
    confirmed       INTEGER NOT NULL DEFAULT 0,
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL
);

CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upload_id   TEXT NOT NULL,
    mapping_id  TEXT NOT NULL,
    formats     TEXT NOT NULL,
    profile     TEXT NOT NULL,
    status      TEXT NOT NULL,             -- queued | running | done | failed | expired
    result_json TEXT,                      -- per-invoice results (may contain cell values) -> purged
    error_de    TEXT,                      -- purged
    invoice_count INTEGER NOT NULL DEFAULT 0,
    valid_count   INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL,
    started_at  REAL,
    finished_at REAL,
    expired_at  REAL
);
CREATE INDEX jobs_user ON jobs(user_id, created_at);

CREATE TABLE files (
    id         TEXT PRIMARY KEY,
    job_id     TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,              -- xrechnung-cii | zugferd | pdf | zip
    filename   TEXT,
    media_type TEXT NOT NULL,
    path       TEXT,
    created_at REAL NOT NULL,
    deleted_at REAL
);

CREATE TABLE subscribers (
    email           TEXT PRIMARY KEY,
    consent_version TEXT NOT NULL,
    source          TEXT,
    requested_at    REAL NOT NULL,
    confirmed_at    REAL,
    unsubscribed_at REAL,
    welcome2_sent_at REAL
);

CREATE TABLE events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    path       TEXT,
    code       TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE usage (
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month       TEXT NOT NULL,             -- YYYY-MM (Europe/Berlin)
    valid_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, month)
);

CREATE TABLE rate_hits (
    bucket     TEXT NOT NULL,              -- e.g. check:<ip hash>, magic-email:<email hash>
    created_at REAL NOT NULL
);
CREATE INDEX rate_hits_bucket ON rate_hits(bucket, created_at);
