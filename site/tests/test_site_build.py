"""Build succeeds; pages exist; guide loading rules; staging on/off."""
from __future__ import annotations

import pytest

EXPECTED = [
    "index.html", "belegbruecke/index.html", "e-rechnung-pruefen/index.html", "ratgeber/index.html",
    "impressum/index.html", "datenschutz/index.html", "agb/index.html", "bestaetigt/index.html", "404.html",
]


def test_build_creates_all_pages(dist):
    for rel in EXPECTED:
        assert (dist / rel).is_file(), rel
    for rel in ("_headers", "robots.txt", "sitemap.xml", "static/style.css", "static/brand.css",
                "static/checker.js", "static/site.js", "static/mock-report.json"):
        assert (dist / rel).is_file(), rel


def test_every_guide_has_page_and_sources(site_build, dist):
    guides, _ = site_build.load_guides()
    assert guides, "at least one guide (content or fixture)"
    for g in guides:
        html = (dist / "ratgeber" / g["slug"] / "index.html").read_text(encoding="utf-8")
        assert "Zuletzt geprüft am " + g["last_checked_de"] in html
        for s in g["sources"]:
            assert s["url"] in html
        assert f'href="{g["path"]}"' in (dist / "ratgeber/index.html").read_text(encoding="utf-8")


def test_brand_values_come_from_contract(site_build, staging_cfg, pages):
    from pathlib import Path
    brand_md = (Path(site_build.REPO_ROOT) / "contracts" / "brand.md").read_text(encoding="utf-8")
    assert staging_cfg.brand["product"] in brand_md
    assert staging_cfg.brand["scope_line"] in brand_md
    assert staging_cfg.brand["colours"]["teal"] == "#0F4C5C"
    for name, html in pages.items():
        assert staging_cfg.brand["scope_line"] in html, f"scope line missing on {name}"


GUIDE = """---
title: "Testratgeber"
description: "Kurz."
slug: test-ratgeber
last_checked: 2026-10-01
sources:
  - {title: "BMF", url: "https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html"}
---
## Abschnitt

Text mit [Quelle](https://www.gesetze-im-internet.de/ustg_1980/__14.html).
"""


def test_content_guides_win_over_fixtures(site_build, monkeypatch, tmp_path):
    (tmp_path / "test.md").write_text(GUIDE, encoding="utf-8")
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", tmp_path)
    guides, is_sample = site_build.load_guides()
    assert not is_sample
    assert [g["slug"] for g in guides] == ["test-ratgeber"]
    g = guides[0]
    assert g["last_checked_de"] == "1. Oktober 2026"
    assert "<h2" in g["body_html"]  # "##" stays h2 under the page h1
    assert 'class="source-link"' in g["body_html"]


def test_empty_content_dir_uses_labelled_fixtures(site_build, monkeypatch, tmp_path):
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", tmp_path)
    guides, is_sample = site_build.load_guides()
    assert is_sample and len(guides) >= 2
    for g in guides:
        assert g["sample"] and "Beispieltext" in g["title"] + g["body_html"]


@pytest.mark.parametrize("broken, msg", [
    (GUIDE.replace("slug: test-ratgeber", "slug: Test Ratgeber"), "slug"),
    (GUIDE.replace('  - {title: "BMF", url: "https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html"}\n', "").replace("sources:", "sources: []"), "sources"),
    (GUIDE.replace("last_checked: 2026-10-01\n", ""), "last_checked"),
    ("no front matter", "front matter"),
])
def test_bad_guides_fail_loudly(site_build, monkeypatch, tmp_path, broken, msg):
    (tmp_path / "bad.md").write_text(broken, encoding="utf-8")
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", tmp_path)
    with pytest.raises(site_build.GuideError, match=msg):
        site_build.load_guides()


def test_production_mode_build(site_build, monkeypatch, tmp_path):
    (tmp_path / "guides").mkdir()
    (tmp_path / "guides" / "test.md").write_text(GUIDE, encoding="utf-8")
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", tmp_path / "guides")
    cfg = site_build.load_config(staging=False, site_public_url="https://example.invalid",
                                 app_public_url="https://app.example.invalid")
    out = site_build.build(tmp_path / "dist", cfg)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Testversion" not in index
    assert 'content="index,follow"' in index
    assert '<link rel="canonical" href="https://example.invalid/">' in index
    assert "X-Robots-Tag" not in (out / "_headers").read_text(encoding="utf-8")
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    assert "Disallow: /\n" not in robots and "Sitemap: https://example.invalid/sitemap.xml" in robots
    assert 'content="noindex,nofollow"' in (out / "404.html").read_text(encoding="utf-8")
    assert "https://app.example.invalid" in (out / "_headers").read_text(encoding="utf-8")


def test_staging_flag_from_env(site_build, monkeypatch):
    monkeypatch.delenv("SITE_STAGING", raising=False)
    assert site_build.load_config().staging is True
    monkeypatch.setenv("SITE_STAGING", "0")
    assert site_build.load_config().staging is False
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.example.invalid/")
    assert site_build.load_config().api_base == "https://app.example.invalid/api/v1"


