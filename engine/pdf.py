"""render_pdf(invoice) -> readable A4 invoice PDF (German labels), reportlab.

Fonts: Bitstream Vera, shipped inside reportlab and embedded in the PDF (no
system fonts needed). `render_pdfa3b` additionally turns the visual into a
PDF/A-3b file and has it approved by pikepdf's allowlist PDF/A validator; it is
the base document for ZUGFeRD (see zugferd.py).
"""
from __future__ import annotations

import io
import os
from decimal import Decimal

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .cii import D, compute_totals, fmt_dec
from .inputcheck import check_invoice

_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
FONT, FONT_BOLD = "AWVera", "AWVeraBd"
FONT_CMD = ("FONTNAME", (0, 0), (-1, -1), FONT)  # tables otherwise select Helvetica (not embedded, breaks PDF/A)

UNITS_DE = {"C62": "Stk", "HUR": "Std", "DAY": "Tag", "KGM": "kg", "MTR": "m", "LTR": "l", "MTK": "m²", "SET": "Satz"}
CATEGORY_DE = {"S": "Normal-/ermäßigter Satz", "Z": "Nullsatz", "E": "steuerbefreit", "AE": "Reverse Charge",
               "K": "innergemeinschaftliche Lieferung", "G": "Ausfuhr", "O": "nicht steuerbar"}


def _fonts() -> None:
    if FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT, os.path.join(_FONT_DIR, "Vera.ttf")))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(_FONT_DIR, "VeraBd.ttf")))


def eur(v: Decimal) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def num_de(v: Decimal) -> str:
    return fmt_dec(v).replace(".", ",")


