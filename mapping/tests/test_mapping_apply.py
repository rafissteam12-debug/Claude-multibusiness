from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from mapping import MappingError, apply, propose
from mapping.fixtures.make_fixtures import FIXTURES
from mapping.targets import invoice_schema, seller_profile_schema

VALIDATOR = Draft202012Validator(invoice_schema(), format_checker=FormatChecker())

INVOICE_COUNTS = {"lexware_like.csv": 5, "sevdesk_like.csv": 4, "excel_handmade.xlsx": 3, "access_export.csv": 4,
                  "row_per_line.csv": 3, "no_vat_column.csv": 3, "mixed_vat.csv": 2, "credit_notes.csv": 4}


def test_seller_profile_fixture_is_valid(seller_profile):
    schema = invoice_schema()
    registry = Registry().with_resource("invoice.schema.json", Resource.from_contents(schema))
    v = Draft202012Validator(seller_profile_schema(), registry=registry, format_checker=FormatChecker())
    assert list(v.iter_errors(seller_profile)) == []


@pytest.mark.parametrize("name", FIXTURES)
def test_apply_output_validates_against_schema(name, load, seller_profile):
    table = load(name)
    invoices, errors = apply(table, propose(table, seller_profile), seller_profile)
    assert errors == []
    assert len(invoices) == INVOICE_COUNTS[name]
    for inv in invoices:
        assert list(VALIDATOR.iter_errors(inv)) == [], inv["number"]
        assert inv["seller"] == seller_profile["seller"]  # profile always wins
        assert inv["payment"]["iban"] == "DE89370400440532013000"
        assert inv["source"]["row_numbers"]


def _by_number(invoices):
    return {i["number"]: i for i in invoices}


def test_row_per_line_groups_lines(load, seller_profile):
    t = load("row_per_line.csv")
    invs = _by_number(apply(t, propose(t, seller_profile), seller_profile)[0])
    assert [len(invs[n]["lines"]) for n in ("2026-301", "2026-302", "2026-303")] == [3, 2, 1]
    first = invs["2026-301"]
    assert first["buyer_reference"] == "04011000-1234512345-06"
    assert first["order_reference"] == "B-55120"
    assert [l["unit"] for l in first["lines"]] == ["C62", "HUR", "C62"]
    assert first["lines"][0] == {"id": "1", "description": "Druck Broschüre A5, 500 Stück", "quantity": "500", "unit": "C62",
                                 "net_price": "0.84", "vat_rate": "19", "vat_category": "S"}
    assert invs["2026-302"]["lines"][1]["quantity"] == "1000"
    assert first["source"]["row_numbers"] == [2, 3, 4]


def test_due_date_from_payment_days_and_from_column(load, seller_profile):
    t = load("lexware_like.csv")
    inv = _by_number(apply(t, propose(t, seller_profile), seller_profile)[0])["RE-2026-0101"]
    assert inv["issue_date"] == "2026-10-02" and inv["payment"]["due_date"] == "2026-10-16"
    assert inv["delivery_date"] == "2026-09-30"
    assert inv["source"]["expected_totals"] == {"net": "255.00", "vat": "48.45", "gross": "303.45"}
    assert inv["buyer"]["country"] == "DE"  # 'Deutschland' -> DE
    t2 = load("no_vat_column.csv")
    inv2 = _by_number(apply(t2, propose(t2, seller_profile), seller_profile)[0])["2026/0451"]
    assert inv2["payment"]["due_date"] == "2026-10-15"


def test_gross_to_net_uses_line_rate(load, seller_profile):
    t = load("mixed_vat.csv")
    inv = _by_number(apply(t, propose(t, seller_profile), seller_profile)[0])["CAT-2026-88"]
    assert [(l["net_price"], l["vat_rate"]) for l in inv["lines"]] == [("2.00", "7"), ("8.00", "7"), ("30.00", "19"), ("35.00", "19")]


def test_credit_notes_become_381_with_positive_amounts(load, seller_profile):
    t = load("credit_notes.csv")
    invs = _by_number(apply(t, propose(t, seller_profile), seller_profile)[0])
    gs = invs["GS-2026-0007"]
    assert gs["type_code"] == "381"
    assert gs["lines"][0]["net_price"] == "45.00"
    assert gs["preceding_invoice"] == {"number": "RE-2026-0101"}
    assert gs["source"]["expected_totals"] == {"net": "45.00", "gross": "53.55"}
    assert invs["RE-2026-0101"]["type_code"] == "380" and "preceding_invoice" not in invs["RE-2026-0101"]


