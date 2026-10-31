"""Invoice model (contracts/invoice.schema.json) -> UN/CEFACT CII D16B XML.

Profiles:
- "xrechnung": XRechnung 3.0 CIUS (BT-24 = XRECHNUNG_ID, BT-10 required).
- "zugferd":   EN 16931 core (BT-24 = urn:cen.eu:en16931:2017), the XML part of
               ZUGFeRD/Factur-X profile EN16931.

All amounts are computed here with Decimal (ROUND_HALF_UP to cents), so the XML
cannot disagree with its own sums. The engine does not decide tax treatment:
VAT category, rate and exemption reasons come from the input.
"""
from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from lxml import etree

from .inputcheck import check_invoice

RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
NSMAP = {"rsm": RSM, "ram": RAM, "qdt": QDT, "udt": UDT}

XRECHNUNG_ID = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
EN16931_ID = "urn:cen.eu:en16931:2017"
GUIDELINE = {"xrechnung": XRECHNUNG_ID, "zugferd": EN16931_ID}
PEPPOL_PROCESS = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

CENT = Decimal("0.01")
NO_RATE_CATEGORIES = ("O",)  # BR-O-05 / BR-O-12: no VAT rate for "not subject to VAT"


def D(v) -> Decimal:
    return Decimal(str(v))


def money(v) -> Decimal:
    return D(v).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt2(v: Decimal) -> str:
    return f"{v:.2f}"


def fmt_dec(v: Decimal) -> str:
    """Plain decimal without exponent or superfluous trailing zeros ("100", "14.5")."""
    s = format(v.normalize(), "f")
    return s


# ---------------------------------------------------------------- totals

def compute_totals(inv: dict) -> dict:
    """Line amounts, VAT breakdown and document totals (all Decimal).

    `inv` must be schema-valid; it is not re-checked here.
    """
    lines = []
    breakdown: "OrderedDict[tuple[str, Decimal | None], Decimal]" = OrderedDict()
    for line in inv["lines"]:
        amount = money(D(line["quantity"]) * D(line["net_price"]))
        cat = line["vat_category"]
        rate = None if cat in NO_RATE_CATEGORIES else D(line["vat_rate"])
        key = (cat, rate)
        breakdown[key] = breakdown.get(key, Decimal("0")) + amount
        lines.append(amount)
    groups = []
    for (cat, rate), basis in sorted(breakdown.items(), key=lambda kv: (kv[0][0], kv[0][1] or Decimal(0))):
        vat = money(basis * rate / 100) if rate is not None else Decimal("0.00")
        groups.append({"category": cat, "rate": rate, "basis": money(basis), "vat": vat})
    net = money(sum(lines, Decimal("0")))
    vat_total = sum((g["vat"] for g in groups), Decimal("0.00"))
    gross = net + vat_total
    return {"lines": lines, "groups": groups, "net": net, "vat": vat_total, "gross": gross, "due": gross}


def totals_warning(invoice: dict) -> dict | None:
    """Compare `source.expected_totals` with the computed totals.

    Returns None when no expected totals are given or all given values agree,
    else {"expected": {...}, "computed": {...}} (strings) for the Report's
    `totals_warning`. Only keys present in expected_totals are compared.
    """
    expected = ((invoice.get("source") or {}).get("expected_totals")) or {}
    if not expected:
        return None
    t = compute_totals(invoice)
    computed = {"net": fmt2(t["net"]), "vat": fmt2(t["vat"]), "gross": fmt2(t["gross"])}
    differs = any(money(expected[k]) != t[k] for k in ("net", "vat", "gross") if k in expected)
    if not differs:
        return None
    return {"expected": dict(expected), "computed": computed}


# ---------------------------------------------------------------- XML helpers

def _el(parent, ns_tag: str, text=None, **attrs):
    prefix, tag = ns_tag.split(":")
    node = etree.SubElement(parent, f"{{{NSMAP[prefix]}}}{tag}", {k: str(v) for k, v in attrs.items()})
    if text is not None:
        node.text = str(text)
    return node


def _date102(parent, ns_tag: str, iso: str, qualified: bool = False):
    wrapper = _el(parent, ns_tag)
    _el(wrapper, "qdt:DateTimeString" if qualified else "udt:DateTimeString", iso.replace("-", ""), format="102")
    return wrapper


