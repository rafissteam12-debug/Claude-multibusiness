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
