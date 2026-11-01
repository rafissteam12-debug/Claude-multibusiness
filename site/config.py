"""Site configuration: the one place for brand names, URLs and flags.

Brand names, colours and the scope line are read from `contracts/brand.md`
(the single source of truth). URLs come from environment variables with the
defaults listed in `contracts/config.md`. STAGING is ON unless explicitly
switched off with SITE_STAGING=0 (see docs/requests/website.md). The usage
beacon is OFF unless SITE_EVENTS=1 (§ 25 TDDDG, pending legal review; docs/legal/PRE_REVIEW.md section 5).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SITE_DIR.parent
BRAND_MD = REPO_ROOT / "contracts" / "brand.md"

PLACEHOLDER = "[[BUSINESS_ID_PENDING]]"

# Event names the site may send; must be a subset of EVENTS_ALLOWED in contracts/config.md.
SITE_EVENTS = ("page_view", "link_click", "check_run", "subscribe")


class BrandParseError(RuntimeError):
    pass


def _grab(pattern: str, text: str, what: str) -> str:
    m = re.search(pattern, text)
    if not m:
        raise BrandParseError(f"contracts/brand.md: could not read {what}")
    return m.group(1).strip()


def load_brand(path: Path = BRAND_MD) -> dict:
    text = path.read_text(encoding="utf-8")
    brand = {
        "umbrella": _grab(r"Umbrella:\s*\*\*(.+?)\*\*", text, "umbrella name"),
        "product": _grab(r"Product:\s*\*\*(.+?)\*\*", text, "product name"),
        "presenter": _grab(r"Presenter:\s*\*\*(.+?)\*\*", text, "presenter name"),
        "scope_line": _grab(r"Scope line[^\n]*\n\s*\"(.+?)\"", text, "scope line"),
    }
    colours = {}
    for name, key in [
        ("teal", "teal"), ("dark teal", "dark_teal"), ("off-white", "off_white"),
        ("white", "white"), ("ink", "ink"), ("body", "body"), ("muted", "muted"),
        ("line", "line"), ("signal orange", "orange"), ("success", "success"),
    ]:
        colours[key] = _grab(r"(?<![\w-])" + re.escape(name) + r"\s*`(#[0-9A-Fa-f]{6})`", text, f"colour {name}")
    brand["colours"] = colours
    return brand


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


@dataclass
class SiteConfig:
    app_public_url: str
    site_public_url: str
    staging: bool
    brand: dict = field(default_factory=dict)
    placeholder: str = PLACEHOLDER
    events: tuple = SITE_EVENTS
    events_enabled: bool = False
    max_upload_mb: int = 5

    @property
    def active_events(self) -> tuple:
        """Events the browser may send; empty unless SITE_EVENTS=1."""
        return self.events if self.events_enabled else ()

    @property
    def api_base(self) -> str:
        return self.app_public_url.rstrip("/") + "/api/v1"


def load_config(**overrides) -> SiteConfig:
    cfg = SiteConfig(
        app_public_url=os.environ.get("APP_PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        site_public_url=os.environ.get("SITE_PUBLIC_URL", "http://localhost:8080").rstrip("/"),
        staging=_env_flag("SITE_STAGING", True),
        events_enabled=_env_flag("SITE_EVENTS", False),
        brand=load_brand(),
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg
