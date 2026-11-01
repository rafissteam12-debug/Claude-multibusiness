"""Resource limits of read_table (review H1): zip bombs, row and column caps."""
from __future__ import annotations

import io
import time
import zipfile

import openpyxl
import pytest

from mapping import TableReadError, read_table
from mapping import reader


def _xlsx(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _no_openpyxl(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("openpyxl must not be called for a rejected zip")
    monkeypatch.setattr(openpyxl, "load_workbook", boom)


def test_zip_bomb_rejected_before_openpyxl(monkeypatch):
    # ~2 MiB of zeros compresses to a few KB: ratio far above 100. Built here, never committed.
    good = _xlsx([["Rechnungsnr", "Betrag"], ["RE-1", "10,00"]])
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(good)) as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith("sheet1.xml"):
                data = data + b" " * (2 * 1024 * 1024)
            dst.writestr(info.filename, data)
    bomb = buf.getvalue()
    assert len(bomb) < 200_000
    _no_openpyxl(monkeypatch)
    t0 = time.monotonic()
    with pytest.raises(TableReadError) as exc:
        read_table(bomb, "bombe.xlsx")
    assert time.monotonic() - t0 < 2
    assert "zu groß" in exc.value.message_de


def test_zip_total_size_and_member_count(monkeypatch):
    good = _xlsx([["Rechnungsnr", "Betrag"], ["RE-1", "10,00"]])
    monkeypatch.setattr(reader, "MAX_XLSX_UNCOMPRESSED", 1000)
    with pytest.raises(TableReadError):
        read_table(good, "a.xlsx")
    monkeypatch.undo()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(reader.MAX_XLSX_MEMBERS + 1):
            zf.writestr(f"x/{i}.xml", b"<a/>")
    _no_openpyxl(monkeypatch)
    with pytest.raises(TableReadError):
        read_table(buf.getvalue(), "viele.xlsx")


def test_broken_zip_is_table_read_error():
    with pytest.raises(TableReadError):
        read_table(b"PK\x03\x04kaputt", "x.xlsx")


def test_csv_row_cap_and_exact_limit():
    header = "Rechnungsnr;Betrag\n"
    ok = header + "".join(f"RE-{i};1,00\n" for i in range(reader.MAX_ROWS))
    assert len(read_table(ok.encode(), "ok.csv").rows) == reader.MAX_ROWS
    too_many = ok + "RE-X;1,00\n"
    with pytest.raises(TableReadError) as exc:
        read_table(too_many.encode(), "gross.csv")
    assert exc.value.message_de.startswith("Die Datei ist zu groß: höchstens 20 000 Zeilen")


def test_csv_stops_reading_early(monkeypatch):
    monkeypatch.setattr(reader, "MAX_ROWS", 10)
    seen = []
    real = reader._check_width

    def counting(rec):
        seen.append(1)
        return real(rec)
    monkeypatch.setattr(reader, "_check_width", counting)
    text = "A;B\n" + "x;1\n" * 5000
    with pytest.raises(TableReadError):
        read_table(text.encode(), "a.csv")
    # sniffing reads 200 lines; the real parse must stop right after the cap
    assert len(seen) < 200 * 4 + 10 + reader.MAX_HEADER_SCAN + 5


def test_xlsx_row_cap(monkeypatch):
    monkeypatch.setattr(reader, "MAX_ROWS", 30)
    data = _xlsx([["Rechnungsnr", "Betrag"]] + [[f"RE-{i}", 1] for i in range(80)])
    with pytest.raises(TableReadError) as exc:
        read_table(data, "a.xlsx")
    assert "höchstens" in exc.value.message_de
    data = _xlsx([["Rechnungsnr", "Betrag"]] + [[f"RE-{i}", 1] for i in range(30)])
    assert len(read_table(data, "a.xlsx").rows) == 30


def test_column_cap_csv_and_xlsx():
    wide = ";".join(f"S{i}" for i in range(reader.MAX_COLUMNS + 1))
    with pytest.raises(TableReadError) as exc:
        read_table((wide + "\n" + wide + "\n").encode(), "breit.csv")
    assert "Spalten" in exc.value.message_de
    # empty trailing cells beyond the cap are fine
    t = read_table(("A;B" + ";" * 300 + "\nx;1\n").encode(), "a.csv")
    assert t.columns == ["A", "B"]
    with pytest.raises(TableReadError):
        read_table(_xlsx([[f"S{i}" for i in range(reader.MAX_COLUMNS + 1)], ["x"] * (reader.MAX_COLUMNS + 1)]), "b.xlsx")


def test_xlsx_with_formatted_empty_rows_and_gaps():
    data = _xlsx([["Rechnungsnr", "Betrag"], ["RE-1", 1], [], [], ["RE-2", 2]])
    t = read_table(data, "a.xlsx")
    assert [r[0] for r in t.rows] == ["RE-1", "RE-2"]
    assert t.row_numbers == [2, 5]


def test_input_size_limit():
    with pytest.raises(TableReadError):
        read_table(b"A;B\n" + b"x" * (reader.MAX_INPUT_BYTES + 1), "a.csv")
