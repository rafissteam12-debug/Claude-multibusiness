"""Implementations of the closed transform list (contracts/mapping.md) plus value parsers.

Every function takes a string and returns a string, or raises TransformError with a RowError
code and a German message fragment. `gross_to_net` needs the line's VAT rate and is applied
by `apply` after the rate is known (see `gross_to_net`).
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .targets import TRANSFORMS


class TransformError(ValueError):
    def __init__(self, code: str, message_de: str):
        super().__init__(message_de)
        self.code = code
        self.message_de = message_de


_CURRENCY_NOISE = re.compile(r"(?i)\s|€|eur|%| | ")
_DE_NUM = re.compile(r"^[+-]?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$")
_EN_NUM = re.compile(r"^[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")
_PLAIN_NUM = re.compile(r"^[+-]?\d+(\.\d+)?$")


def _clean_number(value: str) -> tuple[str, bool]:
    """Remove currency/percent signs and spaces; handle trailing minus and (123) accounting style."""
    v = _CURRENCY_NOISE.sub("", value.strip())
    negative = False
    if v.startswith("(") and v.endswith(")"):
        v, negative = v[1:-1], True
    if v.endswith("-") and len(v) > 1:
        v, negative = v[:-1], True
    if v.startswith("-"):
        v, negative = v[1:], not negative
    elif v.startswith("+"):
        v = v[1:]
    return v, negative


def _bad_number(value: str) -> TransformError:
    return TransformError("bad_number", f"'{value}' ist keine gültige Zahl")


def de_decimal(value: str) -> str:
    """'1.234,56' -> '1234.56'; also accepts '19 %', '12,50 €', '-3,00', '3,00-'."""
    v, neg = _clean_number(value)
    if not v or not _DE_NUM.match(v):
        # Tolerate an already-canonical value like '12.5' only when it cannot be a thousands group.
        if v and _PLAIN_NUM.match(v) and not re.match(r"^\d{1,3}\.\d{3}$", v):
            out = v
        else:
            raise _bad_number(value)
    else:
        out = v.replace(".", "").replace(",", ".")
    return ("-" if neg and not _is_zero(out) else "") + out


def en_decimal(value: str) -> str:
    """'1,234.56' -> '1234.56'."""
    v, neg = _clean_number(value)
    if not v or not _EN_NUM.match(v):
        raise _bad_number(value)
    out = v.replace(",", "")
    return ("-" if neg and not _is_zero(out) else "") + out


def _is_zero(v: str) -> bool:
    try:
        return Decimal(v) == 0
    except InvalidOperation:
        return False


def parse_decimal(value: str) -> Decimal:
    """Parse a canonical decimal ('-1234.56'). Used for values after (or without) a number transform."""
    v, neg = _clean_number(value)
    if not v or not _PLAIN_NUM.match(v):
        raise _bad_number(value)
    d = Decimal(v)
    return -d if neg else d


def format_decimal(d: Decimal, min_places: int = 0, max_places: int = 6) -> str:
    """Decimal -> plain string, no exponent, between min and max decimal places."""
    q = Decimal(1).scaleb(-max_places)
    d = d.quantize(q, rounding=ROUND_HALF_UP)
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if min_places:
        whole, _, frac = s.partition(".")
        s = whole + "." + frac.ljust(min_places, "0")
    if s.startswith("-") and Decimal(s) == 0:
        s = s[1:]
    return s


_DMY = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")


def _bad_date(value: str) -> TransformError:
    return TransformError("bad_date", f"'{value}' ist kein gültiges Datum")


def _make_date(y: int, m: int, d: int, value: str) -> str:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        raise _bad_date(value) from None


def _parse_dmy(v: str, value: str) -> str | None:
    m = _DMY.match(v)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    year = int(y) + 2000 if len(y) == 2 else int(y)
    return _make_date(year, mo, d, value)


def _parse_iso(v: str, value: str) -> str | None:
    m = _ISO.match(v)
    if not m:
        return None
    return _make_date(int(m.group(1)), int(m.group(2)), int(m.group(3)), value)


# date_dmy and date_iso each accept the other format as a fallback (review M6): exports often mix
# '2026-10-31' and '31.10.2026' in one column. The two patterns cannot overlap (4-digit year first
# vs. 1-2-digit day first), so the fallback never changes the meaning of a value.

def date_dmy(value: str) -> str:
    """'31.10.2026' (also '31.10.26', '31/10/2026', '31.10.2026 00:00:00') -> '2026-10-31'; ISO accepted too."""
    v = value.strip()
    out = _parse_dmy(v, value) or _parse_iso(v, value)
    if out is None:
        raise _bad_date(value)
    return out


def date_iso(value: str) -> str:
    """'2026-10-31' (optionally with a time part) -> '2026-10-31'; '31.10.2026' accepted too."""
    v = value.strip()
    out = _parse_iso(v, value) or _parse_dmy(v, value)
    if out is None:
        raise _bad_date(value)
    return out


def abs_(value: str) -> str:
    v = value.strip()
    return v[1:] if v.startswith("-") else v


ZERO_RATE_MESSAGE = ("0 % Umsatzsteuer: Bitte wählen Sie die Kategorie (z. B. steuerfrei, innergemeinschaftlich, "
                     "Kleinunternehmer) in der Zuordnung.")


def rate_to_category(value: str, default_category: str = "S") -> str:
    """'19' -> 'S'; '0' -> the seller's default category when that is not 'S' (e.g. E for Kleinunternehmer).

    With default 'S' a 0 % rate is NOT guessed (review M4): it may be Z, E, AE, K, G or O, each with
    different legal consequences. Raises TransformError('missing_exemption'); the user then maps
    `/lines/*/vat_category` explicitly (a category column or a constant).
    """
    v = value.strip()
    try:
        d = parse_decimal(v)
    except TransformError:
        try:
            d = parse_decimal(de_decimal(v))
        except TransformError:
            raise _bad_number(value) from None
    if d > 0:
        return "S"
    if default_category and default_category != "S":
        return default_category
    raise TransformError("missing_exemption", ZERO_RATE_MESSAGE)


# Document type words -> BT-3 code (compared after lower-casing and removing spaces, '-', '_', '.').
DOC_TYPE_CODES = {
    # 381 credit note
    "gutschrift": "381", "gs": "381", "storno": "381", "stornorechnung": "381", "rechnungsstorno": "381",
    "stornierung": "381", "rechnungskorrektur": "381", "korrekturrechnung": "381", "korrektur": "381",
    "creditnote": "381", "credit": "381", "refund": "381", "erstattung": "381", "381": "381",
    # 380 invoice
    "rechnung": "380", "re": "380", "ausgangsrechnung": "380", "invoice": "380", "commercialinvoice": "380",
    "abschlagsrechnung": "380", "teilrechnung": "380", "schlussrechnung": "380", "380": "380",
}


def _doc_key(value: str) -> str:
    return re.sub(r"[\s\-_.]+", "", value.strip().lower())


def doc_type(value: str) -> str:
    """'Gutschrift'/'Storno'/'Rechnungskorrektur'/'credit note' -> '381'; 'Rechnung'/'invoice' -> '380'."""
    code = DOC_TYPE_CODES.get(_doc_key(value))
    if code is None:
        raise TransformError("invalid_value", f"'{value}' ist keine erkannte Belegart (Rechnung oder Gutschrift)")
    return code


def is_doc_type(value: str) -> bool:
    return _doc_key(value) in DOC_TYPE_CODES


UNIT_CODES = {"C62", "HUR", "DAY", "KGM", "MTR", "LTR", "MTK", "SET", "MIN", "MON", "WEE", "ANN", "KMT", "TNE", "GRM", "MTQ", "LS", "H87", "XPP"}
UNIT_MAP = {
    # contract list
    "stk": "C62", "std": "HUR", "tag": "DAY", "kg": "KGM", "m": "MTR", "l": "LTR", "m2": "MTK", "pauschal": "C62",
    # common spellings
    "stück": "C62", "stueck": "C62", "st": "C62", "stk.": "C62", "st.": "C62", "pcs": "C62", "pc": "C62",
    "piece": "C62", "pieces": "C62", "ea": "C62", "each": "C62", "x": "C62", "psch": "C62", "psch.": "C62",
    "pausch.": "C62", "pauschale": "C62", "lump sum": "C62", "einheit": "C62", "unit": "C62", "units": "C62",
    "std.": "HUR", "stunde": "HUR", "stunden": "HUR", "h": "HUR", "hr": "HUR", "hrs": "HUR", "hour": "HUR", "hours": "HUR",
    "tage": "DAY", "tg": "DAY", "tg.": "DAY", "day": "DAY", "days": "DAY", "pt": "DAY", "personentag": "DAY",
    "kilogramm": "KGM", "kilogram": "KGM", "meter": "MTR", "lfm": "MTR", "liter": "LTR", "litre": "LTR", "ltr": "LTR",
    "m²": "MTK", "qm": "MTK", "quadratmeter": "MTK", "sqm": "MTK", "set": "SET", "satz": "SET",
    "min": "MIN", "minute": "MIN", "minuten": "MIN", "monat": "MON", "monate": "MON", "month": "MON", "mon": "MON",
    "woche": "WEE", "wochen": "WEE", "week": "WEE", "jahr": "ANN", "year": "ANN", "km": "KMT", "t": "TNE", "g": "GRM", "m³": "MTQ", "m3": "MTQ",
}


def unit_map(value: str) -> str:
    v = value.strip()
    if v.upper() in UNIT_CODES:
        return v.upper()
    code = UNIT_MAP.get(v.lower())
    if code is None:
        raise TransformError("unknown_unit", f"Einheit '{value}' ist unbekannt")
    return code


def strip(value: str) -> str:
    return value.strip()


def upper(value: str) -> str:
    return value.upper()


def gross_to_net(gross: str, vat_rate: str) -> str:
    """Gross unit price -> net unit price with the line's VAT rate (both canonical decimals)."""
    g = parse_decimal(gross)
    r = parse_decimal(vat_rate)
    net = g / (Decimal(1) + r / Decimal(100))
    return format_decimal(net, min_places=2, max_places=4)


SIMPLE = {
    "de_decimal": de_decimal,
    "en_decimal": en_decimal,
    "date_dmy": date_dmy,
    "date_iso": date_iso,
    "abs": abs_,
    "unit_map": unit_map,
    "strip": strip,
    "upper": upper,
    "doc_type": doc_type,
}

assert set(SIMPLE) | {"gross_to_net", "rate_to_category"} == set(TRANSFORMS)


def looks_like_number(value: str) -> str | None:
    """Return 'de', 'en', 'int' or None for one cell (used by the heuristic)."""
    v, _ = _clean_number(value)
    if not v:
        return None
    if re.match(r"^\d+$", v):
        return "int"
    de = bool(_DE_NUM.match(v))
    en = bool(_EN_NUM.match(v))
    if de and not en:
        return "de"
    if en and not de:
        return "en"
    if de and en:  # '1.234' or '1,234' style, ambiguous
        return "ambiguous"
    return None
