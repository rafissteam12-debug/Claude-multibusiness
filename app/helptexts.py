"""Help articles from content/help/*.md (front matter: title, slug, sources, last_checked)."""
from __future__ import annotations

import re
from functools import lru_cache

import markdown

from .settings import CONTENT_DIR

HELP_DIR = CONTENT_DIR / "help"


def _front(text: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    fm, body = m.group(1), text[m.end():]
    meta = {}
    for key in ("title", "slug", "last_checked"):
        km = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
        if km:
            meta[key] = km.group(1)
    meta["sources"] = [{"title": t, "url": u} for t, u in
                       re.findall(r'-\s*title:\s*"(.*?)"\s*\n\s*url:\s*"(.*?)"', fm)]
    return meta, body


@lru_cache(maxsize=1)
def articles() -> dict[str, dict]:
    out = {}
    if not HELP_DIR.exists():
        return out
    for f in sorted(HELP_DIR.glob("*.md")):
        meta, body = _front(f.read_text(encoding="utf-8"))
        slug = meta.get("slug") or f.stem
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            continue
        body = re.sub(r"^#\s+.*\n", "", body.lstrip(), count=1)  # title is rendered by the template
        html = markdown.markdown(body, extensions=["tables"])
        out[slug] = {"slug": slug, "title": meta.get("title", slug), "html": html,
                     "sources": meta.get("sources", []), "last_checked": meta.get("last_checked")}
    return out
