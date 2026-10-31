"""Placeholder build (orchestrator seed, 31 Oct 2026). The website agent replaces this.
Writes a noindex 'Testversion' page so the Cloudflare link can be tested end to end."""
from pathlib import Path

DIST = Path(__file__).parent / "dist"
DIST.mkdir(parents=True, exist_ok=True)
(DIST / "index.html").write_text("""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Belegbrücke – Testversion</title></head>
<body style="font-family:system-ui,sans-serif;background:#F7F5F0;color:#17262B;margin:0">
<div style="background:#B4410B;color:#fff;padding:8px 16px;font-weight:600">Testversion – nicht öffentlich</div>
<main style="max-width:720px;margin:48px auto;padding:0 16px"><h1 style="color:#0F4C5C">Belegbrücke</h1>
<p>Diese Seite ist ein Platzhalter. Die Website wird gerade gebaut.</p></main></body></html>
""", encoding="utf-8")
(DIST / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n", encoding="utf-8")
(DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
print("built", DIST)
