"""Negative tests: generator input errors and crafted XML rejected by the validator."""
from __future__ import annotations

import pytest
from helpers_engine import ids, remove, set_text, tree, dump

from engine import InvoiceInputError, build_cii, validate
from engine.validation import MAX_BYTES


def _errors(inv, profile="xrechnung"):
    with pytest.raises(InvoiceInputError) as exc:
        build_cii(inv, profile=profile)
    errs = exc.value.errors
    for e in errs:
        assert e.row == 0 and e.field.startswith("/") and e.message_de and e.code
    return {(e.field, e.code) for e in errs}


# ---------------------------------------------------------------- generator input

def test_missing_bt10_for_xrechnung_only(sample):
    inv = sample()
    del inv["buyer_reference"]
    assert ("/buyer_reference", "missing_required") in _errors(inv)
    build_cii(inv, profile="zugferd")  # fine for ZUGFeRD EN16931


def test_bad_iban(sample):
    inv = sample()
    inv["payment"]["iban"] = "DE89370400440532013001"
    assert ("/payment/iban", "bad_iban") in _errors(inv)


def test_missing_seller_contact(sample):
    inv = sample()
    del inv["seller"]["contact"]
    assert ("/seller/contact", "missing_required") in _errors(inv)


def test_exemption_missing_for_e(sample):
    inv = sample()
    inv["lines"][0]["vat_category"] = "E"
    inv["lines"][0]["vat_rate"] = "0"
    assert ("/vat_exemptions/E", "missing_exemption") in _errors(inv)


def test_exemption_reason_for_z_rejected(sample):
    inv = sample()
    inv["lines"][0]["vat_category"] = "Z"
    inv["lines"][0]["vat_rate"] = "0"
    inv["vat_exemptions"] = {"Z": {"text": "nicht erlaubt"}}
    assert ("/vat_exemptions/Z", "forbidden_exemption") in _errors(inv)


def test_missing_due_date_and_terms(sample):
    inv = sample()
    del inv["payment"]["due_date"], inv["payment"]["terms"]
    assert ("/payment/due_date", "missing_required") in _errors(inv)


def test_seller_without_vat_id_and_tax_number(sample):
    inv = sample()
    del inv["seller"]["vat_id"]
    assert ("/seller/vat_id", "missing_required") in _errors(inv)


def test_tax_number_alone_is_not_enough(sample):
    inv = sample()
    del inv["seller"]["vat_id"]
    inv["seller"]["tax_number"] = "045/123/45678"
    assert ("/seller/company_id", "missing_required") in _errors(inv)


def test_bad_date_and_float_money(sample):
    inv = sample()
    inv["issue_date"] = "2026-13-40"
    inv["lines"][0]["net_price"] = 12.5
    errs = _errors(inv)
    assert ("/issue_date", "bad_date") in errs
    assert ("/lines/0/net_price", "invalid_value") in errs


def test_negative_amount_and_missing_iban(sample):
    inv = sample()
    inv["lines"][1]["quantity"] = "-1"
    del inv["payment"]["iban"]
    errs = _errors(inv)
    assert ("/lines/1/quantity", "bad_number") in errs
    assert ("/payment/iban", "missing_required") in errs


def test_error_messages_contain_no_values(sample):
    inv = sample()
    inv["payment"]["iban"] = "DE00SECRET0000000000000"
    with pytest.raises(InvoiceInputError) as exc:
        build_cii(inv)
    assert all("SECRET" not in e.message_de for e in exc.value.errors)


# ---------------------------------------------------------------- crafted XML

@pytest.fixture
def xml(sample):
    return lambda: tree(build_cii(sample()))


def test_xml_missing_bt10(xml):
    r = validate(dump(remove(xml(), "//ram:BuyerReference")))
    assert not r["valid"] and "BR-DE-15" in ids(r, "XRechnung")
    msg = next(e for l in r["layers"] for e in l["errors"] if e["id"] == "BR-DE-15")
    assert "Leitweg-ID" in msg["message_de"] and msg["text_en"]


def test_xml_wrong_totals(xml):
    r = validate(dump(set_text(xml(), "//ram:GrandTotalAmount", "9999.99")))
    assert not r["valid"] and {"BR-CO-15", "BR-CO-16"} <= ids(r, "EN16931")


