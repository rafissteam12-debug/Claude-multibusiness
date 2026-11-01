"""Generator: samples, profiles, BT-32, exemptions, credit notes, payment, totals."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest
from helpers_engine import NS, ids, tree
from lxml import etree

import engine
from engine import build_cii, totals_warning, validate


def test_both_samples_valid(sample_files):
    assert len(sample_files) >= 2
    for f in sample_files:
        inv = json.loads(f.read_text(encoding="utf-8"))
        report = validate(build_cii(inv))
        assert report["valid"], (f.name, report)
        assert report["profile"] == "xrechnung"


def test_api_surface():
    for name in ("build_cii", "build_zugferd", "validate", "render_pdf", "FeatureUnavailable", "InvoiceInputError",
                 "validate_many", "totals_warning"):
        assert hasattr(engine, name)
    from contracts.types import FeatureUnavailable, InvoiceInputError
    assert engine.FeatureUnavailable is FeatureUnavailable and engine.InvoiceInputError is InvoiceInputError


def test_guideline_ids(sample):
    xr = tree(build_cii(sample()))
    gid = "//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID/text()"
    assert xr.xpath(gid, namespaces=NS) == ["urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"]
    inv = sample()
    del inv["buyer_reference"]  # not required for ZUGFeRD EN16931
    zf_xml = build_cii(inv, profile="zugferd")
    assert tree(zf_xml).xpath(gid, namespaces=NS) == ["urn:cen.eu:en16931:2017"]
    r = validate(zf_xml)
    assert r["profile"] == "zugferd" and r["valid"], r
    xr_layer = next(l for l in r["layers"] if l["name"] == "XRechnung")
    assert xr_layer["ran"] is False and xr_layer["skipped_reason"]


def test_unknown_profile(sample):
    with pytest.raises(ValueError):
        build_cii(sample(), profile="ubl")


def test_tax_number_fc_without_vat_id(sample):
    inv = sample()
    del inv["seller"]["vat_id"]
    inv["seller"]["tax_number"] = "045/123/45678"
    inv["seller"]["company_id"] = "HRB 99999 (fiktiv)"
    xml = build_cii(inv)
    regs = tree(xml).xpath("//ram:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", namespaces=NS)
    assert [(r.get("schemeID"), r.text) for r in regs] == [("FC", "045/123/45678")]
    assert validate(xml)["valid"]


def test_exempt_category_e_with_reason_and_code(sample):
    inv = sample()
    inv["lines"].append({"description": "Schulungsleistung", "quantity": "2", "net_price": "100",
                         "vat_category": "E", "vat_rate": "0"})
    inv["vat_exemptions"] = {"E": {"text": "Steuerfrei (fiktives Testbeispiel)", "code": "VATEX-EU-132"}}
    root = tree(build_cii(inv))
    e = root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax[ram:CategoryCode='E']", namespaces=NS)[0]
    assert e.findtext(f"{{{NS['ram']}}}ExemptionReason") == "Steuerfrei (fiktives Testbeispiel)"
    assert e.findtext(f"{{{NS['ram']}}}ExemptionReasonCode") == "VATEX-EU-132"
    s = root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax[ram:CategoryCode='S']", namespaces=NS)[0]
    assert s.find(f"{{{NS['ram']}}}ExemptionReason") is None
    assert validate(build_cii(inv))["valid"]


def test_zero_rated_never_gets_reason(sample):
    inv = sample()
    inv["lines"].append({"description": "Buch", "quantity": "1", "net_price": "10", "vat_category": "Z", "vat_rate": "0"})
    root = tree(build_cii(inv))
    z = root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax[ram:CategoryCode='Z']", namespaces=NS)
    assert z and z[0].find(f"{{{NS['ram']}}}ExemptionReason") is None
    assert validate(build_cii(inv))["valid"]


def test_credit_note_with_preceding_invoice(sample):
    inv = sample()
    inv["type_code"] = "381"
    inv["preceding_invoice"] = {"number": "RE-2026-0400", "issue_date": "2026-10-01"}
    xml = build_cii(inv)
    root = tree(xml)
    assert root.xpath("//rsm:ExchangedDocument/ram:TypeCode/text()", namespaces=NS) == ["381"]
    assert root.xpath("//ram:InvoiceReferencedDocument/ram:IssuerAssignedID/text()", namespaces=NS) == ["RE-2026-0400"]
    assert validate(xml)["valid"]


def test_payment_means_30_terms_only(sample):
    inv = sample()
    inv["payment"]["means_code"] = "30"
    del inv["payment"]["due_date"]
    xml = build_cii(inv)
    root = tree(xml)
    assert root.xpath("//ram:SpecifiedTradeSettlementPaymentMeans/ram:TypeCode/text()", namespaces=NS) == ["30"]
    assert not root.xpath("//ram:DueDateDateTime", namespaces=NS)
    assert validate(xml)["valid"]


def test_due_date_only(sample):
    inv = sample()
    del inv["payment"]["terms"]
    root = tree(build_cii(inv))
    assert not root.xpath("//ram:SpecifiedTradePaymentTerms/ram:Description", namespaces=NS)
    assert validate(build_cii(inv))["valid"]


def test_period_and_electronic_address_scheme(sample):
    inv = sample()
    del inv["delivery_date"]
    inv["period"] = {"start": "2026-10-01", "end": "2026-10-31"}
    inv["buyer"]["electronic_address"] = "991-01234-56"
    inv["buyer"]["electronic_address_scheme"] = "0204"
    root = tree(build_cii(inv))
    assert root.xpath("//ram:BuyerTradeParty/ram:URIUniversalCommunication/ram:URIID/@schemeID", namespaces=NS) == ["0204"]
    assert root.xpath("//ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString/text()", namespaces=NS) == ["20261001"]
    assert validate(build_cii(inv))["valid"]


def test_totals_decimal_exact():
    from engine.cii import compute_totals
    inv = {"lines": [{"quantity": "3", "net_price": "0.1", "vat_category": "S", "vat_rate": "19"},
                     {"quantity": "1", "net_price": "0.005", "vat_category": "S", "vat_rate": "7"}]}
    t = compute_totals(inv)
    assert t["net"] == Decimal("0.31") and t["vat"] == Decimal("0.06") and t["gross"] == Decimal("0.37")


def test_totals_warning(sample):
    inv = sample()
    assert totals_warning(inv) is None
    inv["source"] = {"expected_totals": {"net": "6056.72", "vat": "1150.78", "gross": "7207.50"}}
    assert totals_warning(inv) is None
    inv["source"]["expected_totals"]["gross"] = "7207.51"
    w = totals_warning(inv)
    assert w == {"expected": {"net": "6056.72", "vat": "1150.78", "gross": "7207.51"},
                 "computed": {"net": "6056.72", "vat": "1150.78", "gross": "7207.50"}}
    # source never reaches the XML
    assert b"7207.51" not in build_cii(inv)


def test_category_o_without_rate():
    inv = {
        "number": "RE-O-1", "issue_date": "2026-10-26", "buyer_reference": "KD-1",
        "seller": {"name": "Beispiel Beratung", "street": "Weg 1", "postcode": "10115", "city": "Berlin",
                   "country": "DE", "tax_number": "11/222/33333", "company_id": "HRB 11111 (fiktiv)", "electronic_address": "re@beratung.example",
                   "electronic_address_scheme": "EM",
                   "contact": {"name": "A. Muster", "phone": "+49 30 123456", "email": "a@beratung.example"}},
        "buyer": {"name": "Kunde AG", "street": "Allee 2", "postcode": "20095", "city": "Hamburg", "country": "DE",
                  "electronic_address": "ap@kunde.example", "electronic_address_scheme": "EM"},
        "lines": [{"description": "Leistung", "quantity": "1", "net_price": "500", "vat_category": "O", "vat_rate": "0"}],
        "payment": {"iban": "DE89370400440532013000", "due_date": "2026-11-09"},
        "vat_exemptions": {"O": {"code": "VATEX-EU-O", "text": "Nicht steuerbar (fiktives Testbeispiel)"}},
    }
    xml = build_cii(inv)
    root = tree(xml)
    assert not root.xpath("//ram:SpecifiedLineTradeSettlement//ram:RateApplicablePercent", namespaces=NS)  # BR-O-05
    assert root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent/text()",
                      namespaces=NS) == ["0"]  # BR-DE-14
    r = validate(xml)
    assert r["valid"], ids(r)


# ---------------------------------------------------------------- H5: BT-29 seller identifier

def _seller_id_only(sample, scheme=None):
    inv = sample()
    seller = inv["seller"]
    for k in ("vat_id", "company_id"):
        seller.pop(k, None)
    seller["tax_number"] = "045/123/45678"
    seller["seller_id"] = {"id": "LIEF-4711"} if scheme is None else {"id": "4000001000005", "scheme": scheme}
    return inv


@pytest.mark.parametrize("profile", ["xrechnung", "zugferd"])
def test_seller_id_and_tax_number_only_is_valid(sample, profile):
    inv = _seller_id_only(sample)
    if profile == "zugferd":
        del inv["buyer_reference"]
    xml = build_cii(inv, profile=profile)
    root = tree(xml)
    party = root.xpath("//ram:SellerTradeParty", namespaces=NS)[0]
    assert etree.QName(party[0]).localname == "ID" and party[0].text == "LIEF-4711"
    assert etree.QName(party[1]).localname == "Name"
    assert party.xpath("ram:SpecifiedTaxRegistration/ram:ID[@schemeID='FC']/text()", namespaces=NS) == ["045/123/45678"]
    assert not party.xpath("ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']", namespaces=NS)
    r = validate(xml)
    assert r["valid"], r
    assert all(l["ran"] and not l["errors"] for l in r["layers"][:3] if l["name"] != "XRechnung" or profile == "xrechnung")


def test_seller_global_id_with_scheme(sample):
    xml = build_cii(_seller_id_only(sample, scheme="0088"))
    party = tree(xml).xpath("//ram:SellerTradeParty", namespaces=NS)[0]
    assert etree.QName(party[0]).localname == "GlobalID" and party[0].get("schemeID") == "0088"
    assert party[0].text == "4000001000005" and etree.QName(party[1]).localname == "Name"
    assert validate(xml)["valid"]


def test_seller_id_is_written_before_name_with_vat_id_too(sample):
    inv = sample()
    inv["seller"]["seller_id"] = {"id": "LIEF-4711"}
    party = tree(build_cii(inv)).xpath("//ram:SellerTradeParty", namespaces=NS)[0]
    assert [etree.QName(c).localname for c in party][:2] == ["ID", "Name"]
    assert validate(build_cii(inv))["valid"]


# ---------------------------------------------------------------- L6: credit notes

def test_credit_note_without_due_date_and_with_bg3(sample):
    inv = sample()
    inv["type_code"] = "381"
    inv["payment"].pop("due_date", None)
    inv["payment"]["terms"] = "Der Betrag wird Ihrem Konto gutgeschrieben."
    inv["preceding_invoice"] = {"number": "RE-2026-0400", "issue_date": "2026-10-01"}
    xml = build_cii(inv)
    root = tree(xml)
    assert not root.xpath("//ram:DueDateDateTime", namespaces=NS)  # BT-9 only when explicitly given
    ref = root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:InvoiceReferencedDocument", namespaces=NS)
    assert len(ref) == 1
    assert ref[0].xpath("ram:IssuerAssignedID/text()", namespaces=NS) == ["RE-2026-0400"]
    assert ref[0].xpath("ram:FormattedIssueDateTime/*/text()", namespaces=NS) == ["20261001"]
    r = validate(xml)
    assert r["valid"], ids(r)


def test_credit_note_due_date_kept_when_given(sample):
    inv = sample()
    inv["type_code"] = "381"
    inv["payment"]["due_date"] = "2026-11-30"
    root = tree(build_cii(inv))
    assert root.xpath("//ram:DueDateDateTime/*/text()", namespaces=NS) == ["20261130"]
    assert not root.xpath("//ram:InvoiceReferencedDocument", namespaces=NS)  # no BG-3 without input