def test_excel_postcode_leading_zero_restored(load, seller_profile):
    t = load("excel_handmade.xlsx")
    inv = _by_number(apply(t, propose(t, seller_profile), seller_profile)[0])["26041"]
    assert inv["buyer"]["postcode"] == "01067"
    assert inv["lines"][0]["unit"] == "HUR" and inv["lines"][0]["quantity"] == "7.5"


# ---------------------------------------------------------------- RowErrors on broken rows

HEADER = "Rechnungsnr;Rechnungsdatum;Kunde;Straße;PLZ;Ort;E-Mail;Bezeichnung;Menge;Einheit;Einzelpreis;MwSt-Satz\n"
GOOD = "R-1;01.10.2026;A GmbH;Weg 1;10115;Berlin;a@a.example;Teil;1;Stk;10,00;19\n"


def _errors(csv_table, seller_profile, body: str, mapping_from: str | None = None):
    t = csv_table(HEADER + body)
    base = csv_table(HEADER + GOOD + GOOD.replace("R-1", "R-2")) if mapping_from is None else csv_table(mapping_from)
    m = propose(base, seller_profile)
    return apply(t, m, seller_profile)


def test_bad_date_message(csv_table, seller_profile):
    invs, errs = _errors(csv_table, seller_profile, GOOD + GOOD.replace("R-1", "R-2").replace("01.10.2026", "31.13.2026"))
    assert [i["number"] for i in invs] == ["R-1"]
    assert len(errs) == 1
    e = errs[0]
    assert (e.row, e.column, e.field, e.code) == (3, "Rechnungsdatum", "/issue_date", "bad_date")
    assert e.message_de == "Zeile 3: Rechnungsdatum '31.13.2026' ist kein gültiges Datum"


def test_bad_number_unknown_unit_missing_fields(csv_table, seller_profile):
    body = (GOOD
            + "R-2;01.10.2026;B GmbH;Weg 2;10115;Berlin;b@b.example;Teil;eins;Stk;10,00;19\n"
            + "R-3;01.10.2026;C GmbH;Weg 3;10115;Berlin;c@c.example;Teil;1;Fass;10,00;19\n"
            + "R-4;01.10.2026;D GmbH;;;Berlin;d@d.example;Teil;1;Stk;10,00;19\n"
            + "R-5;01.10.2026;E GmbH;Weg 5;10115;Berlin;;;1;Stk;10,00;19\n")
    invs, errs = _errors(csv_table, seller_profile, body)
    assert [i["number"] for i in invs] == ["R-1"]
    codes = {(e.row, e.code, e.field) for e in errs}
    assert (3, "bad_number", "/lines/*/quantity") in codes
    assert (4, "unknown_unit", "/lines/*/unit") in codes
    assert (5, "buyer_address_missing", "/buyer/street") in codes
    assert (5, "buyer_address_missing", "/buyer/postcode") in codes
    assert (6, "missing_required", "/buyer/electronic_address") in codes
    assert (6, "missing_required", "/lines/*/description") in codes
    assert all(e.message_de.startswith(f"Zeile {e.row}: ") for e in errs)


def test_negative_without_abs_and_mixed_signs(csv_table, seller_profile):
    # mapping proposed on positive data has no 'abs' -> negative price is an error
    invs, errs = _errors(csv_table, seller_profile, GOOD.replace("10,00", "-10,00"))
    assert invs == [] and errs[0].code == "negative_amount" and "abs" in errs[0].message_de
    # mixed signs inside one invoice (row per line, 'abs' present)
    lines = HEADER + GOOD + GOOD + GOOD.replace("10,00", "-5,00")
    t = csv_table(lines)
    m = propose(t, seller_profile)
    assert m["grouping"]["mode"] == "row_per_line"
    invs, errs = apply(t, m, seller_profile)
    assert invs == []
    assert [(e.row, e.code) for e in errs] == [(4, "negative_amount")]


def test_inconsistent_header_in_line_rows(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD + GOOD.replace("A GmbH", "Andere GmbH"))
    m = propose(t, seller_profile)
    invs, errs = apply(t, m, seller_profile)
    assert invs == []
    assert [(e.row, e.code, e.field) for e in errs] == [(3, "inconsistent_invoice", "/buyer/name")]


def test_continuation_rows_without_number(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD + ";;;;;;;Zweite Position;2;Std;50,00;19\n" + GOOD.replace("R-1", "R-2") + ";;;;;;;Noch was;1;Stk;1,00;7\n")
    m = propose(t, seller_profile)
    assert m["grouping"]["mode"] == "row_per_line"
    invs, errs = apply(t, m, seller_profile)
    assert errs == []
    assert [len(i["lines"]) for i in invs] == [2, 2]
    assert invs[1]["lines"][1]["vat_rate"] == "7"


