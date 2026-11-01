"""Shared fixtures for site tests: load site/build.py as a module and build once into a temp dir."""
from __future__ import annotations

import importlib.util
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def site_build():
    return _load("site_build", SITE_DIR / "build.py")


@pytest.fixture(scope="session")
def staging_cfg(site_build):
    return site_build.load_config(app_public_url="http://localhost:8000",
                                  site_public_url="http://localhost:8080", staging=True)


@pytest.fixture(scope="session")
def dist(site_build, staging_cfg, tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    site_build.build(out, staging_cfg)  # enforces the '[prüfen' check on real content too
    return out


@pytest.fixture(scope="session")
def pages(dist) -> dict[str, str]:
    return {p.relative_to(dist).as_posix(): p.read_text(encoding="utf-8") for p in sorted(dist.rglob("*.html"))}


class Collector(HTMLParser):
    """Collect tags with attributes and heading levels, plus visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.headings: list[int] = []
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)


def parse(html_text: str) -> Collector:
    c = Collector()
    c.feed(html_text)
    return c


@pytest.fixture(scope="session")
def parsed(pages) -> dict[str, Collector]:
    return {k: parse(v) for k, v in pages.items()}


@pytest.fixture(scope="session")
def html_parse():
    return parse
