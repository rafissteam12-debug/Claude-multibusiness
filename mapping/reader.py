"""read_table: CSV/XLSX bytes -> contracts.types.Table (all cells strings, 1-based row numbers)."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date, datetime, time
from decimal import Decimal

from contracts.types import Table


class TableReadError(ValueError):
    """The file cannot be read as a table. `message_de` is safe to show (contains no cell values)."""

    def __init__(self, message_de: str):
        super().__init__(message_de)
        self.message_de = message_de


DELIMITERS = (";", ",", "\t", "|")
MAX_HEADER_SCAN = 25

# ---- resource limits (review H1). Checked while reading, so a hostile file is rejected early.
MAX_INPUT_BYTES = 10 * 1024 * 1024        # upload limit (contracts/api.md); also bounds decoded CSV text
MAX_ROWS = 20_000                         # data rows (non-empty) per table
MAX_COLUMNS = 200                         # columns with any content
MAX_XLSX_UNCOMPRESSED = 50 * 1024 * 1024  # sum of declared member sizes in the XLSX zip
MAX_XLSX_RATIO = 100                      # max compression ratio of one zip member ...
XLSX_RATIO_MIN_SIZE = 1024 * 1024         # ... checked for members larger than 1 MiB (tiny XML parts compress well)
MAX_XLSX_MEMBERS = 1000
MAX_EMPTY_RUN = 1000                      # stop reading an XLSX sheet after this many empty rows in a row

_MSG_TOO_BIG = "Die Datei ist zu groß: höchstens 10 MB."
_MSG_ROWS = (f"Die Datei ist zu groß: höchstens {MAX_ROWS:,} Zeilen je Datei. ".replace(",", " ")
             + "Bitte teilen Sie die Datei auf (z. B. nach Monaten).")
_MSG_COLS = f"Die Datei hat zu viele Spalten: höchstens {MAX_COLUMNS}. Bitte entfernen Sie nicht benötigte Spalten."
_MSG_ZIP = ("Die Excel-Datei ist entpackt zu groß oder ungewöhnlich aufgebaut "
            "(höchstens 50 MB entpackt). Bitte speichern Sie sie als CSV oder teilen Sie sie auf.")


def _check_width(rec: list[str]) -> list[str]:
    """Reject records with content beyond MAX_COLUMNS; cut empty trailing cells."""
    if len(rec) <= MAX_COLUMNS:
        return rec
    if any(c.strip() for c in rec[MAX_COLUMNS:]):
        raise TableReadError(_MSG_COLS)
    return rec[:MAX_COLUMNS]


def _row_limit() -> int:
    # records kept while reading: data rows plus a possible title block and the header row
    return MAX_ROWS + MAX_HEADER_SCAN + 1


# ---------------------------------------------------------------- decoding

def _decode(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        # cp1252 leaves 5 bytes undefined; latin-1 never fails.
        return data.decode("latin-1"), "latin-1"


# ---------------------------------------------------------------- CSV

def _parse_csv(text: str, delimiter: str) -> list[tuple[int, list[str]]]:
    """Records with the 1-based source line number where each record starts."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, quotechar='"')
    out: list[tuple[int, list[str]]] = []
    prev = 0
    filled = 0
    limit = _row_limit()
    try:
        for rec in reader:
            rec = _check_width(rec)
            if any(c.strip() for c in rec):
                filled += 1
                if filled > limit:
                    raise TableReadError(_MSG_ROWS)
            out.append((prev + 1, rec))
            prev = reader.line_num
    except csv.Error as exc:  # e.g. NUL byte, unterminated quote
        raise TableReadError("Die CSV-Datei konnte nicht gelesen werden (fehlerhafte Anführungszeichen oder Steuerzeichen).") from exc
    return out