def test_xml_bad_iban_warns(xml):
    r = validate(dump(set_text(xml(), "//ram:IBANID", "DE00370400440532013000")))
    warn = {w["id"] for l in r["layers"] for w in l["warnings"]}
    assert "BR-DE-19" in warn


def test_xml_missing_seller_contact(xml):
    r = validate(dump(remove(xml(), "//ram:SellerTradeParty/ram:DefinedTradeContact")))
    assert not r["valid"] and "BR-DE-2" in ids(r)


def test_xml_exempt_without_reason(xml):
    root = xml()
    set_text(root, "//ram:CategoryCode", "E")
    set_text(root, "//ram:RateApplicablePercent", "0")
    set_text(root, "//ram:CalculatedAmount", "0.00")
    set_text(root, "//ram:TaxTotalAmount", "0.00")
    set_text(root, "//ram:GrandTotalAmount", "6056.72")
    set_text(root, "//ram:DuePayableAmount", "6056.72")
    r = validate(dump(root))
    assert not r["valid"] and "BR-E-10" in ids(r, "EN16931")


def test_xml_reason_for_zero_rated(xml):
    from lxml import etree
    from helpers_engine import NS
    root = xml()
    set_text(root, "//ram:CategoryCode", "Z")
    set_text(root, "//ram:RateApplicablePercent", "0")
    set_text(root, "//ram:CalculatedAmount", "0.00")
    set_text(root, "//ram:TaxTotalAmount", "0.00")
    set_text(root, "//ram:GrandTotalAmount", "6056.72")
    set_text(root, "//ram:DuePayableAmount", "6056.72")
    tax = root.xpath("//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", namespaces=NS)[0]
    reason = etree.Element(f"{{{NS['ram']}}}ExemptionReason")
    reason.text = "unzulässig"
    tax.find(f"{{{NS['ram']}}}TypeCode").addnext(reason)
    r = validate(dump(root))
    assert not r["valid"] and "BR-Z-10" in ids(r, "EN16931")


def test_xml_missing_due_date_and_terms(xml):
    r = validate(dump(remove(xml(), "//ram:SpecifiedTradePaymentTerms")))
    assert not r["valid"] and "BR-CO-25" in ids(r, "EN16931")


def test_xml_seller_without_tax_registration(xml):
    r = validate(dump(remove(xml(), "//ram:SellerTradeParty/ram:SpecifiedTaxRegistration")))
    assert not r["valid"] and {"BR-CO-26", "BR-DE-16"} <= ids(r)


XXE = b"""<?xml version="1.0"?>
<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">&xxe;</rsm:CrossIndustryInvoice>"""

LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]>
<l>&c;</l>"""


@pytest.mark.parametrize("payload", [XXE, LAUGHS])
def test_xxe_and_entity_expansion_rejected(payload):
    r = validate(payload, "evil.xml")
    assert not r["valid"] and ids(r) == {"XML-DOCTYPE"}
    assert "root:" not in str(r)


def test_oversize_rejected():
    r = validate(b"<a>" + b" " * (MAX_BYTES + 1) + b"</a>", "big.xml")
    assert not r["valid"] and ids(r) == {"FILE-TOO-LARGE"}
    assert all(not l["ran"] for l in r["layers"] if l["name"] != "XSD")


def test_not_wellformed_and_empty_and_unknown():
    assert ids(validate(b"<a><b></a>")) == {"XML-NOT-WELLFORMED"}
    assert ids(validate(b"")) == {"FILE-EMPTY"}
    assert ids(validate(b"<foo xmlns='urn:x'/>")) == {"FORMAT-UNKNOWN"}


def test_ubl_is_skipped_not_passed():
    r = validate(b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"/>', "x.xml")
    assert r["valid"] is False and all(not l["ran"] and l["skipped_reason"] for l in r["layers"])


def test_pdf_without_xml(sample):
    from engine import render_pdf
    r = validate(render_pdf(sample()), "rechnung.pdf")
    assert not r["valid"] and ids(r) == {"PDF-NO-XML"}


def test_pdf_with_embedded_cii_is_checked(sample):
    from facturx import generate_from_binary
    from engine import render_pdf
    inv = sample()
    del inv["buyer_reference"]
    pdf = generate_from_binary(render_pdf(inv), build_cii(inv, profile="zugferd"), flavor="factur-x",
                               level="en16931", check_xsd=False)
    r = validate(pdf, "rechnung.pdf")
    assert r["profile"] == "zugferd" and r["valid"], ids(r)
