"""Belegbruecke demo: turn a simple invoice export into an XRechnung 3.0 (CII) e-invoice.

Input: a JSON file with the fields a legacy invoicing tool or spreadsheet already
holds (see samples/). Output: an XRechnung 3.0 CII XML file, and optionally a
ZUGFeRD-style hybrid PDF (visual PDF with the same XML embedded) when --pdf is passed.

The tool computes line totals, VAT breakdown and invoice totals itself with
decimal arithmetic, so the structured data cannot disagree with its own sums.
It is a technical converter: it does not decide tax treatment. VAT category and
rate come from the input and must be confirmed by the customer or their tax adviser.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from lxml import etree

RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
NSMAP = {"rsm": RSM, "ram": RAM, "qdt": QDT, "udt": UDT}
XRECHNUNG_ID = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
PEPPOL_PROCESS = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

CENT = Decimal("0.01")


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(v: Decimal) -> str:
    return f"{v:.2f}"


def el(parent, ns_tag: str, text=None, **attrs):
    prefix, tag = ns_tag.split(":")
    node = etree.SubElement(parent, f"{{{NSMAP[prefix]}}}{tag}", {k: str(v) for k, v in attrs.items()})
    if text is not None:
        node.text = str(text)
    return node


def date102(parent, ns_tag: str, iso: str):
    wrapper = el(parent, ns_tag)
    el(wrapper, "udt:DateTimeString", iso.replace("-", ""), format="102")
    return wrapper


def party(parent, tag: str, p: dict, seller: bool):
    node = el(parent, tag)
    el(node, "ram:Name", p["name"])
    if seller and p.get("contact"):
        c = p["contact"]
        contact = el(node, "ram:DefinedTradeContact")
        el(contact, "ram:PersonName", c["name"])
        tel = el(contact, "ram:TelephoneUniversalCommunication")
        el(tel, "ram:CompleteNumber", c["phone"])
        mail = el(contact, "ram:EmailURIUniversalCommunication")
        el(mail, "ram:URIID", c["email"])
    addr = el(node, "ram:PostalTradeAddress")
    el(addr, "ram:PostcodeCode", p["postcode"])
    el(addr, "ram:LineOne", p["street"])
    el(addr, "ram:CityName", p["city"])
    el(addr, "ram:CountryID", p.get("country", "DE"))
    uri = el(node, "ram:URIUniversalCommunication")
    el(uri, "ram:URIID", p["electronic_address"], schemeID=p.get("electronic_address_scheme", "EM"))
    if p.get("vat_id"):
        reg = el(node, "ram:SpecifiedTaxRegistration")
        el(reg, "ram:ID", p["vat_id"], schemeID="VA")
    return node


def build(inv: dict) -> tuple[etree._Element, dict]:
    root = etree.Element(f"{{{RSM}}}CrossIndustryInvoice", nsmap=NSMAP)
    ctx = el(root, "rsm:ExchangedDocumentContext")
    el(el(ctx, "ram:BusinessProcessSpecifiedDocumentContextParameter"), "ram:ID", PEPPOL_PROCESS)
    el(el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter"), "ram:ID", XRECHNUNG_ID)

    doc = el(root, "rsm:ExchangedDocument")
    el(doc, "ram:ID", inv["number"])
    el(doc, "ram:TypeCode", inv.get("type_code", "380"))
    date102(doc, "ram:IssueDateTime", inv["issue_date"])
    if inv.get("note"):
        el(el(doc, "ram:IncludedNote"), "ram:Content", inv["note"])

    tx = el(root, "rsm:SupplyChainTradeTransaction")
    breakdown: dict[tuple[str, Decimal], Decimal] = defaultdict(lambda: Decimal("0"))
    line_total_sum = Decimal("0")
    for i, line in enumerate(inv["lines"], start=1):
        qty = Decimal(str(line["quantity"]))
        price = Decimal(str(line["net_price"]))
        amount = money(qty * price)
        cat, rate = line.get("vat_category", "S"), Decimal(str(line.get("vat_rate", 19)))
        breakdown[(cat, rate)] += amount
        line_total_sum += amount

        item = el(tx, "ram:IncludedSupplyChainTradeLineItem")
        el(el(item, "ram:AssociatedDocumentLineDocument"), "ram:LineID", str(i))
        el(el(item, "ram:SpecifiedTradeProduct"), "ram:Name", line["description"])
        agr = el(item, "ram:SpecifiedLineTradeAgreement")
        el(el(agr, "ram:NetPriceProductTradePrice"), "ram:ChargeAmount", f"{price:.4f}")
        el(el(item, "ram:SpecifiedLineTradeDelivery"), "ram:BilledQuantity", f"{qty}", unitCode=line.get("unit", "C62"))
        stl = el(item, "ram:SpecifiedLineTradeSettlement")
        tax = el(stl, "ram:ApplicableTradeTax")
        el(tax, "ram:TypeCode", "VAT")
        el(tax, "ram:CategoryCode", cat)
        el(tax, "ram:RateApplicablePercent", f"{rate.normalize()}")
        el(el(stl, "ram:SpecifiedTradeSettlementLineMonetarySummation"), "ram:LineTotalAmount", fmt(amount))

    agreement = el(tx, "ram:ApplicableHeaderTradeAgreement")
    el(agreement, "ram:BuyerReference", inv["buyer_reference"])
    party(agreement, "ram:SellerTradeParty", inv["seller"], seller=True)
    party(agreement, "ram:BuyerTradeParty", inv["buyer"], seller=False)
    if inv.get("order_reference"):
        el(el(agreement, "ram:BuyerOrderReferencedDocument"), "ram:IssuerAssignedID", inv["order_reference"])

    delivery = el(tx, "ram:ApplicableHeaderTradeDelivery")
    if inv.get("delivery_date"):
        event = el(delivery, "ram:ActualDeliverySupplyChainEvent")
        date102(event, "ram:OccurrenceDateTime", inv["delivery_date"])

    settlement = el(tx, "ram:ApplicableHeaderTradeSettlement")
    el(settlement, "ram:InvoiceCurrencyCode", inv.get("currency", "EUR"))
    pm = el(settlement, "ram:SpecifiedTradeSettlementPaymentMeans")
    el(pm, "ram:TypeCode", "58")
    acct = el(pm, "ram:PayeePartyCreditorFinancialAccount")
    el(acct, "ram:IBANID", inv["payment"]["iban"])
    if inv["payment"].get("account_name"):
        el(acct, "ram:AccountName", inv["payment"]["account_name"])

    tax_total = Decimal("0")
    for (cat, rate), basis in sorted(breakdown.items()):
        vat = money(basis * rate / 100)
        tax_total += vat
        t = el(settlement, "ram:ApplicableTradeTax")
        el(t, "ram:CalculatedAmount", fmt(vat))
        el(t, "ram:TypeCode", "VAT")
        if cat != "S" and inv.get("vat_exemption_reason"):
            el(t, "ram:ExemptionReason", inv["vat_exemption_reason"])
        el(t, "ram:BasisAmount", fmt(money(basis)))
        el(t, "ram:CategoryCode", cat)
        el(t, "ram:RateApplicablePercent", f"{rate.normalize()}")

    terms = el(settlement, "ram:SpecifiedTradePaymentTerms")
    if inv["payment"].get("terms"):
        el(terms, "ram:Description", inv["payment"]["terms"])
    date102(terms, "ram:DueDateDateTime", inv["payment"]["due_date"])

    net = money(line_total_sum)
    gross = net + tax_total
    summ = el(settlement, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    el(summ, "ram:LineTotalAmount", fmt(net))
    el(summ, "ram:TaxBasisTotalAmount", fmt(net))
    el(summ, "ram:TaxTotalAmount", fmt(tax_total), currencyID=inv.get("currency", "EUR"))
    el(summ, "ram:GrandTotalAmount", fmt(gross))
    el(summ, "ram:DuePayableAmount", fmt(gross))

    totals = {"net": fmt(net), "vat": fmt(tax_total), "gross": fmt(gross), "lines": len(inv["lines"])}
    return root, totals


def write_pdf(inv: dict, totals: dict, xml_bytes: bytes, out_pdf: Path) -> None:
    """Visual PDF with the XML embedded (ZUGFeRD/Factur-X style hybrid).

    Note: a conformant ZUGFeRD file must also be PDF/A-3 and use the ZUGFeRD
    profile identifier; this demo embeds the XRechnung XML for illustration only.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from facturx import generate_from_binary

    tmp = out_pdf.with_suffix(".visual.pdf")
    c = canvas.Canvas(str(tmp), pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Rechnung {inv['number']}  ·  {inv['issue_date']}")
    c.setFont("Helvetica", 10)
    y -= 24
    c.drawString(50, y, f"{inv['seller']['name']} → {inv['buyer']['name']}")
    y -= 30
    for line in inv["lines"]:
        c.drawString(50, y, f"{line['quantity']} × {line['description']} à {line['net_price']} EUR (USt {line.get('vat_rate', 19)}%)")
        y -= 16
    y -= 10
    c.drawString(50, y, f"Netto {totals['net']} EUR   USt {totals['vat']} EUR   Brutto {totals['gross']} EUR")
    y -= 30
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, y, "Demo-Datei von Belegbrücke. Strukturierte Rechnungsdaten sind als XML eingebettet.")
    c.save()
    pdf = generate_from_binary(tmp.read_bytes(), xml_bytes, check_xsd=False, flavor="factur-x", level="en16931")
    out_pdf.write_bytes(pdf)
    tmp.unlink()


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python generate.py input.json output.xml [--pdf]")
        return 2
    inv = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root, totals = build(inv)
    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    out = Path(sys.argv[2])
    out.write_bytes(xml_bytes)
    print(f"wrote {out}  net {totals['net']}  VAT {totals['vat']}  gross {totals['gross']}")
    if "--pdf" in sys.argv:
        write_pdf(inv, totals, xml_bytes, out.with_suffix(".pdf"))
        print(f"wrote {out.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
