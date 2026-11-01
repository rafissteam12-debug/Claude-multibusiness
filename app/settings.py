"""Configuration from environment variables (contracts/config.md) and brand names (contracts/brand.md).

Brand names and the scope line are read from contracts/brand.md so a rename is one edit there.
"""
from __future__ import annotations

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
TERMS_VERSION = "agb-draft-1"
TERMS_TEXT_SHA256 = {"agb-draft-1": "3d88e7f59fb73f254df28d15b8b27f36359071dac4d36fa793318ddb4df34bce"}
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
        ai_provider=(env("AI_PROVIDER") or "heuristic").strip().lower(),
        events_allowed=frozenset(e.strip() for e in events.split(",") if e.strip()),
        retention_hours=retention,
        secret_was_generated=generated,
    )


def legal_text(kind: str, version: str) -> str:
    """Verbatim consent ('consent') or terms ('terms') text of a version; raises if missing or changed."""
    pins = CONSENT_TEXT_SHA256 if kind == "consent" else TERMS_TEXT_SHA256
    if version not in pins:
        raise RuntimeError(f"no stored {kind} text for version {version}")
    import hashlib
    data = (LEGAL_TEXTS_DIR / f"{kind}-{version}.txt").read_bytes()
    if hashlib.sha256(data).hexdigest() != pins[version]:
        raise RuntimeError(f"{kind} text {version} was changed; create a new version instead")
    return data.decode("utf-8")
