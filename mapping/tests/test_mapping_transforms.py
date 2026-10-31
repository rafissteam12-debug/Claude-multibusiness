from __future__ import annotations

import pytest

from mapping import value_shape
from mapping.transforms import (
    TransformError, date_dmy, date_iso, de_decimal, en_decimal, gross_to_net, rate_to_category, unit_map,
)


def test_value_shape_examples_from_contract():
    assert value_shape("Müller GmbH") == "Xxxxxx XxxX"
    assert value_shape("31.10.2026") == "dd.dd.dddd"
    assert value_shape("buchhaltung@kunde.example") == "xxxxxxxxxxx@xxxxx.xxxxxxx"
    assert value_shape("1.234,56 €") == "d.ddd,dd €"
    assert value_shape("") == ""


@pytest.mark.parametrize("raw,out", [
    ("1.234,56", "1234.56"), ("12,5", "12.5"), ("19 %", "19"), ("1.250,00 €", "1250.00"), ("-45,00", "-45.00"),
    ("45,00-", "-45.00"), ("1.000", "1000"), ("7", "7"), ("12.50", "12.50"), ("(3,00)", "-3.00"),
])
def test_de_decimal(raw, out):
    assert de_decimal(raw) == out


@pytest.mark.parametrize("raw,out", [("1,234.56", "1234.56"), ("1200.00", "1200.00"), ("-3.5", "-3.5"), ("19", "19")])
def test_en_decimal(raw, out):
    assert en_decimal(raw) == out


@pytest.mark.parametrize("bad", ["abc", "1,2,3", "", "12.34.56,7x"])
def test_bad_numbers(bad):
    with pytest.raises(TransformError) as exc:
        de_decimal(bad)
    assert exc.value.code == "bad_number"


def test_dates():
    assert date_dmy("31.10.2026") == "2026-10-31"
    assert date_dmy("1.2.26") == "2026-02-01"
    assert date_dmy("07.10.2026 00:00:00") == "2026-10-07"
    assert date_iso("2026-10-31") == "2026-10-31"
    assert date_iso("2026-10-31T12:00:00Z") == "2026-10-31"
    for bad in ("31.13.2026", "2026-02-30", "gestern"):
        with pytest.raises(TransformError) as exc:
            (date_iso if "-" in bad else date_dmy)(bad)
        assert exc.value.code == "bad_date"


def test_units():
    assert [unit_map(u) for u in ("Stk", "Std", "Tag", "kg", "m", "l", "m2", "Pauschal", "C62", "hours")] == \
        ["C62", "HUR", "DAY", "KGM", "MTR", "LTR", "MTK", "C62", "C62", "HUR"]
    with pytest.raises(TransformError) as exc:
        unit_map("Fass")
    assert exc.value.code == "unknown_unit"


def test_rate_to_category_and_gross_to_net():
    assert rate_to_category("19") == "S"
    assert rate_to_category("7,00") == "S"
    assert rate_to_category("0") == "Z"
    assert rate_to_category("0", default_category="E") == "E"
    assert gross_to_net("119.00", "19") == "100.00"
    assert gross_to_net("2.14", "7") == "2.00"
    assert gross_to_net("10.00", "19") == "8.4034"
