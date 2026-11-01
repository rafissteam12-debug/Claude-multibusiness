"""Privacy page and AGB draft stay in line with content/legal (P1-8; remediation release)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FAKTEN = REPO_ROOT / "content" / "legal" / "datenschutz-fakten.md"
GERMAN_MONTHS = {"January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai",
                 "June": "Juni", "July": "Juli", "August": "August", "September": "September",
                 "October": "Oktober", "November": "November", "December": "Dezember"}

# Wording that would claim the strict log retention (daily rotation, 14-day deletion, journald limits) is active.
ACTIVE_RETENTION_CLAIMS = [
    r"14 Tage[^.]{0,40}(konfiguriert|eingestellt|aktiv\b)",
    r"\b(ist|sind) (konfiguriert|eingestellt|aktiv)\b[^.]{0,40}tägliche Rotation",
    r"werden täglich rotiert",
    r"Protokolle werden nach 14 Tagen gelöscht",
    r"14 Tage für rotierte Dateien",
    r"strenge Altersgrenze (ist|wird) gesetzt",
]


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.fixture(scope="module")
def fakten() -> str:
    return FAKTEN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def privacy(pages) -> str:
    return _text(pages["datenschutz/index.html"])


def test_strict_log_retention_not_claimed_while_planned(fakten, privacy):
    journald = next(line for line in fakten.splitlines() if "MaxRetentionSec" in line)
    if "geplant" not in journald:
        pytest.skip("datenschutz-fakten.md no longer marks strict log retention as planned; review the page wording")
    assert "Ausgelegt auf 14 Tage; wird mit der Servereinrichtung aktiviert" in privacy
    assert "ausgelegt auf 14 Tage; wird mit der Servereinrichtung aktiviert" in privacy
    for pattern in ACTIVE_RETENTION_CLAIMS:
        assert not re.search(pattern, privacy), pattern


def test_cloudflare_dpa_version_matches_fakten(fakten, privacy):
    m = re.search(r"Version (\d+\.\d+), „effective (\w+) (\d{1,2}), (\d{4})“", fakten)
    assert m, "Cloudflare DPA version not found in datenschutz-fakten.md"
    version, month, day, year = m.groups()
    expected = f"Version {version}, gültig ab {int(day)}. {GERMAN_MONTHS[month]} {year}"
    assert expected in privacy
    assert "(laut Cloudflare-Seite, geprüft 1. Nov. 2026" in privacy and "am **1. Nov. 2026**" in fakten
    assert not re.search(r"Version 6\.3\b|v6\.3", privacy)


def test_ai_mapping_described_as_off_by_default(fakten, privacy):
    assert "**Standard: aus**" in fakten
    assert "Die KI-Unterstützung ist standardmäßig aus" in privacy
    assert "erst nach rechtlicher Freigabe der Übermittlung eingeschaltet" in privacy
    assert "Standard „global“" in privacy and "`global`" in fakten
    assert "bestätigt der Betreiber vor dem Einschalten" in privacy


# ---------- AGB draft from content/legal ----------

def test_agb_page_rendered_from_content(pages, parsed, dist):
    html = pages["agb/index.html"]
    assert "agb-draft-2" in html
    assert "Entwurf – nicht freigegeben" in html
    assert "[[BUSINESS_ID_PENDING]]" in html
    assert parsed["agb/index.html"].headings.count(1) == 1
    assert "/agb/" in (dist / "sitemap.xml").read_text(encoding="utf-8")


def test_agb_missing_fails_build(site_build, staging_cfg, monkeypatch, tmp_path):
    legal = tmp_path / "legal"
    legal.mkdir()
    avv = REPO_ROOT / "content" / "legal" / "avv-entwurf.md"
    (legal / "avv-entwurf.md").write_text(avv.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(site_build, "CONTENT_LEGAL", legal)
    with pytest.raises(site_build.GuideError, match="agb-entwurf.md"):
        site_build.build(tmp_path / "out", staging_cfg)
