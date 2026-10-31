from __future__ import annotations

import pytest

from mapping import propose, validate_mapping
from mapping.fixtures.make_fixtures import FIXTURES
from mapping.scoring import expected_for, score
from mapping.targets import ALLOWED_TARGETS, TRANSFORMS, pointer_exists_in_schema

SCORES: dict[str, dict] = {}


@pytest.mark.parametrize("name", FIXTURES)
def test_heuristic_score_at_least_80_percent(name, load, seller_profile):
    table = load(name)
    mapping = propose(table, seller_profile)
    s = score(mapping, expected_for(name))
    SCORES[name] = s
    print(f"\n{name}: required {s['required_score']:.0%}, all fields {s['all_score']:.0%}, wrong {s['all_wrong']}")
    assert s["required_score"] >= 0.8, s


@pytest.mark.parametrize("name", FIXTURES)
def test_mapping_is_contract_conform(name, load, seller_profile):
    table = load(name)
    m = propose(table, seller_profile)
    assert validate_mapping(m, table.columns) == []
    assert m["provider"] == "heuristic" and m["version"] == 1 and m["mapping_id"]
    for f in m["fields"]:
        assert f["target"] in ALLOWED_TARGETS
        assert not f["target"].startswith("/seller")
        assert ("source_column" in f) != ("constant" in f)
        assert all(t in TRANSFORMS for t in f.get("transform", []))
        assert 0 <= f["confidence"] <= 1
        assert f["reason_de"]
        # reasons and constants must not carry cell values (mappings are stored)
        cells = {c for row in table.rows for c in row if len(c) > 3 and (any(ch.isdigit() for ch in c) or "@" in c or " " in c)}
        assert not any(c in f["reason_de"] for c in cells), f
        if "constant" in f:
            assert f["constant"] not in cells or f["constant"] in ("1", "19", "DE", "EM", "C62", "HUR", "S")


def test_all_targets_exist_in_schema():
    for t in ALLOWED_TARGETS:
        assert pointer_exists_in_schema(t), t
    assert not pointer_exists_in_schema("/lines/*/gross_price")
    assert not pointer_exists_in_schema("/buyer/nickname")


def test_grouping_detection(load, seller_profile):
    assert propose(load("row_per_line.csv"), seller_profile)["grouping"] == {"mode": "row_per_line", "invoice_number_column": "Belegnr"}
    assert propose(load("lexware_like.csv"), seller_profile)["grouping"]["mode"] == "row_per_invoice"


def test_defaults_from_profile_when_no_vat_column(load, seller_profile):
    seller_profile["defaults"] = {"vat_rate": "7", "vat_category": "S", "unit": "HUR"}
    m = propose(load("no_vat_column.csv"), seller_profile)
    by = {f["target"]: f for f in m["fields"]}
    assert by["/lines/*/vat_rate"]["constant"] == "7"
    assert by["/lines/*/vat_category"]["constant"] == "S"
    assert by["/lines/*/unit"]["constant"] == "HUR"


def test_buyer_reference_left_unmapped_without_column(load, seller_profile):
    m = propose(load("lexware_like.csv"), seller_profile)
    assert "/buyer_reference" not in {f["target"] for f in m["fields"]}


def test_seller_and_iban_columns_never_mapped(csv_table, seller_profile):
    t = csv_table("Rechnungsnr;Datum;Kunde;Verkäufer;IBAN;Betrag\n"
                  "1;01.10.2026;A GmbH;Wir GmbH;DE89370400440532013000;10,00\n")
    m = propose(t, seller_profile)
    cols = {f.get("source_column") for f in m["fields"]}
    assert "IBAN" not in cols and "Verkäufer" not in cols


def test_value_patterns_rescue_unknown_headers(csv_table, seller_profile):
    t = csv_table("Rechnungsnr;Datum;Kunde;Kontakt1;Kontakt2;Menge;Preis\n"
                  "1;01.10.2026;A GmbH;a@x.example;DE111111111;1;10,00\n"
                  "2;02.10.2026;B GmbH;b@y.example;DE222222222;2;12,00\n")
    by = {f["target"]: f for f in propose(t, seller_profile)["fields"]}
    assert by["/buyer/electronic_address"]["source_column"] == "Kontakt1"
    assert by["/buyer/vat_id"]["source_column"] == "Kontakt2"


def test_mwst_header_disambiguated_by_values(csv_table, seller_profile):
    rate = csv_table("Nr;Datum;Netto;MwSt\n1;01.10.2026;100,00;19\n2;01.10.2026;50,00;7\n")
    amount = csv_table("Nr;Datum;Netto;MwSt\n1;01.10.2026;100,00;19,00\n2;01.10.2026;50,00;9,50\n3;01.10.2026;10,00;1,90\n")
    by_rate = {f["target"]: f for f in propose(rate, seller_profile)["fields"]}
    by_amount = {f["target"]: f for f in propose(amount, seller_profile)["fields"]}
    assert by_rate["/lines/*/vat_rate"].get("source_column") == "MwSt"
    assert by_amount["/source/expected_totals/vat"]["source_column"] == "MwSt"
    assert "constant" in by_amount["/lines/*/vat_rate"]


def test_credit_note_columns_get_abs(load, seller_profile):
    by = {f["target"]: f for f in propose(load("credit_notes.csv"), seller_profile)["fields"]}
    assert by["/lines/*/net_price"]["transform"] == ["de_decimal", "abs"]
    assert by["/lines/*/vat_rate"]["transform"] == ["de_decimal"]


def test_reasons_are_german(load, seller_profile):
    m = propose(load("sevdesk_like.csv"), seller_profile)
    by = {f["target"]: f for f in m["fields"]}
    assert "Spaltenname 'Invoice number' passt zu 'Rechnungsnummer'" in by["/number"]["reason_de"]
    assert "JJJJ-MM-TT" in by["/issue_date"]["reason_de"]
