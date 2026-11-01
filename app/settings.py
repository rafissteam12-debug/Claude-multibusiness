"""Configuration from environment variables (contracts/config.md) and brand names (contracts/brand.md).

Brand names and the scope line are read from contracts/brand.md so a rename is one edit there.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"
CONTENT_DIR = REPO_ROOT / "content"
PLACEHOLDER = "[[BUSINESS_ID_PENDING]]"

DEFAULT_EVENTS = "page_view,link_click,check_run,subscribe,upload,mapping_confirmed,conversion_done"
CONSENT_VERSIONS = ("2026-10-31-v1",)  # consent texts this server knows (contracts/api.md)
CURRENT_CONSENT_VERSION = CONSENT_VERSIONS[-1]
LEGAL_TEXTS_DIR = APP_DIR / "legal_texts"
# Verbatim texts per version (legal pre-review 6.4). A wording change needs a NEW version and a new file;
# the hashes pin the files so an old version can never be edited silently.
CONSENT_TEXT_SHA256 = {"2026-10-31-v1": "dcd2492a668fafefa1441f91990ad22ab2bd93979c4d28cb4b96c4a27c5678b5"}
# AGB versions: agb-draft-1 stays pinned for acceptances already recorded; new acceptances use the current version.
TERMS_VERSION = "agb-draft-2"
TERMS_TEXT_SHA256 = {"agb-draft-1": "3d88e7f59fb73f254df28d15b8b27f36359071dac4d36fa793318ddb4df34bce",
                     "agb-draft-2": "033d66ee6342e9f15a8f9373d82499c9e8ed8f5126eaa6b29b1a0a36829898bf"}
# AVV (Auftragsverarbeitungsvertrag) acceptance, asked before the first upload and again when the version changes.
AVV_VERSION = "avv-draft-1"
AVV_TEXT_SHA256 = {"avv-draft-1": "eb7b664c821c366088aac927327bc1422b7e8561ca1fdf862d0b94688d97c1c7"}
LEGAL_PINS = {"consent": CONSENT_TEXT_SHA256, "terms": TERMS_TEXT_SHA256, "avv": AVV_TEXT_SHA256}
CHECKBOX_PREFIX = "[Kontrollkästchen] "
LEGACY_CONSENT_KEY_ID = "legacy-session"  # consent records hashed with SESSION_SECRET (before CONSENT_HMAC_KEYS)
PLAN_LIMITS = {"free": 3, "start": 30, "business": 300}

CHECK_MAX_BYTES = 5 * 1024 * 1024
UPLOAD_MAX_BYTES = 10 * 1024 * 1024
JSON_MAX_BYTES = 256 * 1024
TOKEN_TTL_SECONDS = 15 * 60
SESSION_TTL_SECONDS = 7 * 24 * 3600
UNSUBSCRIBE_TTL_SECONDS = 365 * 24 * 3600
MAX_INVOICES_PER_JOB = 500


@lru_cache(maxsize=1)
def brand() -> dict:
    text = (CONTRACTS_DIR / "brand.md").read_text(encoding="utf-8")

    def grab(pattern: str) -> str:
        m = re.search(pattern, text)
        if not m:
            raise RuntimeError(f"contracts/brand.md: pattern {pattern!r} not found")
        return m.group(1).strip()

    colours = {}
    for name, key in [("teal", "teal"), ("dark teal", "dark_teal"), ("off-white", "off_white"),
                      ("white", "white"), ("ink", "ink"), ("body", "body"), ("muted", "muted"),
                      ("line", "line"), ("signal orange", "orange"), ("success", "success")]:
        colours[key] = grab(r"(?<![\w-])" + re.escape(name) + r"\s*`(#[0-9A-Fa-f]{6})`")
    return {
        "umbrella": grab(r"Umbrella:\s*\*\*(.+?)\*\*"),
        "product": grab(r"Product:\s*\*\*(.+?)\*\*"),
        "scope_line": grab(r"Scope line[^\n]*\n\s*\"(.+?)\""),
        "colours": colours,
    }


def _origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}".lower()


@dataclass
class Settings:
    app_env: str = "dev"
    app_public_url: str = "http://localhost:8000"
    site_public_url: str = "http://localhost:8080"
    database_path: Path = Path("./var/app.db")
    temp_dir: Path = Path("./var/tmp")
    session_secret: str = ""
    mailer: str = "console"
    brevo_api_key: str = ""
    mail_from: str = "ablaufwerkinfo@gmail.com"
    ai_provider: str = "heuristic"
    events_allowed: frozenset = field(default_factory=lambda: frozenset(DEFAULT_EVENTS.split(",")))
    retention_hours: float = 24.0
    secret_was_generated: bool = False
    # Consent HMAC keyring: ((key_id, key bytes), ...); the first entry signs new records, all entries are matched.
    consent_keys: tuple = ()
    onboarding_open: bool = False
    ai_transfer_cleared: bool = False

    @property
    def consent_key_id(self) -> str:
        return self.consent_keys[0][0]

    @property
    def new_accounts_allowed(self) -> bool:
        """In prod, new accounts need ONBOARDING_OPEN=1 and final (non-draft) AGB and AVV versions. Staging/dev/test: open."""
        if self.app_env != "prod":
            return True
        return self.onboarding_open and not TERMS_VERSION.startswith("agb-draft") and not AVV_VERSION.startswith("avv-draft")

    @property
    def app_origin(self) -> str:
        return _origin(self.app_public_url)

    @property
    def site_origin(self) -> str:
        return _origin(self.site_public_url)

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    @property
    def show_staging_banner(self) -> bool:
        return self.app_env != "prod"

    @property
    def secure_cookies(self) -> bool:
        return self.app_public_url.lower().startswith("https://") or self.app_env in ("staging", "prod")

    @property
    def retention_seconds(self) -> float:
        return self.retention_hours * 3600

    @property
    def zugferd_available(self) -> bool:
        return bool(os.environ.get("MUSTANG_JAR"))


def load_settings() -> Settings:
    env = os.environ.get
    app_env = (env("APP_ENV") or "dev").strip().lower()
    if app_env not in ("dev", "test", "staging", "prod"):
        raise RuntimeError("APP_ENV must be dev, test, staging or prod")
    secret = env("SESSION_SECRET") or ""
    generated = False
    if not secret or secret == "change-me":
        if app_env in ("staging", "prod"):
            raise RuntimeError("SESSION_SECRET is required outside dev/test")
        secret = secrets.token_hex(32)
        generated = True
    mailer = (env("MAILER") or "console").strip().lower()
    if mailer not in ("console", "brevo"):
        raise RuntimeError("MAILER must be console or brevo")
    if mailer == "console" and app_env == "prod":
        raise RuntimeError("MAILER=console is not allowed in prod")
    if mailer == "brevo" and not env("BREVO_API_KEY"):
        raise RuntimeError("MAILER=brevo needs BREVO_API_KEY")
    consent_keys = parse_consent_keys(env("CONSENT_HMAC_KEYS") or "", secret, app_env)
    ai_provider = (env("AI_PROVIDER") or "heuristic").strip().lower()
    ai_cleared = (env("AI_TRANSFER_CLEARED") or "0").strip() == "1"
    if ai_provider == "anthropic" and app_env in ("staging", "prod") and not ai_cleared:
        raise RuntimeError("AI_PROVIDER=anthropic needs AI_TRANSFER_CLEARED=1 in staging/prod (international transfer "
                           "to Anthropic not yet cleared, docs/legal/LAUNCH_COMPLIANCE.md section 2); use AI_PROVIDER=heuristic")
    onboarding = (env("ONBOARDING_OPEN") or "0").strip()
    if onboarding not in ("0", "1"):
        raise RuntimeError("ONBOARDING_OPEN must be 0 or 1")
    events = env("EVENTS_ALLOWED") or DEFAULT_EVENTS
    try:
        retention = float(env("RETENTION_HOURS") or 24)
    except ValueError:
        raise RuntimeError("RETENTION_HOURS must be a number") from None
    return Settings(
        app_env=app_env,
        app_public_url=(env("APP_PUBLIC_URL") or "http://localhost:8000").rstrip("/"),
        site_public_url=(env("SITE_PUBLIC_URL") or "http://localhost:8080").rstrip("/"),
        database_path=Path(env("DATABASE_PATH") or "./var/app.db"),
        temp_dir=Path(env("TEMP_DIR") or "./var/tmp"),
        session_secret=secret,
        mailer=mailer,
        brevo_api_key=env("BREVO_API_KEY") or "",
        mail_from=env("MAIL_FROM") or "ablaufwerkinfo@gmail.com",
        ai_provider=ai_provider,
        events_allowed=frozenset(e.strip() for e in events.split(",") if e.strip()),
        retention_hours=retention,
        secret_was_generated=generated,
        consent_keys=consent_keys,
        onboarding_open=onboarding == "1",
        ai_transfer_cleared=ai_cleared,
    )


_KEY_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def parse_consent_keys(raw: str, session_secret: str, app_env: str) -> tuple:
    """CONSENT_HMAC_KEYS = "keyid:base64key,keyid2:base64key2" (first = current signing key).

    `legacy-session` is the key of records created before dedicated keys existed: HMAC with SESSION_SECRET. If it is
    not listed, it is added implicitly (last) with the CURRENT SESSION_SECRET. After rotating SESSION_SECRET, list the
    old secret explicitly as `legacy-session:<old SESSION_SECRET>` (raw value, not base64) to keep old records
    matchable. Staging/prod refuse to start without a dedicated current key, or when it equals SESSION_SECRET.
    """
    keys: list[tuple[str, bytes]] = []
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        kid, sep, val = part.partition(":")
        kid = kid.strip()
        if not sep or not _KEY_ID_RE.match(kid) or not val:
            raise RuntimeError("CONSENT_HMAC_KEYS: each entry must be keyid:base64key")
        if any(k == kid for k, _ in keys):
            raise RuntimeError("CONSENT_HMAC_KEYS: duplicate key id")
        if kid == LEGACY_CONSENT_KEY_ID:
            key = val.encode()
        else:
            try:
                key = base64.b64decode(val.strip(), validate=True)
            except (binascii.Error, ValueError):
                raise RuntimeError("CONSENT_HMAC_KEYS: key is not valid base64") from None
            if len(key) < 32:
                raise RuntimeError("CONSENT_HMAC_KEYS: keys must be at least 32 bytes")
        keys.append((kid, key))
    if app_env in ("staging", "prod"):
        if not keys:
            raise RuntimeError("CONSENT_HMAC_KEYS is required outside dev/test")
        if keys[0][0] == LEGACY_CONSENT_KEY_ID:
            raise RuntimeError("CONSENT_HMAC_KEYS: the current (first) key must be a dedicated key, not legacy-session")
        if keys[0][1] == session_secret.encode():
            raise RuntimeError("CONSENT_HMAC_KEYS: the current key must differ from SESSION_SECRET")
    if not any(k == LEGACY_CONSENT_KEY_ID for k, _ in keys):
        keys.append((LEGACY_CONSENT_KEY_ID, session_secret.encode()))
    return tuple(keys)


def legal_text(kind: str, version: str) -> str:
    """Verbatim consent ('consent'), terms ('terms') or AVV ('avv') text of a version; raises if missing or changed."""
    pins = LEGAL_PINS[kind]
    if version not in pins:
        raise RuntimeError(f"no stored {kind} text for version {version}")
    data = (LEGAL_TEXTS_DIR / f"{kind}-{version}.txt").read_bytes()
    if hashlib.sha256(data).hexdigest() != pins[version]:
        raise RuntimeError(f"{kind} text {version} was changed; create a new version instead")
    return data.decode("utf-8")


def checkbox_labels(kind: str, version: str) -> list[str]:
    """The verbatim checkbox labels (lines starting with "[Kontrollkästchen] ") of a stored legal text."""
    return [ln[len(CHECKBOX_PREFIX):].strip() for ln in legal_text(kind, version).splitlines() if ln.startswith(CHECKBOX_PREFIX)]
