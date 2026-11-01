"""Help articles from content/help/*.md (front matter: title, slug, sources, last_checked).

Unverified notes (`[prüfen: …]`) must never reach users (review H2): the strict loader raises
`UnverifiedContent`. The app loads strictly in staging/prod (at startup); in dev/test a marked article
is still shown but a warning is logged, so local work is not blocked while content is being checked.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

import markdown

from .settings import CONTENT_DIR

HELP_DIR = CONTENT_DIR / "help"
MARKER_RE = re.compile(r"\[\s*prüfen", re.I)
log = logging.getLogger("app")


class UnverifiedContent(RuntimeError):
    """Raised when a text that the app would show or send still contains a `[prüfen` marker."""


def refuse_unverified(text: str, name: str) -> None:
    m = MARKER_RE.search(text)
    if m:
        line = text.count("\n", 0, m.start()) + 1
        raise UnverifiedContent(f"{name}:{line}: unverified note '[prüfen' must be resolved before the text is used")


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


def load_articles(directory: Path = HELP_DIR, strict: bool = True) -> dict[str, dict]:
    out = {}
    if not directory.exists():
        return out
    for f in sorted(directory.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        try:
            refuse_unverified(text, f"content/help/{f.name}")
        except UnverifiedContent as exc:
            if strict:
                raise
            log.warning("%s", exc)
        meta, body = _front(text)
        slug = meta.get("slug") or f.stem
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            continue
        body = re.sub(r"^#\s+.*\n", "", body.lstrip(), count=1)  # title is rendered by the template
        html = markdown.markdown(body, extensions=["tables"])
        out[slug] = {"slug": slug, "title": meta.get("title", slug), "html": html,
                     "sources": meta.get("sources", []), "last_checked": meta.get("last_checked")}
    return out


@lru_cache(maxsize=1)
def articles() -> dict[str, dict]:
    return load_articles(strict=False)