def _delimiter_score(records: list[tuple[int, list[str]]]) -> tuple[int, int]:
    counts: dict[int, int] = {}
    for _, rec in records[:200]:
        if not any(c.strip() for c in rec):
            continue
        counts[len(rec)] = counts.get(len(rec), 0) + 1
    best = (0, 0)
    for width, n in counts.items():
        if width > 1 and (n, width) > best:
            best = (n, width)
    return best


def _sniff_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:200])
    scored = []
    for d in DELIMITERS:
        try:
            recs = _parse_csv(sample, d)
        except TableReadError:
            continue
        n, width = _delimiter_score(recs)
        scored.append(((n, width), d))
    scored.sort(key=lambda s: s[0], reverse=True)
    if not scored or scored[0][0][0] == 0:
        return ";"  # single column file; any delimiter gives the same result
    return scored[0][1]


# ---------------------------------------------------------------- XLSX

def _number_to_str(v: int | float) -> str:
    if isinstance(v, bool):
        return "WAHR" if v else "FALSCH"
    if isinstance(v, int):
        return str(v)
    if v != v or v in (float("inf"), float("-inf")):
        return ""
    if float(v).is_integer():
        return str(int(v))
    d = Decimal(f"{v:.15g}")  # Excel keeps 15 significant digits; drops float noise
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _cell_to_str(value, number_format: str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (int, float)):
        if number_format and "%" in number_format and not isinstance(value, bool):
            return _number_to_str(float(Decimal(f"{value:.15g}") * 100)) + "%"
        return _number_to_str(value)
    return str(value)


