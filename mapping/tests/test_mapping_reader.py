from __future__ import annotations

import io
import re
from datetime import datetime

import openpyxl
import pytest

from contracts.types import Table
from mapping import TableReadError, read_table
from mapping.fixtures.make_fixtures import FIXTURES
from mapping.scoring import FIXTURES_DIR

EXPECTED = {
    # name: (encoding, delimiter, rows, first row number, first column)
    "lexware_like.csv": ("cp1252", ";", 5, 2, "Rechnungsnr."),
    "sevdesk_like.csv": ("utf-8-sig", ",", 4, 2, "Invoice number"),
    "excel_handmade.xlsx": ("utf-8", None, 3, 2, "Re-Nr"),
    "access_export.csv": ("utf-8", "\t", 4, 5, "RechNr"),
    "row_per_line.csv": ("utf-8", ";", 6, 2, "Belegnr"),
    "no_vat_column.csv": ("cp1252", ";", 3, 2, "Belegnummer"),
    "mixed_vat.csv": ("utf-8", ";", 6, 2, "Rechnungsnummer"),
    "credit_notes.csv": ("utf-8", ";", 4, 2, "Nr."),
}


@pytest.mark.parametrize("name", FIXTURES)
def test_read_all_fixtures(name, load):
    t = load(name)
    enc, delim, nrows, first, col0 = EXPECTED[name]
    assert isinstance(t, Table)
    assert (t.encoding, t.delimiter, len(t.rows), t.row_numbers[0], t.columns[0]) == (enc, delim, nrows, first, col0)
    assert len(t.row_numbers) == len(t.rows)
    assert all(isinstance(c, str) for row in t.rows for c in row)
    assert all(len(row) == len(t.columns) for row in t.rows)


def test_cp1252_umlauts(load):
    t = load("lexware_like.csv")
    assert "Straße" in t.columns
    assert t.rows[0][t.columns.index("Kunde")] == "Bäckerei Sonnenschein GmbH"
    assert t.rows[0][t.columns.index("Einzelpreis")] == "85,00"


def test_quoted_thousands_with_comma_delimiter(load):
    t = load("sevdesk_like.csv")
    assert t.rows[0][t.columns.index("Unit price net")] == "1,200.00"
    assert t.columns[0] == "Invoice number"  # BOM stripped


def test_access_title_rows_skipped_and_line_numbers(load):
    t = load("access_export.csv")
    assert t.columns[:3] == ["RechNr", "RechDatum", "KdName"]
    assert t.row_numbers == [5, 6, 7, 8]  # header is source line 4; trailing empty lines dropped


def test_xlsx_values(load):
    t = load("excel_handmade.xlsx")
    row = dict(zip(t.columns, t.rows[0]))
    assert t.sheet == "Rechnungen 2026"
    assert row["Datum"] == "01.10.2026"
    assert row["Re-Nr"] == "26041"
    assert row["Stunden"] == "7.5"
    assert row["MwSt"] == "19%"
    assert row["PLZ"] == "1067"  # leading zero lost by Excel; apply restores it for DE
    assert row["Gesamt brutto"] == "825.56"


def test_xlsx_float_noise_and_formula_values():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nr", "Betrag", "Datum"])
    ws.append(["1", 0.1 + 0.2, datetime(2026, 1, 2, 13, 45)])
    ws.append(["2", 1e-7, None])
    buf = io.BytesIO()
    wb.save(buf)
    t = read_table(buf.getvalue(), "x.xlsx")
    assert t.rows[0] == ["1", "0.3", "02.01.2026"]
    assert t.rows[1][1] == "0.0000001"
    assert t.rows[1][2] == ""


def test_utf8_without_bom_and_crlf_and_trailing_empty_rows():
    data = "Nr;Datum;Betrag\r\n1;01.10.2026;10,00\r\n2;02.10.2026;20,00\r\n;;\r\n\r\n".encode("utf-8")
    t = read_table(data, "a.csv")
    assert t.encoding == "utf-8" and t.delimiter == ";"
    assert t.rows == [["1", "01.10.2026", "10,00"], ["2", "02.10.2026", "20,00"]]
    assert t.row_numbers == [2, 3]


def test_multiline_quoted_cell_keeps_source_line_numbers():
    data = 'Nr,Text,Betrag\n1,"zwei\nZeilen",3\n2,eins,4\n'.encode()
    t = read_table(data, "a.csv")
    assert t.rows[0][1] == "zwei\nZeilen"
    assert t.row_numbers == [2, 4]


def test_tab_and_duplicate_and_empty_headers():
    data = "Nr\tBetrag\tBetrag\t\nA\t1\t2\tx\n".encode()
    t = read_table(data, "a.txt")
    assert t.delimiter == "\t"
    assert t.columns == ["Nr", "Betrag", "Betrag (2)", "Spalte 4"]


def test_old_xls_and_empty_file_rejected():
    with pytest.raises(TableReadError):
        read_table(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 100, "alt.xls")
    with pytest.raises(TableReadError):
        read_table(b"", "leer.csv")
    with pytest.raises(TableReadError):
        read_table(b"PK\x03\x04kaputt", "kaputt.xlsx")


def test_fixture_files_are_fictional():
    for name in FIXTURES:
        raw = (FIXTURES_DIR / name).read_bytes()
        if name.endswith(".xlsx"):
            t = read_table(raw, name)
            text = "\n".join(" ".join(r) for r in t.rows)
        else:
            text = raw.decode("utf-8", errors="replace")
        for token in re.split(r"[\s;,\"]+", text):
            if "@" in token:
                assert token.endswith((".example", ".invalid")), token
        ibans = re.findall(r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b", text)
        assert all(i == "DE89370400440532013000" for i in ibans)