def _party(parent, tag: str, p: dict, seller: bool):
    node = _el(parent, tag)
    _el(node, "ram:Name", p["name"])
    if seller and p.get("company_id"):
        _el(_el(node, "ram:SpecifiedLegalOrganization"), "ram:ID", p["company_id"])  # BT-30
    if p.get("contact"):
        c = p["contact"]
        contact = _el(node, "ram:DefinedTradeContact")
        _el(contact, "ram:PersonName", c["name"])
        _el(_el(contact, "ram:TelephoneUniversalCommunication"), "ram:CompleteNumber", c["phone"])
        _el(_el(contact, "ram:EmailURIUniversalCommunication"), "ram:URIID", c["email"])
    addr = _el(node, "ram:PostalTradeAddress")
    _el(addr, "ram:PostcodeCode", p["postcode"])
    _el(addr, "ram:LineOne", p["street"])
    _el(addr, "ram:CityName", p["city"])
    _el(addr, "ram:CountryID", p["country"])
    _el(_el(node, "ram:URIUniversalCommunication"), "ram:URIID", p["electronic_address"],
        schemeID=p["electronic_address_scheme"])
    if p.get("vat_id"):
        _el(_el(node, "ram:SpecifiedTaxRegistration"), "ram:ID", p["vat_id"], schemeID="VA")  # BT-31 / BT-48
    if seller and p.get("tax_number"):
        _el(_el(node, "ram:SpecifiedTaxRegistration"), "ram:ID", p["tax_number"], schemeID="FC")  # BT-32
    return node


def _tax(parent, cat: str, rate: Decimal | None, *, calculated=None, basis=None, exemption=None):
    t = _el(parent, "ram:ApplicableTradeTax")
    if calculated is not None:
        _el(t, "ram:CalculatedAmount", fmt2(calculated))
    _el(t, "ram:TypeCode", "VAT")
    if exemption and exemption.get("text"):
        _el(t, "ram:ExemptionReason", exemption["text"])  # BT-120
    if basis is not None:
        _el(t, "ram:BasisAmount", fmt2(basis))
    _el(t, "ram:CategoryCode", cat)
    if exemption and exemption.get("code"):
        _el(t, "ram:ExemptionReasonCode", exemption["code"])  # BT-121
    if rate is not None:
        _el(t, "ram:RateApplicablePercent", fmt_dec(rate))
    return t


# ---------------------------------------------------------------- builder

