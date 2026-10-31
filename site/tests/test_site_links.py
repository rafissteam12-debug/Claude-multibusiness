"""Links resolve; no third-party resources; accessibility basics."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

RESOURCE_ATTRS = {"script": "src", "link": "href", "img": "src", "source": "src", "iframe": "src",
                  "video": "src", "audio": "src", "embed": "src", "object": "data"}


def _resolve(dist, path: str) -> bool:
    path = path.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return True
    target = dist / path.lstrip("/")
    if path.endswith("/"):
        return (target / "index.html").is_file()
    return target.is_file() or (target / "index.html").is_file()


def test_every_internal_link_resolves(dist, parsed):
    broken = []
    for name, doc in parsed.items():
        for tag, a in doc.tags:
            for attr in ("href", "src"):
                v = a.get(attr)
                if not v or v.startswith(("http://", "https://", "mailto:", "#", "//")):
                    continue
                if not v.startswith("/"):
                    broken.append((name, v, "relative link"))
                elif not _resolve(dist, v):
                    broken.append((name, v))
    assert not broken, broken


def test_same_page_anchors_exist(parsed, pages):
    for name, doc in parsed.items():
        ids = {a.get("id") for _, a in doc.tags if a.get("id")}
        for tag, a in doc.tags:
            href = a.get("href") or ""
            if href.startswith("#"):
                assert href[1:] in ids, (name, href)


def test_no_external_resources(parsed, dist, staging_cfg):
    for name, doc in parsed.items():
        for tag, a in doc.tags:
            attr = RESOURCE_ATTRS.get(tag)
            if attr and a.get(attr):
                url = a[attr]
                if tag == "link" and a.get("rel") == "canonical":
                    continue
                assert url.startswith("/") and not url.startswith("//"), (name, tag, url)
            assert "srcset" not in a or all(p.strip().startswith("/") for p in a["srcset"].split(","))
            style = a.get("style", "")
            assert "url(" not in style, (name, style)
    for css in (dist / "static").glob("*.css"):
        text = css.read_text(encoding="utf-8")
        assert "@import" not in text and not re.search(r"url\(\s*['\"]?(https?:)?//", text), css
        assert "@font-face" not in text or "url(/" in text
    for js in (dist / "static").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        assert not re.search(r"https?://", text), f"hard-coded URL in {js.name}"


def test_external_anchors_are_sources_or_app_links(parsed, staging_cfg):
    for name, doc in parsed.items():
        for tag, a in doc.tags:
            href = a.get("href", "")
            if tag != "a" or not href.startswith(("http://", "https://")):
                continue
            if href.startswith(staging_cfg.app_public_url):
                assert "data-app-link" in a, (name, href)
                continue
            assert "source-link" in (a.get("class") or ""), (name, href)
            assert "noopener" in (a.get("rel") or ""), (name, href)
            assert urlsplit(href).scheme == "https", (name, href)


def test_images_have_alt(parsed):
    for name, doc in parsed.items():
        for tag, a in doc.tags:
            if tag == "img":
                assert a.get("alt") is not None and (a["alt"].strip() or a.get("role") == "presentation"), (name, a)


def test_html_lang_and_single_h1_and_heading_order(parsed):
    for name, doc in parsed.items():
        html_tags = [a for t, a in doc.tags if t == "html"]
        assert html_tags and html_tags[0].get("lang") == "de", name
        assert doc.headings.count(1) == 1, (name, doc.headings)
        assert doc.headings[0] == 1, (name, doc.headings)
        for prev, cur in zip(doc.headings, doc.headings[1:]):
            assert cur <= prev + 1, f"{name}: heading jumps h{prev} -> h{cur}"


def test_form_controls_have_labels(parsed):
    for name, doc in parsed.items():
        label_for = {a.get("for") for t, a in doc.tags if t == "label"}
        for tag, a in doc.tags:
            if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit"):
                assert a.get("id") in label_for or a.get("aria-label"), (name, a)


def test_unique_ids(parsed):
    for name, doc in parsed.items():
        ids = [a["id"] for _, a in doc.tags if a.get("id")]
        assert len(ids) == len(set(ids)), (name, sorted(i for i in ids if ids.count(i) > 1))


def test_meta_tags_present(parsed):
    for name, doc in parsed.items():
        metas = {(a.get("name") or a.get("property")): a.get("content") for t, a in doc.tags if t == "meta"}
        for key in ("viewport", "description", "robots", "og:title", "og:description", "og:url"):
            assert metas.get(key), (name, key)
        assert any(t == "link" and a.get("rel") == "canonical" for t, a in doc.tags), name