def test_duplicate_number_in_row_per_invoice_mode(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD + GOOD)
    m = propose(t, seller_profile)
    m["grouping"]["mode"] = "row_per_invoice"
    invs, errs = apply(t, m, seller_profile)
    assert any(e.code == "inconsistent_invoice" and e.row == 3 for e in errs)


def test_profile_without_iban_or_due_date(csv_table, seller_profile):
    sp = copy.deepcopy(seller_profile)
    del sp["payment_defaults"]["iban"]
    del sp["payment_defaults"]["payment_days"]
    t = csv_table(HEADER + GOOD)
    invs, errs = apply(t, propose(t, sp), sp)
    assert invs == []
    assert {e.field for e in errs} == {"/payment/iban", "/payment/due_date"}


def test_zero_rate_uses_default_category_and_exemption(csv_table, seller_profile):
    sp = copy.deepcopy(seller_profile)
    sp["defaults"]["vat_category"] = "E"
    sp["defaults"]["vat_exemptions"] = {"E": {"text": "Steuerbefreit (Testtext)"}}
    t = csv_table(HEADER + GOOD.replace(";19\n", ";0\n"))
    invs, errs = apply(t, propose(t, sp), sp)
    assert errs == []
    assert invs[0]["lines"][0]["vat_category"] == "E"
    assert invs[0]["vat_exemptions"] == {"E": {"text": "Steuerbefreit (Testtext)"}}


def test_invalid_mapping_raises(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD)
    m = propose(t, seller_profile)
    bad = copy.deepcopy(m)
    bad["fields"].append({"target": "/seller/name", "constant": "X"})
    with pytest.raises(MappingError):
        apply(t, bad, seller_profile)
    bad = copy.deepcopy(m)
    bad["fields"][0]["transform"] = ["rot13"]
    with pytest.raises(MappingError):
        apply(t, bad, seller_profile)
    bad = copy.deepcopy(m)
    bad["fields"][0]["source_column"] = "Gibt es nicht"
    with pytest.raises(MappingError):
        apply(t, bad, seller_profile)


def test_new_codes_invalid_value_bad_iban_missing_exemption(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD)
    m = propose(t, seller_profile)
    sp = copy.deepcopy(seller_profile)
    sp["payment_defaults"]["iban"] = "DE89370400440532013001"  # wrong check digits
    invs, errs = apply(t, m, sp)
    assert invs == [] and [(e.code, e.field) for e in errs] == [("bad_iban", "/payment/iban")]

    m2 = copy.deepcopy(m)
    for f in m2["fields"]:
        if f["target"] == "/lines/*/vat_category":
            f.clear()
            f.update({"target": "/lines/*/vat_category", "constant": "X"})
    invs, errs = apply(t, m2, seller_profile)
    assert [(e.code, e.field) for e in errs] == [("invalid_value", "/lines/*/vat_category")]

    sp = copy.deepcopy(seller_profile)
    sp["defaults"]["vat_category"] = "E"  # 0 % -> E, but no exemption text configured
    t0 = csv_table(HEADER + GOOD.replace(";19\n", ";0\n"))
    invs, errs = apply(t0, propose(t0, sp), sp)
    assert invs == [] and [(e.row, e.code) for e in errs] == [(2, "missing_exemption")]


ZERO_MSG = ("Zeile 2: 0 % Umsatzsteuer: Bitte wählen Sie die Kategorie (z. B. steuerfrei, innergemeinschaftlich, "
            "Kleinunternehmer) in der Zuordnung.")


def test_zero_rate_with_default_s_is_not_guessed(csv_table, seller_profile):
    # review M4: 0 % with seller default S used to become Z silently
    t = csv_table(HEADER + GOOD.replace(";19\n", ";0\n") + GOOD.replace("R-1", "R-2"))
    m = propose(t, seller_profile)
    invs, errs = apply(t, m, seller_profile)
    assert [i["number"] for i in invs] == ["R-2"]
    assert [(e.row, e.column, e.field, e.code) for e in errs] == [(2, "MwSt-Satz", "/lines/*/vat_category", "missing_exemption")]
    assert errs[0].message_de == ZERO_MSG


