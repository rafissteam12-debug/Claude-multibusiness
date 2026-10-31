"""Render Ada carousel slides: slides.json -> slide-N.svg -> slide-N.png (1080x1350).

Usage:  python content/ada/posts/render_slides.py            # all posts with slides.json
        python content/ada/posts/render_slides.py ig-001-pdf-ist-keine-e-rechnung

Style follows content/carousels/02-wen-trifft-2027/slide-1.svg and contracts/brand.md.
Every slide carries the "KI-generiert" badge. The first slide shows the Ada avatar:
the SVG references ../../ada-avatar-plain.svg; because cairosvg does not reliably
render nested SVG <image>, the PNG gets the avatar composited with Pillow.
Text is wrapped by measuring with the locally installed fallback font (Inter);
IBM Plex Sans is preferred in the SVG when installed.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
from PIL import Image, ImageFont

HERE = Path(__file__).resolve().parent
ADA_PNG = HERE.parent / "ada-avatar-plain.png"
AVATAR_HREF = "../../ada-avatar-plain.svg"  # relative to content/ada/posts/<post>/

W, H = 1080, 1350
X0, XMAX = 72, 1008
C = {
    "teal": "#0F4C5C", "dark": "#0A3540", "bg": "#F7F5F0", "white": "#FFFFFF",
    "ink": "#17262B", "body": "#33453F", "muted": "#55635F", "line": "#DAD6CC",
    "orange": "#B4410B", "green": "#1E7A55",
}
FAMILY = "IBM Plex Sans, Inter, Arial, sans-serif"
MONO = "IBM Plex Mono, DejaVu Sans Mono, monospace"
FOOTER_Y = 1150
AVATAR = (760, 1040, 248)


def _font_file(pattern: str) -> str:
    try:
        return subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


_FONTS = {700: _font_file("Inter:bold"), 600: _font_file("Inter:semibold"),
          400: _font_file("Inter"), "mono": _font_file("DejaVu Sans Mono")}


def text_width(text: str, size: int, weight=400) -> float:
    path = _FONTS.get(weight) or _FONTS[400]
    if not path:
        return len(text) * size * 0.55
    return ImageFont.truetype(path, size).getlength(text)


def wrap(text: str, size: int, weight=400, max_w: float = XMAX - X0) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = f"{cur} {word}".strip()
            if text_width(cand, size, weight) <= max_w * 0.97 or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def t(x, y, s, size, weight=400, fill="body", anchor=None, family=FAMILY) -> str:
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="{family}" font-size="{size}"{w}'
            f' fill="{C.get(fill, fill)}"{a}>{escape(s)}</text>')


def render_block(b: dict, y: float) -> tuple[list[str], float]:
    out: list[str] = []
    kind = b["type"]
    if kind == "kicker":
        y += 40
        out.append(t(X0, y, b["text"], 40, 600, b.get("color", "orange")))
        y += 30
    elif kind == "title":
        size = b.get("size", 84)
        for line in wrap(b["text"], size, 700):
            y += size * 1.14
            out.append(t(X0, y, line, size, 700, b.get("color", "teal")))
        y += b.get("gap", 36)
    elif kind == "text":
        size = b.get("size", 38)
        weight = b.get("weight", 400)
        for line in wrap(b["text"], size, weight):
            y += size * 1.42
            out.append(t(X0, y, line, size, weight, b.get("color", "body")))
        y += b.get("gap", 22)
    elif kind == "bullets":
        size = b.get("size", 36)
        for item in b["items"]:
            lines = wrap(item, size, 400, XMAX - X0 - 48)
            for i, line in enumerate(lines):
                y += size * 1.42
                if i == 0:
                    out.append(f'<rect x="{X0}" y="{y - size * 0.62:.0f}" width="16" height="16" rx="3" fill="{C["teal"]}"/>')
                out.append(t(X0 + 48, y, line, size, 400, "body"))
            y += 14
        y += 10
    elif kind == "card":
        out_c, h = render_card(b, y + 10)
        out += out_c
        y += h + 34
    elif kind == "spacer":
        y += b.get("h", 40)
    else:
        raise ValueError(f"unknown block type {kind}")
    return out, y


def render_card(b: dict, y: float) -> tuple[list[str], float]:
    """White card with rows. Row: {label, value, status?, mono?}."""
    inner: list[str] = []
    pad = 36
    cy = y + pad
    if b.get("title"):
        cy += 34
        inner.append(t(X0 + pad, cy, b["title"], 34, 600, "ink"))
        cy += 18
    for row in b["rows"]:
        size = row.get("size", 32)
        fam = MONO if row.get("mono") else FAMILY
        status = row.get("status")
        cy += size * 1.5
        if status:
            col = {"ok": "green", "error": "orange", "skip": "muted"}[status]
            word = {"ok": "bestanden", "error": "Fehler", "skip": "übersprungen"}[status]
            inner.append(f'<circle cx="{X0 + pad + 12}" cy="{cy - size * 0.36:.0f}" r="12" fill="{C[col]}"/>')
            inner.append(t(X0 + pad + 40, cy, row["label"], size, 600, "ink"))
            inner.append(t(XMAX - pad, cy, row.get("value", word), size, 600, col, anchor="end"))
        elif row.get("stack"):
            inner.append(t(X0 + pad, cy, row["label"], size, 400, "muted"))
            cy += size * 1.35
            inner.append(t(X0 + pad, cy, row["value"], size + 2, 600, row.get("color", "ink")))
        else:
            if row.get("label"):
                inner.append(t(X0 + pad, cy, row["label"], size, 400, "muted", family=fam))
            if row.get("value"):
                vx = X0 + pad + row.get("indent", 0)
                lines = wrap(row["value"], size, 400, XMAX - X0 - 2 * pad - row.get("indent", 0))
                for i, line in enumerate(lines):
                    if i:
                        cy += size * 1.35
                    inner.append(t(vx if row.get("label") is None else XMAX - pad, cy, line, size,
                                   row.get("weight", 400), row.get("color", "ink"),
                                   anchor=None if row.get("label") is None else "end", family=fam))
        if row.get("rule"):
            cy += 22
            inner.append(f'<line x1="{X0 + pad}" y1="{cy:.0f}" x2="{XMAX - pad}" y2="{cy:.0f}" stroke="{C["line"]}" stroke-width="2"/>')
    h = cy - y + pad
    border = C[b.get("border", "line")]
    card = [f'<rect x="{X0}" y="{y:.0f}" width="{XMAX - X0}" height="{h:.0f}" rx="18" fill="{C["white"]}" stroke="{border}" stroke-width="{3 if b.get("border") else 2}"/>']
    return card + inner, h


def slide_svg(post: dict, idx: int, slide: dict) -> str:
    n = len(post["slides"])
    first = idx == 0
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="{escape(slide["alt"], {chr(34): "&quot;"})}">',
        f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>',
        f'<rect x="0" y="0" width="{W}" height="14" fill="{C["teal"]}"/>',
        f'<rect x="72" y="80" width="260" height="60" rx="30" fill="{C["teal"]}"/>',
        t(202, 120, "KI-generiert", 26, 600, "white", anchor="middle"),
        t(1008, 120, f'{post["series"]} · {idx + 1}/{n}', 26, 400, "muted", anchor="end"),
    ]
    if slide.get("demo_label"):
        parts.append(f'<rect x="72" y="166" width="{text_width(slide["demo_label"], 26, 600) + 48:.0f}" height="52" rx="10" fill="none" stroke="{C["muted"]}" stroke-width="2" stroke-dasharray="8 6"/>')
        parts.append(t(96, 201, slide["demo_label"], 26, 600, "muted"))
    y = slide.get("y", 300 if first else (262 if slide.get("demo_label") else 230))
    for block in slide["blocks"]:
        out, y = render_block(block, y)
        parts += out
    limit = slide.get("source_y", 1100)
    if y > limit - 10:
        print(f"  WARNING slide {idx + 1}: content ends at y={y:.0f} (> {limit - 10})", file=sys.stderr)
    if slide.get("source"):
        sy = limit
        for line in reversed(wrap("Quelle: " + slide["source"], 24, 400, (AVATAR[0] - 40 - X0) if first else XMAX - X0)):
            parts.append(t(X0, sy, line, 24, 400, "muted"))
            sy -= 32
    line_end = 720 if first else XMAX
    parts += [
        f'<line x1="72" y1="{FOOTER_Y}" x2="{line_end}" y2="{FOOTER_Y}" stroke="{C["line"]}" stroke-width="2"/>',
        t(72, 1215, "Ada · Ablaufwerk", 30, 600, "ink"),
        t(72, 1260, "Keine Steuer- oder Rechtsberatung.", 26, 400, "muted"),
    ]
    if not first:
        parts.append(t(1008, 1215, "KI-generierte Figur", 26, 400, "muted", anchor="end"))
    if first:
        ax, ay, s = AVATAR
        parts.append(f'<image href="{AVATAR_HREF}" x="{ax}" y="{ay}" width="{s}" height="{s}"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def to_png(svg: str, out: Path, with_avatar: bool) -> None:
    # Drop the <image> for cairosvg; composite the avatar with Pillow instead.
    svg_no_img = "\n".join(l for l in svg.splitlines() if not l.startswith("<image "))
    png = cairosvg.svg2png(bytestring=svg_no_img.encode("utf-8"), output_width=W, output_height=H)
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    if with_avatar:
        ax, ay, s = AVATAR
        ava = Image.open(ADA_PNG).convert("RGBA").resize((s, s), Image.LANCZOS)
        img.alpha_composite(ava, (ax, ay))
    img.convert("RGB").save(out, optimize=True)


def render_post(folder: Path) -> None:
    post = json.loads((folder / "slides.json").read_text(encoding="utf-8"))
    print(f"{folder.name}: {len(post['slides'])} slides")
    for i, slide in enumerate(post["slides"]):
        svg = slide_svg(post, i, slide)
        (folder / f"slide-{i + 1}.svg").write_text(svg, encoding="utf-8")
        to_png(svg, folder / f"slide-{i + 1}.png", with_avatar=(i == 0))


def main(argv: list[str]) -> None:
    folders = [HERE / a for a in argv] if argv else sorted(p.parent for p in HERE.glob("*/slides.json"))
    for f in folders:
        render_post(f)


if __name__ == "__main__":
    main(sys.argv[1:])