def build_tree(inv: dict, profile: str) -> etree._Element:
    """Build the CII tree from a normalised, checked invoice."""
    totals = compute_totals(inv)
    cur = inv["currency"]
    root = etree.Element(f"{{{RSM}}}CrossIndustryInvoice", nsmap=NSMAP)
    ctx = _el(root, "rsm:ExchangedDocumentContext")
    if profile == "xrechnung":
        _el(_el(ctx, "ram:BusinessProcessSpecifiedDocumentContextParameter"), "ram:ID", PEPPOL_PROCESS)  # BT-23
    _el(_el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter"), "ram:ID", GUIDELINE[profile])  # BT-24

    doc = _el(root, "rsm:ExchangedDocument")
    _el(doc, "ram:ID", inv["number"])
    _el(doc, "ram:TypeCode", inv["type_code"])
    _date102(doc, "ram:IssueDateTime", inv["issue_date"])
    if inv.get("note"):
        _el(_el(doc, "ram:IncludedNote"), "ram:Content", inv["note"])

    tx = _el(root, "rsm:SupplyChainTradeTransaction")
    for i, (line, amount) in enumerate(zip(inv["lines"], totals["lines"]), start=1):
        item = _el(tx, "ram:IncludedSupplyChainTradeLineItem")
        _el(_el(item, "ram:AssociatedDocumentLineDocument"), "ram:LineID", line.get("id") or str(i))
        _el(_el(item, "ram:SpecifiedTradeProduct"), "ram:Name", line["description"])
        agr = _el(item, "ram:SpecifiedLineTradeAgreement")
        _el(_el(agr, "ram:NetPriceProductTradePrice"), "ram:ChargeAmount", fmt_dec(D(line["net_price"])))
        _el(_el(item, "ram:SpecifiedLineTradeDelivery"), "ram:BilledQuantity", fmt_dec(D(line["quantity"])),
            unitCode=line["unit"])
        stl = _el(item, "ram:SpecifiedLineTradeSettlement")
        cat = line["vat_category"]
        _tax(stl, cat, None if cat in NO_RATE_CATEGORIES else D(line["vat_rate"]))
        _el(_el(stl, "ram:SpecifiedTradeSettlementLineMonetarySummation"), "ram:LineTotalAmount", fmt2(amount))

    agreement = _el(tx, "ram:ApplicableHeaderTradeAgreement")
    if inv.get("buyer_reference"):
        _el(agreement, "ram:BuyerReference", inv["buyer_reference"])  # BT-10
    _party(agreement, "ram:SellerTradeParty", inv["seller"], seller=True)
    _party(agreement, "ram:BuyerTradeParty", inv["buyer"], seller=False)
    if inv.get("order_reference"):
        _el(_el(agreement, "ram:BuyerOrderReferencedDocument"), "ram:IssuerAssignedID", inv["order_reference"])

    delivery = _el(tx, "ram:ApplicableHeaderTradeDelivery")
    if inv.get("delivery_date"):
        _date102(_el(delivery, "ram:ActualDeliverySupplyChainEvent"), "ram:OccurrenceDateTime", inv["delivery_date"])

    settlement = _el(tx, "ram:ApplicableHeaderTradeSettlement")
    _el(settlement, "ram:InvoiceCurrencyCode", cur)
    pay = inv["payment"]
    pm = _el(settlement, "ram:SpecifiedTradeSettlementPaymentMeans")
    _el(pm, "ram:TypeCode", pay["means_code"])  # BT-81: 58 or 30
    if pay.get("iban"):
        acct = _el(pm, "ram:PayeePartyCreditorFinancialAccount")
        _el(acct, "ram:IBANID", pay["iban"].replace(" ", "").upper())
        if pay.get("account_name"):
            _el(acct, "ram:AccountName", pay["account_name"])
        if pay.get("bic"):
            _el(_el(pm, "ram:PayeeSpecifiedCreditorFinancialInstitution"), "ram:BICID", pay["bic"])

    exemptions = inv.get("vat_exemptions") or {}
    for g in totals["groups"]:
        cat = g["category"]
        rate = g["rate"] if g["rate"] is not None else Decimal("0")  # BR-DE-14: BT-119 always present
        _tax(settlement, cat, rate, calculated=g["vat"], basis=g["basis"],
             exemption=exemptions.get(cat) if cat not in ("S", "Z") else None)

    if inv.get("period"):
        per = _el(settlement, "ram:BillingSpecifiedPeriod")  # BG-14
        _date102(per, "ram:StartDateTime", inv["period"]["start"])
        _date102(per, "ram:EndDateTime", inv["period"]["end"])

    terms = _el(settlement, "ram:SpecifiedTradePaymentTerms")
    if pay.get("terms"):
        _el(terms, "ram:Description", pay["terms"])  # BT-20
    if pay.get("due_date"):
        _date102(terms, "ram:DueDateDateTime", pay["due_date"])  # BT-9

    summ = _el(settlement, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    _el(summ, "ram:LineTotalAmount", fmt2(totals["net"]))
    _el(summ, "ram:TaxBasisTotalAmount", fmt2(totals["net"]))
    _el(summ, "ram:TaxTotalAmount", fmt2(totals["vat"]), currencyID=cur)
    _el(summ, "ram:GrandTotalAmount", fmt2(totals["gross"]))
    _el(summ, "ram:DuePayableAmount", fmt2(totals["due"]))

    if inv.get("preceding_invoice"):
        ref = _el(settlement, "ram:InvoiceReferencedDocument")  # BG-3
        _el(ref, "ram:IssuerAssignedID", inv["preceding_invoice"]["number"])
        if inv["preceding_invoice"].get("issue_date"):
            _date102(ref, "ram:FormattedIssueDateTime", inv["preceding_invoice"]["issue_date"], qualified=True)
    return root


def build_cii(invoice: dict, profile: str = "xrechnung") -> bytes:
    """Return CII XML bytes (UTF-8). Raises InvoiceInputError on bad input."""
    inv = check_invoice(invoice, profile)
    root = build_tree(inv, profile)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
