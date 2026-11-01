"""Static site build: site/templates (Jinja2) + guide markdown -> site/dist/.

Usage:  python site/build.py [--out DIR]
Needs only jinja2, markdown and PyYAML (site/requirements.txt).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import ipaddress
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

SITE_DIR = Path(__file__).resolve().parent
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

from config import REPO_ROOT, SiteConfig, load_config  # noqa: E402

TEMPLATES = SITE_DIR / "templates"
STATIC = SITE_DIR / "static"
CONTENT_GUIDES = REPO_ROOT / "content" / "guides"
FIXTURE_GUIDES = SITE_DIR / "fixtures" / "guides"
CONTENT_LEGAL = REPO_ROOT / "content" / "legal"
# Legal drafts from content/legal rendered as their own page: file name -> URL path.
LEGAL_DOCS = {"avv-entwurf.md": "/avv/"}
DEFAULT_OUT = SITE_DIR / "dist"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GERMAN_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                 "August", "September", "Oktober", "November", "Dezember"]

# Sources cited on fixed pages (legal statements need a source URL, CLAUDE.md rule 4).
SOURCES = {
    "bmf_faq": {"title": "Bundesministerium der Finanzen: Fragen und Antworten zur E-Rechnung",
                "url": "https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html"},
    "ustg_14": {"title": "§ 14 UStG – Ausstellung von Rechnungen (gesetze-im-internet.de)",
                "url": "https://www.gesetze-im-internet.de/ustg_1980/__14.html"},
    "ustg_27": {"title": "§ 27 UStG – Allgemeine Übergangsvorschriften, Abs. 38 (gesetze-im-internet.de)",
                "url": "https://www.gesetze-im-internet.de/ustg_1980/__27.html"},
    "dsgvo": {"title": "Verordnung (EU) 2016/679 (DSGVO), EUR-Lex",
              "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj"},
    "ddg_5": {"title": "§ 5 DDG – Allgemeine Informationspflichten (gesetze-im-internet.de)",
              "url": "https://www.gesetze-im-internet.de/ddg/__5.html"},
}
SOURCES_CHECKED = dt.date(2026, 10, 31)


class GuideError(ValueError):
    pass


class BuildError(RuntimeError):
    """A rule check on the rendered site failed; the build must not be deployed."""


# Unverified editorial notes ("[prüfen: ...]") must never reach a rendered page (REVIEW H2).
REVIEW_MARKER_RE = re.compile(r"\[\s*prüfen", re.I)
LOCAL_HOSTS = {"localhost", "0.0.0.0", ""}
URL_VARS = (("APP_PUBLIC_URL", "app_public_url"), ("SITE_PUBLIC_URL", "site_public_url"))


def _is_local_host(host: str) -> bool:
    host = (host or "").strip("[]").lower()
    if host in LOCAL_HOSTS or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def public_url_problems(cfg: SiteConfig, env=None) -> list[str]:
    """Problems that forbid a production build (SITE_STAGING=0), REVIEW M10.

    With `env` given (the CLI passes os.environ), an unset variable is a problem too,
    because the dev defaults point to localhost.
    """
    if cfg.staging:
        return []
    problems = []
    for var, attr in URL_VARS:
        if env is not None and not str(env.get(var, "")).strip():
            problems.append(f"{var} is not set (required when SITE_STAGING=0)")
            continue
        url = getattr(cfg, attr)
        parts = urlsplit(url)
        if _is_local_host(parts.hostname or ""):
            problems.append(f"{var}={url!r} points to localhost; set the public URL for SITE_STAGING=0")
        elif parts.scheme != "https":
            problems.append(f"{var}={url!r} must use https when SITE_STAGING=0")
    return problems


def find_review_markers(out: Path, sources: dict[str, Path] | None = None) -> list[str]:
    """Return 'file:line: text' for every '[prüfen' in a rendered page, with the source file if known."""
    hits = []
    sources = sources or {}
    for page in sorted(Path(out).rglob("*.html")):
        rel = page.relative_to(out).as_posix()
        for no, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            m = REVIEW_MARKER_RE.search(line)
            if not m:
                continue
            snippet = line[m.start():m.start() + 70].strip()
            where = f"{rel}:{no}"
            src = sources.get(rel)
            if src is not None:
                where += f" (source: {_source_line(src, line[m.end():m.end() + 40])})"
            hits.append(f"{where}: {snippet}")
    return hits


def _source_line(src: Path, tail: str) -> str:
    """'path:line' of the marker in the source file, matched by the text after '[prüfen'."""
    try:
        rel = src.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = src.as_posix()
    key = re.split(r"[<&\]]", html.unescape(tail).lstrip(": "), maxsplit=1)[0].strip()[:25]
    try:
        lines = src.read_text(encoding="utf-8").splitlines()
        marked = [no for no, line in enumerate(lines, 1) if REVIEW_MARKER_RE.search(line)]
        for no in marked:
            if key and key in lines[no - 1]:
                return f"{rel}:{no}"
        if marked:
            return f"{rel}:{marked[0]}"
    except OSError:
        pass
    return rel


def german_date(d: dt.date) -> str:
    return f"{d.day}. {GERMAN_MONTHS[d.month - 1]} {d.year}"


def parse_date(value) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise GuideError(f"last_checked not a date: {value!r}")


def split_front_matter(text: str, name: str) -> tuple[dict, str]:
    text = text.lstrip("﻿")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        raise GuideError(f"{name}: missing front matter (--- ... ---)")
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise GuideError(f"{name}: front matter is not a mapping")
    return meta, m.group(2)


def normalise_sources(raw, name: str) -> list[dict]:
    if not raw:
        raise GuideError(f"{name}: 'sources' is empty; every guide needs sources")
    out = []
    for item in raw:
        if isinstance(item, str):
            item = {"title": item, "url": item}
        if not isinstance(item, dict) or "url" not in item:
            raise GuideError(f"{name}: each source needs a url")
        url = str(item["url"]).strip()
        if urlsplit(url).scheme not in ("https", "http"):
            raise GuideError(f"{name}: source url must be http(s): {url!r}")
        out.append({"title": str(item.get("title") or url).strip(), "url": url})
    return out


def _external_links(html_text: str) -> str:
    """Open external links in guide bodies safely; no referrer leak."""
    return re.sub(r'<a href="(https?://[^"]+)"',
                  r'<a href="\1" rel="noopener noreferrer" class="source-link"', html_text)


def load_guides() -> tuple[list[dict], bool]:
    """Return (guides, is_sample). content/guides wins; fixtures only if it is empty."""
    files = sorted(CONTENT_GUIDES.glob("*.md")) if CONTENT_GUIDES.is_dir() else []
    files = [f for f in files if not f.name.lower().startswith(("readme", "_"))]
    is_sample = not files
    if is_sample:
        files = sorted(FIXTURE_GUIDES.glob("*.md"))
    guides, seen = [], set()
    for f in files:
        meta, body = split_front_matter(f.read_text(encoding="utf-8"), f.name)
        for key in ("title", "description", "slug", "sources", "last_checked"):
            if key not in meta:
                raise GuideError(f"{f.name}: front matter misses '{key}'")
        slug = str(meta["slug"]).strip().strip("/")
        if not SLUG_RE.match(slug):
            raise GuideError(f"{f.name}: slug must be lowercase a-z, 0-9 and '-': {slug!r}")
        if slug in seen:
            raise GuideError(f"{f.name}: duplicate slug {slug!r}")
        seen.add(slug)
        # The page template owns the <h1>; demote headings only if the guide itself uses "# ".
        baselevel = 2 if re.search(r"^# ", body, re.M) else 1
        md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"],
                               extension_configs={"toc": {"baselevel": baselevel, "permalink": False}})
        checked = parse_date(meta["last_checked"])
        guides.append({
            "source": f,
            "title": str(meta["title"]).strip(),
            "description": str(meta["description"]).strip(),
            "slug": slug,
            "path": f"/ratgeber/{slug}/",
            "sources": normalise_sources(meta["sources"], f.name),
            "last_checked": checked,
            "last_checked_de": german_date(checked),
            "body_html": _external_links(md.convert(body)),
            "sample": bool(meta.get("sample", is_sample)),
            "order": meta.get("order", 999),
        })
    guides.sort(key=lambda g: (g["order"], g["title"]))
    return guides, is_sample


def load_legal_doc(name: str) -> dict:
    """Render a draft legal text from content/legal (front matter: title, status). Missing file fails the build."""
    f = CONTENT_LEGAL / name
    if not f.is_file():
        raise GuideError(f"{name}: legal draft not found in content/legal")
    meta, body = split_front_matter(f.read_text(encoding="utf-8"), name)
    for key in ("title", "status"):
        if key not in meta:
            raise GuideError(f"{name}: front matter misses '{key}'")
    body = re.sub(r"\A\s*# [^\n]*\n", "", body, count=1)  # the page template owns the <h1>
    md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"],
                           extension_configs={"toc": {"baselevel": 1, "permalink": False}})
    return {"title": str(meta["title"]).strip(), "status": str(meta["status"]).strip(), "source": f,
            "body_html": _external_links(md.convert(body))}


def page_file(path: str) -> str:
    """URL path -> file path inside dist ("/a/" -> "a/index.html")."""
    if path.endswith(".html"):
        return path.lstrip("/")
    return (path.strip("/") + "/index.html").lstrip("/")


PAGES = [
    # template, url path, title, description, in sitemap
    ("index.html", "/", "E-Rechnung aus Ihrem bestehenden Rechnungsexport",
     "Belegbrücke macht aus Ihrem Rechnungsexport (CSV oder Excel) eine geprüfte XRechnung. Mit kostenlosem E-Rechnung-Check.", True),
    ("belegbruecke.html", "/belegbruecke/", "Belegbrücke: So funktioniert der Konverter",
     "Was Belegbrücke tut, für wen es gedacht ist und für wen nicht, wie es abläuft und häufige Fragen.", True),
    ("pruefen.html", "/e-rechnung-pruefen/", "E-Rechnung prüfen: kostenloser Check für XRechnung und ZUGFeRD",
     "Laden Sie eine XML- oder PDF-Datei hoch und sehen Sie, welche Prüfungen gelaufen sind und welche Fehler gefunden wurden.", True),
    ("ratgeber_index.html", "/ratgeber/", "Ratgeber E-Rechnung",
     "Kurze Ratgebertexte zur E-Rechnung, jeweils mit Quellen und Prüfdatum.", True),
    ("impressum.html", "/impressum/", "Impressum", "Impressum (Entwurf).", True),
    ("datenschutz.html", "/datenschutz/", "Datenschutzhinweise", "Datenschutzhinweise (Entwurf).", True),
    ("agb.html", "/agb/", "Allgemeine Geschäftsbedingungen", "AGB (Entwurf).", True),
    # legal_doc pages: rendered from content/legal via LEGAL_DOCS; listed here for the sitemap rule.
    ("legal_doc.html", "/avv/", "Auftragsverarbeitungsvertrag (Entwurf)", "Vertrag über die Auftragsverarbeitung (Entwurf).", True),
    ("bestaetigt.html", "/bestaetigt/", "Anmeldung bestätigt", "Ihre E-Mail-Adresse ist bestätigt.", False),
    ("404.html", "/404.html", "Seite nicht gefunden", "Diese Seite gibt es nicht.", False),
]


def make_env(cfg: SiteConfig) -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=select_autoescape(["html", "xml"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.globals.update(cfg=cfg, brand=cfg.brand, PLACEHOLDER=cfg.placeholder,
                       S=SOURCES, sources_checked_de=german_date(SOURCES_CHECKED))
    env.filters["app_url"] = lambda p: cfg.app_public_url + p
    return env


def brand_css(cfg: SiteConfig) -> str:
    c = cfg.brand["colours"]
    lines = [f"  --{k.replace('_', '-')}: {v};" for k, v in c.items()]
    return "/* generated from contracts/brand.md by site/build.py */\n:root {\n" + "\n".join(lines) + "\n}\n"


def headers_file(cfg: SiteConfig) -> str:
    app_origin = "{0.scheme}://{0.netloc}".format(urlsplit(cfg.app_public_url))
    csp = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
           f"font-src 'self'; connect-src 'self' {app_origin}; form-action 'self' {app_origin}; "
           "frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
    lines = ["/*"]
    if cfg.staging:
        lines.append("  X-Robots-Tag: noindex, nofollow")
    lines += [
        f"  Content-Security-Policy: {csp}",
        "  X-Content-Type-Options: nosniff",
        "  Referrer-Policy: strict-origin-when-cross-origin",
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()",
        "  X-Frame-Options: DENY",
        "",
    ]
    return "\n".join(lines)


def robots_txt(cfg: SiteConfig) -> str:
    if cfg.staging:
        return "# Testversion: nicht indexieren\nUser-agent: *\nDisallow: /\n"
    return f"User-agent: *\nAllow: /\n\nSitemap: {cfg.site_public_url}/sitemap.xml\n"


def sitemap_xml(cfg: SiteConfig, entries: list[tuple[str, dt.date | None]]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in entries:
        out.append("  <url><loc>" + html.escape(cfg.site_public_url + path) + "</loc>"
                   + (f"<lastmod>{lastmod.isoformat()}</lastmod>" if lastmod else "") + "</url>")
    out.append("</urlset>\n")
    return "\n".join(out)


def build(out: Path = DEFAULT_OUT, cfg: SiteConfig | None = None, *,
          allow_review_markers: bool = False) -> Path:
    """Build the site. Raises BuildError if a rule check fails.

    `allow_review_markers` exists only for the shared test fixture while content still
    carries known markers; the CLI never sets it.
    """
    cfg = cfg or load_config()
    problems = public_url_problems(cfg)
    if problems:
        raise BuildError("production build refused:\n  " + "\n  ".join(problems))
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = make_env(cfg)
    guides, guides_are_sample = load_guides()
    sitemap: list[tuple[str, dt.date | None]] = []
    page_sources: dict[str, Path] = {}

    def render(template: str, path: str, title: str, description: str, indexable: bool, **ctx):
        tpl = env.get_template(template)
        page = tpl.render(page={"path": path, "title": title, "description": description,
                                "indexable": indexable and not cfg.staging,
                                "canonical": cfg.site_public_url + (path if path != "/404.html" else "/")},
                          guides=guides, guides_are_sample=guides_are_sample, **ctx)
        target = out / page_file(path)
        src = ctx.get("guide") or ctx.get("doc")
        page_sources[page_file(path)] = src["source"] if src else TEMPLATES / template
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        if indexable:
            sitemap.append((path, ctx.get("lastmod")))

    legal_by_path = {path: name for name, path in LEGAL_DOCS.items()}
    for template, path, title, description, in_sitemap in PAGES:
        if path in legal_by_path:
            render(template, path, title, description, in_sitemap, doc=load_legal_doc(legal_by_path[path]))
        else:
            render(template, path, title, description, in_sitemap)
    for g in guides:
        render("guide.html", g["path"], g["title"], g["description"], True, guide=g, lastmod=g["last_checked"])

    shutil.copytree(STATIC, out / "static")
    (out / "static" / "brand.css").write_text(brand_css(cfg), encoding="utf-8")
    (out / "_headers").write_text(headers_file(cfg), encoding="utf-8")
    (out / "robots.txt").write_text(robots_txt(cfg), encoding="utf-8")
    (out / "sitemap.xml").write_text(sitemap_xml(cfg, sitemap), encoding="utf-8")
    if not allow_review_markers:
        hits = find_review_markers(out, page_sources)
        if hits:
            raise BuildError(f"{len(hits)} unverified '[prüfen' note(s) in rendered pages; "
                             "resolve them in the source:\n  " + "\n  ".join(hits))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    cfg = load_config()
    try:
        problems = public_url_problems(cfg, os.environ)
        if problems:
            raise BuildError("production build refused:\n  " + "\n  ".join(problems))
        out = build(args.out, cfg)
    except (BuildError, GuideError) as exc:
        print(f"site build FAILED: {exc}", file=sys.stderr)
        return 1
    n = sum(1 for _ in out.rglob("*.html"))
    print(f"built {n} pages into {out} (staging={'on' if cfg.staging else 'off'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
