"""Static checks for content drafts (no network, stdlib only)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = sorted((ROOT / "guides").glob("*.md"))
SCOPE = ("Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten "
         "bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.")
BANNED = re.compile(r"rechtssicher|garantiert|testimonial", re.I)
PRICE = re.compile(r"\d+(?:,\d{2})?\s?(?:€|EUR)\s?(?:/|pro|im)\s?(?:Monat|Jahr)", re.I)


def front_matter(text: str) -> tuple[str, str]:
    assert text.startswith("---\n"), "front matter must start the file"
    fm, body = text[4:].split("\n---\n", 1)
    return fm, body


def test_five_guides():
    assert len(GUIDES) == 5


@pytest.mark.parametrize("path", GUIDES, ids=lambda p: p.stem)
def test_guide_front_matter_and_rules(path: Path):
    text = path.read_text(encoding="utf-8")
    fm, body = front_matter(text)
    keys = [l.split(":", 1)[0] for l in fm.splitlines() if l and not l.startswith(" ")]
    assert keys == ["title", "description", "slug", "sources", "last_checked"]
    desc = re.search(r'^description: "(.*)"$', fm, re.M).group(1)
    assert len(desc) <= 155
    slug = re.search(r'^slug: "(.*)"$', fm, re.M).group(1)
    assert slug == path.stem and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug)
    urls = re.findall(r'^    url: "(.*)"$', fm, re.M)
    assert len(urls) >= 3 and all(u.startswith("https://") for u in urls)
    assert re.search(r'^last_checked: "\d{4}-\d{2}-\d{2}"$', fm, re.M)
    words = len(re.findall(r"\w+", re.sub(r"\(https?://[^)]*\)", "", body)))
    assert 600 <= words <= 1100, words
    assert SCOPE in body
    assert "/e-rechnung-pruefen" in body
    assert not BANNED.search(text)
    # every inline link in the body is one of the listed sources or internal
    for url in re.findall(r"\]\((https?://[^)]+)\)", body):
        assert url in urls, f"inline source not in front matter: {url}"


def test_no_prices_or_banned_words_in_user_facing_texts():
    for folder in ("emails", "help"):
        for p in (ROOT / folder).glob("*.md"):
            t = p.read_text(encoding="utf-8")
            assert not BANNED.search(t), p
            assert not PRICE.search(t), p


def test_emails_have_subject_and_footer_placeholder():
    footer = (ROOT / "emails" / "_footer.md").read_text(encoding="utf-8")
    assert "[[BUSINESS_ID_PENDING]]" in footer and SCOPE in footer
    for p in sorted((ROOT / "emails").glob("0*.md")):
        t = p.read_text(encoding="utf-8")
        assert t.startswith("Betreff: "), p
        assert '{% include "_footer.md" %}' in t, p


def test_ada_posts_disclosed_and_tracked():
    posts = sorted(p for p in (ROOT / "ada" / "posts").iterdir() if p.is_dir())
    assert [p.name[:6] for p in posts] == ["ig-001", "ig-002", "ig-003", "ig-004"]
    for p in posts:
        md = (p / "post.md").read_text(encoding="utf-8")
        assert f"`{p.name[:6]}`" in md
        assert "#KI-generiert" in md and "Link in der Bio" in md
        assert not BANNED.search(md.replace("rechtssicher / garantiert", ""))
        slides = p / "slides.json"
        if slides.exists():
            data = json.loads(slides.read_text(encoding="utf-8"))
            for i, s in enumerate(data["slides"], 1):
                svg = (p / f"slide-{i}.svg").read_text(encoding="utf-8")
                assert "KI-generiert" in svg and 'width="1080" height="1350"' in svg
                assert (p / f"slide-{i}.png").exists()
                assert s["alt"]
                if "ig-004" in p.name:
                    assert "Demo mit erfundenen Daten" in svg
            assert "ada-avatar-plain.svg" in (p / "slide-1.svg").read_text(encoding="utf-8")


def test_ada_bio_discloses():
    assert "KI-generiert" in (ROOT / "ada" / "bio.md").read_text(encoding="utf-8")


SHIPPED_DIRS = ("guides", "emails", "help", "ada", "legal")
SHIPPED_SUFFIXES = {".md", ".json", ".svg", ".txt", ".html"}


def shipped_files():
    for d in SHIPPED_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.suffix in SHIPPED_SUFFIXES:
                yield p


def test_no_unverified_notes_in_shipped_content():
    """Review H2: `[prüfen …]` notes must never reach users; open points go to docs/progress/content.md."""
    files = list(shipped_files())
    assert len(files) > 20
    hits = [f"{p.relative_to(ROOT)}:{n}" for p in files
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if re.search(r"\[\s*(prüfen|pruefen)", line, re.I)]
    assert not hits, hits


def test_privacy_facts_use_placeholder_and_no_legal_conclusions():
    t = (ROOT / "legal" / "datenschutz-fakten.md").read_text(encoding="utf-8")
    assert "[[BUSINESS_ID_PENDING]]" in t
    assert not BANNED.search(t)
    for needle in ("7 Tage", "24 Stunden", "Brevo", "Anthropic", "Cloudflare", "IBAN", "12 Monate"):
        assert needle in t, needle


def _fenced_after(text: str, title: str) -> str:
    m = re.search(re.escape(title) + r"\n\n```text\n(.+?)\n```", text)
    assert m, title
    return m.group(1)


def test_agb_draft_2_complete_and_safe():
    t = (ROOT / "legal" / "agb-entwurf.md").read_text(encoding="utf-8")
    fm, body = front_matter(t)
    assert 'version: "agb-draft-2"' in fm
    assert "Entwurf – nicht freigegeben, vor Verwendung anwaltlich prüfen" in t
    assert SCOPE in body
    assert "[[BUSINESS_ID_PENDING]]" in body and not PRICE.search(t) and not BANNED.search(t)
    for needle in ("§ 14 BGB", "Verbraucher", "24 Stunden", "12 Monaten", "avv-draft-1", "außerhalb der EU",
                   "Formulierung anwaltlich prüfen", "Produkthaftungsgesetz", "Kardinalpflicht", "übersprungen",
                   "Versionskennung", "Konto löschen"):
        assert needle in body, needle
    label = _fenced_after(body, "Checkbox-Text agb-draft-2")
    assert "agb-draft-2" in label and "\n" not in label


def test_avv_draft_1_acceptance_block():
    t = (ROOT / "legal" / "avv-entwurf.md").read_text(encoding="utf-8")
    fm, body = front_matter(t)
    assert 'version: "avv-draft-1"' in fm
    assert "Annahme und Nachweis" in body and "Datenexport" in body
    label = _fenced_after(body, "Checkbox-Text avv-draft-1")
    assert "avv-draft-1" in label and "\n" not in label


def test_privacy_facts_record_verified_versions():
    t = (ROOT / "legal" / "datenschutz-fakten.md").read_text(encoding="utf-8")
    assert "Version 6.4" in t and "6.3" not in t.replace("„v6.3“", "")
    assert "AI_TRANSFER_CLEARED" in t and "inference_geo" in t and "Anthropic Console" in t
    assert "geplant – wird mit Servereinrichtung aktiv" in t