def _check_zip(data: bytes) -> None:
    """Reject zip bombs before openpyxl decompresses anything.

    zipfile never yields more than a member's declared `file_size`, so checking the declared
    sizes bounds the real decompression.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
    except (zipfile.BadZipFile, ValueError, OSError) as exc:
        raise TableReadError("Die Excel-Datei konnte nicht geöffnet werden (beschädigt oder kein .xlsx).") from exc
    if len(infos) > MAX_XLSX_MEMBERS:
        raise TableReadError(_MSG_ZIP)
    total = 0
    for info in infos:
        total += info.file_size
        if total > MAX_XLSX_UNCOMPRESSED:
            raise TableReadError(_MSG_ZIP)
        if info.file_size > XLSX_RATIO_MIN_SIZE and info.file_size > MAX_XLSX_RATIO * max(info.compress_size, 1):
            raise TableReadError(_MSG_ZIP)


def _read_xlsx(data: bytes) -> tuple[list[tuple[int, list[str]]], str]:
    _check_zip(data)
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise TableReadError("Excel-Dateien können derzeit nicht gelesen werden.") from exc
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise TableReadError("Die Excel-Datei konnte nicht geöffnet werden (beschädigt oder kein .xlsx).") from exc
    try:
        if not wb.worksheets:
            raise TableReadError("Die Excel-Datei enthält kein Tabellenblatt.")
        ws = wb.worksheets[0]
        if hasattr(ws, "reset_dimensions"):
            # read-only sheets pad every row to the declared dimension (up to XFD); read cells as stored
            ws.reset_dimensions()
        records: list[tuple[int, list[str]]] = []
        filled = 0
        empty_run = 0
        limit = _row_limit()
        last_row = 0
        for row in ws.iter_rows():
            cells = []
            rownum = None
            for i, cell in enumerate(row):
                if rownum is None and getattr(cell, "row", None):
                    rownum = cell.row
                if i >= MAX_COLUMNS:
                    if cell.value not in (None, ""):
                        raise TableReadError(_MSG_COLS)
                    continue
                cells.append(_cell_to_str(cell.value, getattr(cell, "number_format", None)))
            if rownum is None:
                rownum = last_row + 1
            last_row = rownum
            if not any(c.strip() for c in cells):
                empty_run += 1
                if empty_run >= MAX_EMPTY_RUN:
                    break
                continue
            empty_run = 0
            filled += 1
            if filled > limit:
                raise TableReadError(_MSG_ROWS)
            records.append((rownum, cells))
        return records, ws.title
    finally:
        wb.close()


# ---------------------------------------------------------------- header detection

_NUMERICISH = re.compile(r"^[\s+-]?[\d.,]+\s*(%|€|EUR)?$|^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}")


def _is_texty(cell: str) -> bool:
    c = cell.strip()
    return bool(c) and not _NUMERICISH.match(c) and "@" not in c


def _find_header(records: list[tuple[int, list[str]]]) -> int:
    widths = [sum(1 for c in rec if c.strip()) for _, rec in records[: MAX_HEADER_SCAN + 20]]
    if not widths:
        return 0
    max_width = max(widths)
    for i, (_, rec) in enumerate(records[:MAX_HEADER_SCAN]):
        filled = [c for c in rec if c.strip()]
        if len(filled) < max(2, int(max_width * 0.6)):
            continue
        texty = sum(1 for c in filled if _is_texty(c))
        if texty / len(filled) < 0.7:
            continue
        if len(set(c.strip().lower() for c in filled)) < len(filled) * 0.8:
            continue
        return i
    return 0


def _make_columns(header: list[str]) -> list[str]:
    cols: list[str] = []
    seen: dict[str, int] = {}
    for i, h in enumerate(header):
        name = " ".join(h.split()) or f"Spalte {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        cols.append(name)
    return cols


def _build_table(records: list[tuple[int, list[str]]], encoding: str, delimiter: str | None, sheet: str | None) -> Table:
    if not records or not any(any(c.strip() for c in rec) for _, rec in records):
        raise TableReadError("Die Datei enthält keine Daten.")
    h = _find_header(records)
    if sum(1 for _, rec in records[h + 1:] if any(c.strip() for c in rec)) > MAX_ROWS:
        raise TableReadError(_MSG_ROWS)
    header = list(records[h][1])
    body = records[h + 1:]
    width = max([len(header)] + [len(rec) for _, rec in body])
    header += [""] * (width - len(header))
    rows: list[list[str]] = []
    row_numbers: list[int] = []
    for num, rec in body:
        rec = list(rec) + [""] * (width - len(rec))
        if not any(c.strip() for c in rec):
            continue  # empty rows (also trailing) are skipped; numbering keeps source lines
        rows.append(rec)
        row_numbers.append(num)
    # drop trailing columns that have neither header nor data
    keep = width
    while keep > 0 and not header[keep - 1].strip() and all(not r[keep - 1].strip() for r in rows):
        keep -= 1
    header = header[:keep]
    rows = [r[:keep] for r in rows]
    if len([c for c in header if c.strip()]) < 2:
        raise TableReadError("Keine Kopfzeile mit mindestens zwei Spalten gefunden.")
    return Table(columns=_make_columns(header), rows=rows, row_numbers=row_numbers,
                 encoding=encoding, delimiter=delimiter, sheet=sheet)


# ---------------------------------------------------------------- public

def read_table(data: bytes, filename: str) -> Table:
    """Read a CSV or XLSX export. All cells are returned as strings."""
    name = (filename or "").lower()
    if len(data) > MAX_INPUT_BYTES:
        raise TableReadError(_MSG_TOO_BIG)
    if data[:4] == b"PK\x03\x04" or name.endswith((".xlsx", ".xlsm")):
        records, sheet = _read_xlsx(data)
        return _build_table(records, encoding="utf-8", delimiter=None, sheet=sheet)
    if name.endswith(".xls") or data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise TableReadError("Das alte Excel-Format .xls wird nicht unterstützt. Bitte als .xlsx oder CSV speichern.")
    text, encoding = _decode(data)
    text = text.replace("\x00", "")
    delimiter = _sniff_delimiter(text)
    records = _parse_csv(text, delimiter)
    return _build_table(records, encoding=encoding, delimiter=delimiter, sheet=None)