# ---------- REVIEW H2: '[prüfen' notes must fail the build (temporary fixtures only) ----------

def _cli(site_build, monkeypatch, tmp_path, guides_dir, env=None):
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", guides_dir)
    for k in ("SITE_STAGING", "APP_PUBLIC_URL", "SITE_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    return site_build.main(["--out", str(tmp_path / "dist")])


def test_review_marker_fails_build_naming_file_and_line(site_build, monkeypatch, tmp_path, capsys):
    guides = tmp_path / "guides"
    guides.mkdir()
    marked = GUIDE.replace("Text mit [Quelle]", "Satz. [prüfen: mit Quelle abgleichen]\n\nText mit [Quelle]")
    (guides / "marked.md").write_text(marked, encoding="utf-8")
    src_line = marked.splitlines().index("Satz. [prüfen: mit Quelle abgleichen]") + 1
    assert _cli(site_build, monkeypatch, tmp_path, guides) == 1
    err = capsys.readouterr().err
    assert "site build FAILED" in err and "[prüfen" in err
    assert "ratgeber/test-ratgeber/index.html:" in err
    assert f"marked.md:{src_line}" in err


def test_review_marker_any_case_and_api_raises(site_build, monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "m.md").write_text(GUIDE.replace("## Abschnitt", "## Abschnitt\n\n[ Prüfen später]"), encoding="utf-8")
    monkeypatch.setattr(site_build, "CONTENT_GUIDES", guides)
    with pytest.raises(site_build.BuildError, match=r"index\.html:\d+"):
        site_build.build(tmp_path / "dist", site_build.load_config(staging=True))


def test_clean_content_builds(site_build, monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "ok.md").write_text(GUIDE, encoding="utf-8")
    assert _cli(site_build, monkeypatch, tmp_path, guides) == 0


def test_find_review_markers_reports_lines(site_build, tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "index.html").write_text("<p>ok</p>\n<p>x [prüfen: y]</p>\n", encoding="utf-8")
    (tmp_path / "b.html").write_text("<p>E-Rechnung prüfen</p>\n", encoding="utf-8")
    hits = site_build.find_review_markers(tmp_path)
    assert len(hits) == 1 and hits[0].startswith("a/index.html:2: [prüfen")


@pytest.mark.xfail(reason="content/ still carries known '[prüfen' markers until the content fix is merged",
                   strict=False)
def test_current_content_has_no_review_markers(site_build, tmp_path):
    site_build.build(tmp_path / "dist", site_build.load_config(staging=True))


# ---------- REVIEW M10: production build needs real public URLs ----------

@pytest.mark.parametrize("env, msg", [
    ({"SITE_STAGING": "0"}, "APP_PUBLIC_URL is not set"),
    ({"SITE_STAGING": "0", "APP_PUBLIC_URL": "https://app.example.invalid"}, "SITE_PUBLIC_URL is not set"),
    ({"SITE_STAGING": "0", "APP_PUBLIC_URL": "http://localhost:8000",
      "SITE_PUBLIC_URL": "https://example.invalid"}, "APP_PUBLIC_URL='http://localhost:8000' points to localhost"),
    ({"SITE_STAGING": "0", "APP_PUBLIC_URL": "https://app.example.invalid",
      "SITE_PUBLIC_URL": "http://127.0.0.1:8080"}, "SITE_PUBLIC_URL='http://127.0.0.1:8080' points to localhost"),
    ({"SITE_STAGING": "0", "APP_PUBLIC_URL": "https://[::1]:8000",
      "SITE_PUBLIC_URL": "https://example.invalid"}, "points to localhost"),
    ({"SITE_STAGING": "0", "APP_PUBLIC_URL": "http://app.example.invalid",
      "SITE_PUBLIC_URL": "https://example.invalid"}, "must use https"),
])
def test_production_build_refuses_local_or_missing_urls(site_build, monkeypatch, tmp_path, capsys, env, msg):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "ok.md").write_text(GUIDE, encoding="utf-8")
    assert _cli(site_build, monkeypatch, tmp_path, guides, env) == 1
    err = capsys.readouterr().err
    assert "production build refused" in err and msg in err
    assert not (tmp_path / "dist").exists()


def test_production_build_api_refuses_localhost_cfg(site_build, tmp_path):
    cfg = site_build.load_config(staging=False, app_public_url="http://localhost:8000",
                                 site_public_url="https://example.invalid")
    with pytest.raises(site_build.BuildError, match="APP_PUBLIC_URL"):
        site_build.build(tmp_path / "dist", cfg)


def test_production_build_with_public_urls_passes(site_build, monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "ok.md").write_text(GUIDE, encoding="utf-8")
    env = {"SITE_STAGING": "0", "APP_PUBLIC_URL": "https://app.example.invalid",
           "SITE_PUBLIC_URL": "https://example.invalid"}
    assert _cli(site_build, monkeypatch, tmp_path, guides, env) == 0


def test_staging_build_keeps_localhost_defaults(site_build, monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "ok.md").write_text(GUIDE, encoding="utf-8")
    assert _cli(site_build, monkeypatch, tmp_path, guides) == 0
