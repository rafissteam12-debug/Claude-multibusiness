"""Hard rules from CLAUDE.md: staging markers, placeholder, no prices, no cookies/storage, contrast."""
from __future__ import annotations

import re

PLACEHOLDER = "[[BUSINESS_ID_PENDING]]"
PRICE_RE = re.compile(r"€\s*\d|\d[\d.,]*\s*(?:€|&euro;|&#8364;)")


def test_staging_markers(dist, pages):
    headers = (dist / "_headers").read_text(encoding="utf-8")
    assert headers.startswith("/*\n") and "X-Robots-Tag: noindex, nofollow" in headers
    assert (dist / "robots.txt").read_text(encoding="utf-8").splitlines()[-1] == "Disallow: /"
    for name, html in pages.items():
        assert "Testversion – nicht öffentlich" in html, name
        assert '<meta name="robots" content="noindex,nofollow">' in html, name


def test_legal_pages_carry_placeholder(pages):
    for name in ("impressum/index.html", "datenschutz/index.html", "agb/index.html"):
        assert PLACEHOLDER in pages[name], name
        draft = "Entwurf – wird vor Veröffentlichung geprüft" if name.startswith("datenschutz") \
            else "Entwurf, juristische Prüfung ausstehend"
        assert draft in pages[name], name
    assert "Preise: " + PLACEHOLDER in pages["belegbruecke/index.html"]


def test_no_prices_anywhere(dist):
    hits = []
    for f in dist.rglob("*"):
        if f.is_file() and f.suffix in (".html", ".js", ".json", ".css", ".xml", ".txt", ""):
            for m in PRICE_RE.finditer(f.read_text(encoding="utf-8")):
                hits.append((f.relative_to(dist).as_posix(), m.group(0)))
    assert not hits, hits


def test_price_regex_catches_examples():
    for s in ("490 €", "ab 1.490 €", "€ 49", "49,00€", "12 &euro;"):
        assert PRICE_RE.search(s), s
    assert not PRICE_RE.search("Preise: [[BUSINESS_ID_PENDING]]")


def test_no_forbidden_claims(pages, parsed):
    for name, doc in parsed.items():
        text = " ".join(doc.text).lower()
        for word in ("rechtssicher", "garantiert", "testimonial", "kundenstimme"):
            # the only allowed mention is our own negation in the FAQ ("Ist der Prüfbericht eine Garantie? Nein.")
            assert word not in text, (name, word)


def test_no_cookies_or_storage_in_js(dist):
    for js in (dist / "static").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        for bad in ("document.cookie", "localStorage", "sessionStorage", "indexedDB"):
            assert bad not in text, (js.name, bad)


def test_events_use_beacon_text_plain_and_whitelist(dist, staging_cfg):
    js = (dist / "static" / "site.js").read_text(encoding="utf-8")
    assert "navigator.sendBeacon" in js and '"text/plain"' in js and '"/events"' in js
    allowed = "page_view,link_click,check_run,subscribe,upload,mapping_confirmed,conversion_done".split(",")
    assert set(staging_cfg.events) <= set(allowed)
    used = set(re.findall(r'track\("([a-z_]+)"\)', js + (dist / "static" / "checker.js").read_text(encoding="utf-8")))
    assert used and used <= set(staging_cfg.events), used


def test_subscribe_form_contract(parsed):
    doc = parsed["e-rechnung-pruefen/index.html"]
    boxes = [a for t, a in doc.tags if t == "input" and a.get("type") == "checkbox"]
    assert boxes and all("checked" not in b for b in boxes), "consent checkbox must start unticked"
    forms = [a for t, a in doc.tags if t == "form" and "subscribe-form" in (a.get("class") or "")]
    assert forms and forms[0]["data-source"] == "check"


def test_checker_form(parsed):
    doc = parsed["e-rechnung-pruefen/index.html"]
    file_inputs = [a for t, a in doc.tags if t == "input" and a.get("type") == "file"]
    assert len(file_inputs) == 1
    assert ".xml" in file_inputs[0]["accept"] and ".pdf" in file_inputs[0]["accept"]
    form = [a for t, a in doc.tags if t == "form" and a.get("id") == "check-form"][0]
    assert form["data-max-bytes"] == str(5 * 1024 * 1024)
    body = [a for t, a in doc.tags if t == "body"][0]
    assert body["data-api"] == "http://localhost:8000/api/v1"


def _lum(hex_colour: str) -> float:
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_text_colour_contrast(staging_cfg):
    c = staging_cfg.brand["colours"]
    pairs = [
        (c["ink"], c["off_white"]), (c["body"], c["off_white"]), (c["muted"], c["off_white"]),
        (c["teal"], c["off_white"]), (c["muted"], c["white"]), (c["teal"], c["white"]),
        ("#FFFFFF", c["orange"]), (c["orange"], c["white"]), (c["orange"], c["off_white"]),
        (c["success"], c["white"]), ("#A3260B", c["white"]), (c["body"], "#F3F1EC"), (c["ink"], "#FFF6EE"),
        ("#FFFFFF", "#923408"),
    ]
    for fg, bg in pairs:
        assert contrast(fg, bg) >= 4.5, (fg, bg, round(contrast(fg, bg), 2))


def test_privacy_page_lists_facts(pages, parsed):
    """REVIEW M12/H4: every data category, retention, processors and rights are on the page."""
    text = " ".join(parsed["datenschutz/index.html"].text)
    text = " ".join(text.split())
    for needle in (
        "Entwurf – wird vor Veröffentlichung geprüft", "keine Rechtsberatung",
        "gelöscht bei erfolgreicher Umwandlung (mindestens eine gültige E-Rechnung), spätestens nach 24 Stunden",
        "24 Stunden", "ohne Zellwerte", "inaktive Konten nach 12 Monaten",
        "unbestätigte Anmeldungen 7 Tage", "Konto löschen", "JSON-Datei", "Daten exportieren",
        "zusammen mit der Datei gelöscht", "etwa 13 Monate", "3 Jahre nach der Abmeldung", "HMAC",
        "letzten Anmeldung", "lesbare PDF-Fassung",
        "Cloudflare", "Brevo", "Anthropic", "außerhalb der Europäischen Union", "Europäischen Union",
        "Art. 15", "Art. 16", "Art. 17", "Art. 18", "Art. 19", "Art. 20", "Art. 21", "Art. 77",
        "Verantwortlicher",
    ):
        assert needle in text, needle
    assert text.count(PLACEHOLDER) >= 4
    assert "noch nicht freigeschaltet" not in text
