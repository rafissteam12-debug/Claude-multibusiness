#!/usr/bin/env python3
"""Check the built static site (site/dist) against CLAUDE.md rules 2 and 6.

    python ops/scripts/check_site.py [--dist site/dist] [--mode staging|release]

Default mode follows the SITE_STAGING environment variable: "0" -> release, anything else -> staging.

Always (both modes):
  - no unverified "[prüfen" notes in any built HTML file (review H2; CLAUDE.md rule 4)
  - no price strings in any public file (HTML/JS/JSON/XML/TXT): currency amounts next to price words
    (Preis, kostet, Monat, monatlich, mtl., jährlich, Abo, Tarif, zzgl., inkl. MwSt.), amounts with
    cents ("9,90 €"), a leading euro sign ("€ 9"), or schema.org price markup.
    Legal thresholds in guide texts ("800.000 Euro", "250 Euro") are not prices and pass.
Mode "staging" (default; SITE_STAGING=1):
  - every HTML page carries the "Testversion" banner and <meta name="robots" content="noindex...">
  - _headers sends X-Robots-Tag: noindex, nofollow for /*; robots.txt disallows everything
  - legal pages (Impressum, Datenschutz, AGB) carry [[BUSINESS_ID_PENDING]] (no invented identity)
Mode "release" (go-live gate, needs owner approval; SITE_STAGING=0):
  - no [[BUSINESS_ID_PENDING...]] placeholder anywhere, no staging banner
  - no localhost / 127.0.0.1 reference in _headers or any page (APP_PUBLIC_URL / SITE_PUBLIC_URL must be
    set as Cloudflare build variables, review M10)
Exit 0 = ok, 1 = findings (printed as "file: problem").
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGAL_PAGES = ("impressum/index.html", "datenschutz/index.html", "agb/index.html")
TEXT_SUFFIXES = {".html", ".js", ".json", ".xml", ".txt", ".css"}
PLACEHOLDER = "[[BUSINESS_ID_PENDING"
UNVERIFIED = "[prüfen"
LOCALHOST = re.compile(r"\blocalhost\b|\b127\.0\.0\.1\b|\[::1\]", re.IGNORECASE)

AMOUNT = r"\d{1,3}(?:[.  ]\d{3})*(?:,\d{1,2})?"
CURRENCY = r"(?:€|EUR\b|Euro\b)"
MONEY = re.compile(rf"{AMOUNT}\s?-?\s?{CURRENCY}|€\s?\d", re.IGNORECASE)
CENTS = re.compile(rf"\d+,\d{{2}}\s?{CURRENCY}|€\s?\d")
PRICE_WORDS = re.compile(
    r"preis|kostet|kosten\b|/\s?monat|pro monat|monatlich|mtl\.|j[äa]hrlich|pro jahr|\babo\b|tarif|"
    r"zzgl\.|inkl\.\s?mwst|netto|brutto",
    re.IGNORECASE)
SCHEMA_PRICE = re.compile(r'"(?:price|priceCurrency|offers)"\s*:|itemprop="price', re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
WINDOW = 80


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", TAG.sub(" ", html))


def price_findings(text: str) -> list[str]:
    out = []
    for m in MONEY.finditer(text):
        ctx = text[max(0, m.start() - WINDOW): m.end() + WINDOW]
        if CENTS.fullmatch(m.group(0).strip()) or m.group(0).startswith("€") or PRICE_WORDS.search(ctx):
            out.append(f"price-like string: '{ctx.strip()}'")
    return out


def check(dist: Path, mode: str) -> list[str]:
    problems: list[str] = []
    if not dist.is_dir():
        return [f"{dist}: not found (run python site/build.py first)"]
    files = sorted(p for p in dist.rglob("*") if p.is_file() and (p.suffix in TEXT_SUFFIXES or p.name == "_headers"))
    for p in files:
        rel = p.relative_to(dist).as_posix()
        raw = p.read_text(encoding="utf-8", errors="replace")
        if p.name == "mock-report.json":
            continue  # example validation report, contains no prices; amounts are invoice data
        text = visible_text(raw) if p.suffix == ".html" else raw
        if p.suffix in (".html", ".txt"):
            problems += [f"{rel}: {f}" for f in price_findings(text)]
        if SCHEMA_PRICE.search(raw):
            problems.append(f"{rel}: schema.org price markup")
        if mode == "release" and LOCALHOST.search(raw):
            problems.append(f"{rel}: references localhost (set APP_PUBLIC_URL/SITE_PUBLIC_URL build variables)")
        if p.suffix == ".html":
            if UNVERIFIED in raw:
                problems.append(f"{rel}: unverified '[prüfen' note present")
            if mode == "staging":
                if "Testversion" not in raw:
                    problems.append(f"{rel}: staging banner 'Testversion' missing")
                if not re.search(r'<meta[^>]+name="robots"[^>]+noindex', raw):
                    problems.append(f"{rel}: <meta name=robots noindex> missing")
            else:
                if PLACEHOLDER in raw:
                    problems.append(f"{rel}: business ID placeholder still present")
                if "Testversion" in raw:
                    problems.append(f"{rel}: staging banner still present")

    if mode == "staging":
        headers = dist / "_headers"
        h = headers.read_text(encoding="utf-8") if headers.is_file() else ""
        if not re.search(r"(?m)^/\*\s*$", h) or not re.search(r"X-Robots-Tag:\s*noindex,\s*nofollow", h):
            problems.append("_headers: '/*' with 'X-Robots-Tag: noindex, nofollow' missing")
        robots = dist / "robots.txt"
        if not robots.is_file() or not re.search(r"(?m)^Disallow:\s*/\s*$", robots.read_text(encoding="utf-8")):
            problems.append("robots.txt: 'Disallow: /' missing")
        for page in LEGAL_PAGES:
            p = dist / page
            if not p.is_file():
                problems.append(f"{page}: legal page missing")
            elif "[[BUSINESS_ID_PENDING]]" not in p.read_text(encoding="utf-8"):
                problems.append(f"{page}: [[BUSINESS_ID_PENDING]] missing (business identity must not be filled in yet)")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dist", type=Path, default=ROOT / "site" / "dist")
    default_mode = "release" if os.environ.get("SITE_STAGING", "1").strip() == "0" else "staging"
    ap.add_argument("--mode", choices=("staging", "release"), default=default_mode)
    args = ap.parse_args(argv)
    problems = check(args.dist, args.mode)
    for p in problems:
        print(p)
    print(f"check_site ({args.mode}): {'OK' if not problems else f'{len(problems)} finding(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