def test_zero_rate_with_explicit_category_constant_or_column(csv_table, seller_profile):
    sp = copy.deepcopy(seller_profile)
    sp["defaults"]["vat_exemptions"] = {"AE": {"text": "Steuerschuldnerschaft des Leistungsempfängers (Testtext)"}}
    t = csv_table(HEADER + GOOD.replace(";19\n", ";0\n"))
    m = propose(t, sp)
    for f in m["fields"]:
        if f["target"] == "/lines/*/vat_category":
            f.clear()
            f.update({"target": "/lines/*/vat_category", "constant": "Z", "confidence": 1.0})
    invs, errs = apply(t, m, sp)
    assert errs == [] and invs[0]["lines"][0]["vat_category"] == "Z"

    t2 = csv_table(HEADER.replace("\n", ";Kat\n") + GOOD.replace(";19\n", ";0;AE\n"))
    m2 = propose(t2, sp)
    for f in m2["fields"]:
        if f["target"] == "/lines/*/vat_category":
            f.clear()
            f.update({"target": "/lines/*/vat_category", "source_column": "Kat", "transform": [], "confidence": 1.0})
    invs, errs = apply(t2, m2, sp)
    assert errs == [] and invs[0]["lines"][0]["vat_category"] == "AE"


def test_zero_rate_without_category_mapping_uses_message(csv_table, seller_profile):
    t = csv_table(HEADER + GOOD.replace(";19\n", ";0\n"))
    m = propose(t, seller_profile)
    m["fields"] = [f for f in m["fields"] if f["target"] != "/lines/*/vat_category"]
    invs, errs = apply(t, m, seller_profile)
    assert [(e.code, e.message_de) for e in errs] == [("missing_exemption", ZERO_MSG)]


DT_HEADER = "Rechnungsnr;Belegart;Bezug;Rechnungsdatum;Kunde;Straße;PLZ;Ort;E-Mail;Bezeichnung;Menge;Einheit;Einzelpreis;MwSt-Satz\n"
DT_ROW = "{n};{art};{bezug};01.10.2026;A GmbH;Weg 1;10115;Berlin;a@a.example;Teil;1;Stk;{preis};19\n"


def test_doc_type_column_detected_and_applied(csv_table, seller_profile):
    # review M5 / L6: Belegart decides 380/381; Bezug -> preceding invoice
    body = (DT_ROW.format(n="R-1", art="Rechnung", bezug="", preis="100,00")
            + DT_ROW.format(n="G-1", art="Gutschrift", bezug="R-1", preis="250,00")
            + DT_ROW.format(n="S-1", art="Storno", bezug="R-1", preis="-100,00"))
    t = csv_table(DT_HEADER + body)
    m = propose(t, seller_profile)
    f = {x["target"]: x for x in m["fields"]}
    assert f["/type_code"]["source_column"] == "Belegart" and f["/type_code"]["transform"] == ["doc_type"]
    assert f["/preceding_invoice/number"]["source_column"] == "Bezug"
    invs, errs = apply(t, m, seller_profile)
    assert errs == []
    by = _by_number(invs)
    assert by["R-1"]["type_code"] == "380" and "preceding_invoice" not in by["R-1"]
    assert by["G-1"]["type_code"] == "381" and by["G-1"]["lines"][0]["net_price"] == "250.00"
    assert by["G-1"]["preceding_invoice"] == {"number": "R-1"}
    assert by["S-1"]["type_code"] == "381" and by["S-1"]["lines"][0]["net_price"] == "100.00"
    for inv in invs:
        assert list(VALIDATOR.iter_errors(inv)) == []


def test_doc_type_negative_without_abs_is_flipped_for_381(csv_table, seller_profile):
    pos = csv_table(DT_HEADER + DT_ROW.format(n="G-1", art="Gutschrift", bezug="", preis="250,00"))
    m = propose(pos, seller_profile)  # proposed on positive data: no 'abs'
    assert "abs" not in next(x for x in m["fields"] if x["target"] == "/lines/*/net_price")["transform"]
    t = csv_table(DT_HEADER + DT_ROW.format(n="G-1", art="credit note", bezug="", preis="-250,00")
                  + DT_ROW.format(n="R-2", art="Rechnung", bezug="", preis="-5,00")
                  + DT_ROW.format(n="X-3", art="Lieferschein", bezug="", preis="5,00"))
    invs, errs = apply(t, m, seller_profile)
    assert [(i["number"], i["type_code"], i["lines"][0]["net_price"]) for i in invs] == [("G-1", "381", "250.00")]
    got = {(e.row, e.field, e.code) for e in errs}
    assert (3, "/lines/*/net_price", "negative_amount") in got  # 380 rows still need 'abs'
    assert (4, "/type_code", "invalid_value") in got


def test_doc_type_380_with_all_negative_amounts_is_an_error(csv_table, seller_profile):
    neg = csv_table(DT_HEADER + DT_ROW.format(n="R-1", art="Rechnung", bezug="", preis="-5,00"))
    m = propose(neg, seller_profile)  # has 'abs'
    invs, errs = apply(neg, m, seller_profile)
    assert invs == [] and [(e.field, e.code) for e in errs] == [("/type_code", "invalid_value")]