def date_de(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def _story(inv: dict) -> list:
    t = compute_totals(inv)
    base = ParagraphStyle("b", fontName=FONT, bulletFontName=FONT, fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=base, fontSize=7.5, leading=10, textColor=colors.HexColor("#444444"))
    h1 = ParagraphStyle("h", parent=base, fontName=FONT_BOLD, fontSize=16, leading=20)
    bold = ParagraphStyle("bb", parent=base, fontName=FONT_BOLD)

    def P(text, style=base):
        from xml.sax.saxutils import escape
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)

    s, b, pay = inv["seller"], inv["buyer"], inv["payment"]
    title = "Gutschrift" if inv["type_code"] == "381" else "Rechnung"
    story = [P(f"{s['name']} · {s['street']} · {s['postcode']} {s['city']}", small), Spacer(1, 4 * mm)]

    meta = [["Rechnungsnummer", inv["number"]], ["Rechnungsdatum", date_de(inv["issue_date"])]]
    if inv.get("delivery_date"):
        meta.append(["Leistungsdatum", date_de(inv["delivery_date"])])
    if inv.get("period"):
        meta.append(["Leistungszeitraum", f"{date_de(inv['period']['start'])} – {date_de(inv['period']['end'])}"])
    if inv.get("buyer_reference"):
        meta.append(["Käuferreferenz", inv["buyer_reference"]])
    if inv.get("order_reference"):
        meta.append(["Bestellnummer", inv["order_reference"]])
    if inv.get("preceding_invoice"):
        pi = inv["preceding_invoice"]
        meta.append(["Bezug auf Rechnung", f"{pi['number']} {date_de(pi.get('issue_date'))}".strip()])
    buyer_block = P(f"{b['name']}\n{b['street']}\n{b['postcode']} {b['city']}\n{b['country']}")
    meta_tbl = Table([[P(k, small), P(v)] for k, v in meta], colWidths=[32 * mm, 50 * mm])
    meta_tbl.setStyle(TableStyle([FONT_CMD]))
    head = Table([[buyer_block, meta_tbl]], colWidths=[88 * mm, 82 * mm])
    head.setStyle(TableStyle([FONT_CMD, ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [head, Spacer(1, 8 * mm), P(title, h1), Spacer(1, 4 * mm)]
    if inv.get("note"):
        story += [P(inv["note"]), Spacer(1, 3 * mm)]

    rows = [[P("Pos", bold), P("Beschreibung", bold), P("Menge", bold), P("Einheit", bold),
             P("Einzelpreis", bold), P("USt", bold), P("Betrag", bold)]]
    for i, (line, amount) in enumerate(zip(inv["lines"], t["lines"]), start=1):
        rate = "–" if line["vat_category"] == "O" else f"{num_de(D(line['vat_rate']))} %"
        rows.append([P(line.get("id") or str(i)), P(line["description"]), P(num_de(D(line["quantity"]))),
                     P(UNITS_DE.get(line["unit"], line["unit"])), P(eur(D(line["net_price"]))), P(rate), P(eur(amount))])
    lines_tbl = Table(rows, colWidths=[10 * mm, 60 * mm, 17 * mm, 18 * mm, 25 * mm, 14 * mm, 26 * mm], repeatRows=1)
    lines_tbl.setStyle(TableStyle([
        FONT_CMD,
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [lines_tbl, Spacer(1, 5 * mm)]

    sums = [["Summe netto", eur(t["net"])]]
    for g in t["groups"]:
        label = (f"USt {num_de(g['rate'])} % auf {eur(g['basis'])}" if g["rate"] is not None
                 else f"USt ({CATEGORY_DE[g['category']]}) auf {eur(g['basis'])}")
        sums.append([label, eur(g["vat"])])
    sums.append(["Gesamtbetrag", eur(t["gross"])])
    sums_tbl = Table([[P(k), P(v)] for k, v in sums[:-1]] + [[P(sums[-1][0], bold), P(sums[-1][1], bold)]],
                     colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    sums_tbl.setStyle(TableStyle([FONT_CMD, ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black)]))
    story += [sums_tbl, Spacer(1, 5 * mm)]

    for cat, ex in (inv.get("vat_exemptions") or {}).items():
        if any(line["vat_category"] == cat for line in inv["lines"]):
            text = " ".join(x for x in (ex.get("text"), f"({ex['code']})" if ex.get("code") else None) if x)
            story.append(P(f"Hinweis zur Umsatzsteuer ({CATEGORY_DE.get(cat, cat)}): {text}"))
    pay_lines = []
    if pay.get("due_date"):
        pay_lines.append(f"Zahlbar bis {date_de(pay['due_date'])}.")
    if pay.get("terms"):
        pay_lines.append(pay["terms"])
    if pay.get("iban"):
        bank = f"IBAN {pay['iban']}"
        if pay.get("bic"):
            bank += f" · BIC {pay['bic']}"
        if pay.get("account_name"):
            bank += f" · Kontoinhaber {pay['account_name']}"
        pay_lines.append(bank)
    story += [Spacer(1, 2 * mm), P("Zahlung", bold), P("\n".join(pay_lines)), Spacer(1, 8 * mm)]

    tax_ids = []
    if s.get("vat_id"):
        tax_ids.append(f"USt-IdNr. {s['vat_id']}")
    if s.get("tax_number"):
        tax_ids.append(f"Steuernummer {s['tax_number']}")
    if s.get("company_id"):
        tax_ids.append(s["company_id"])
    c = s["contact"]
    story.append(P(f"{s['name']} · {s['street']} · {s['postcode']} {s['city']} · {' · '.join(tax_ids)}\n"
                   f"Kontakt: {c['name']} · {c['phone']} · {c['email']}", small))
    return story


def _render(inv: dict) -> bytes:
    _fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Rechnung {inv['number']}", author=inv["seller"]["name"],
                            invariant=1, initialFontName=FONT, initialFontSize=9)

    def footer(canvas, d):
        canvas.setFont(FONT, 7)
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Seite {d.page}")

    doc.build(_story(inv), onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def render_pdf(invoice: dict) -> bytes:
    """Readable invoice PDF (not an e-invoice). Raises InvoiceInputError on bad input."""
    return _render(check_invoice(invoice, "zugferd"))


def render_pdfa3b(invoice: dict) -> bytes:
    """Visual PDF as PDF/A-3b, approved by pikepdf.pdfa (raises ImportError/PdfaError otherwise)."""
    import pikepdf
    from pikepdf import pdfa

    raw = _render(check_invoice(invoice, "zugferd"))
    pdf = pikepdf.open(io.BytesIO(raw))
    for page in pdf.pages:  # reportlab writes an empty /Trans that the allowlist validator does not check
        if "/Trans" in page.obj:
            del page.obj["/Trans"]
    out = io.BytesIO()
    pdfa.save(pdf, out, "3b")
    return out.getvalue()
