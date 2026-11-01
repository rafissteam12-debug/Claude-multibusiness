"""Input validation: invoice dict -> normalised dict, or InvoiceInputError.

Checks, in order:
1. JSON Schema `contracts/invoice.schema.json` with FormatChecker (dates).
2. Engine rules the schema cannot express: BT-10 for the XRechnung profile,
   IBAN checksum, credit-transfer account for XRechnung, exemption reason for
   every exempt category (E, AE, K, G, O) used in the lines, seller identifier
   (BT-29, BT-30 or BT-31; BR-CO-26).

Error messages are German and never contain invoice values (only field paths),
so they are safe to log and to store as error texts.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path

from contracts.types import InvoiceInputError, RowError

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "invoice.schema.json"
PROFILES = ("xrechnung", "zugferd")
EXEMPT_CATEGORIES = ("E", "AE", "K", "G", "O")

# Engine error codes in addition to the mapping codes of contracts/mapping.md
# (requested in docs/requests/engine.md): invalid_value, bad_iban,
# missing_exemption, forbidden_exemption.

_FIELD_NAMES_DE = {
    "number": "Rechnungsnummer (BT-1)",
    "issue_date": "Rechnungsdatum (BT-2)",
    "seller": "Verkäufer (BG-4)",
    "buyer": "Käufer (BG-7)",
    "lines": "Rechnungspositionen (BG-25)",
    "payment": "Zahlungsangaben (BG-16)",
    "contact": "Kontakt des Verkäufers (BG-6)",
    "name": "Name",
    "street": "Straße (BT-35/BT-50)",
    "postcode": "Postleitzahl (BT-38/BT-53)",
    "city": "Ort (BT-37/BT-52)",
    "country": "Land (BT-40/BT-55)",
    "electronic_address": "Elektronische Adresse (BT-34/BT-49)",
    "electronic_address_scheme": "Schema der elektronischen Adresse (BR-62/BR-63)",
    "phone": "Telefon (BT-42)",
    "email": "E-Mail (BT-43)",
    "description": "Bezeichnung (BT-153)",
    "quantity": "Menge (BT-129)",
    "net_price": "Nettopreis (BT-146)",
    "vat_category": "USt-Kategorie (BT-151)",
    "vat_rate": "USt-Satz (BT-152)",
    "iban": "IBAN (BT-84)",
    "seller_id": "Verkäuferkennung (BT-29)",
    "id": "Kennung",
    "scheme": "Schema der Kennung (ISO 6523 ICD)",
    "start": "Beginn",
    "end": "Ende",
}


def _pointer(parts) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _label(pointer: str) -> str:
    last = pointer.rsplit("/", 1)[-1]
    return _FIELD_NAMES_DE.get(last, pointer)


@lru_cache(maxsize=1)
def _validator():
    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema_errors(inv) -> list[RowError]:
    out: list[RowError] = []
    for e in sorted(_validator().iter_errors(inv), key=lambda e: list(map(str, e.absolute_path))):
        path = list(e.absolute_path)
        ptr = _pointer(path)
        v = e.validator
        if v == "required":
            missing = [p for p in e.validator_value if isinstance(e.instance, dict) and p not in e.instance]
            for p in missing or ["?"]:
                fp = _pointer(path + [p])
                out.append(RowError(0, None, fp, "missing_required", f"Pflichtangabe fehlt: {_label(fp)}."))
        elif v == "anyOf" and ptr == "/payment":
            out.append(RowError(0, None, "/payment/due_date", "missing_required",
                                "Fälligkeitsdatum (BT-9) oder Zahlungsbedingungen (BT-20) angeben (BR-CO-25)."))
        elif v == "anyOf" and ptr == "/seller":
            out.append(RowError(0, None, "/seller/vat_id", "missing_required",
                                "Verkäufer braucht eine USt-IdNr. (BT-31), eine Registernummer (BT-30, z. B. HRB) "
                                "oder eine Verkäuferkennung (BT-29); die Steuernummer (BT-32) allein reicht nach "
                                "EN 16931 nicht (BR-CO-26)."))
        elif v == "anyOf" and ptr.startswith("/vat_exemptions/"):
            out.append(RowError(0, None, ptr, "missing_exemption",
                                "Befreiungsgrund braucht einen Text (BT-120) oder einen Code VATEX-… (BT-121)."))
        elif v == "propertyNames" or "propertyNames" in e.schema_path:
            fp = _pointer(path + [e.instance]) if isinstance(e.instance, str) else ptr
            out.append(RowError(0, None, fp, "forbidden_exemption",
                                "Für diese USt-Kategorie ist kein Befreiungsgrund erlaubt "
                                "(nur E, AE, K, G, O; nie S oder Z, BR-Z-10)."))
        elif v == "format" and e.validator_value == "date":
            out.append(RowError(0, None, ptr, "bad_date", f"Ungültiges Datum in {_label(ptr)} (erwartet JJJJ-MM-TT)."))
        elif v == "pattern" and ptr.split("/")[-1] in ("quantity", "net_price", "vat_rate", "net", "vat", "gross"):
            out.append(RowError(0, None, ptr, "bad_number",
                                f"Ungültiger Betrag in {_label(ptr)} (erwartet z. B. 1234.56 als Text, nicht negativ)."))
        elif v in ("minItems", "minLength"):
            out.append(RowError(0, None, ptr, "missing_required", f"Pflichtangabe fehlt oder ist leer: {_label(ptr)}."))
        elif v == "additionalProperties":
            extra = [k for k in e.instance if k not in (e.schema.get("properties") or {})] if isinstance(e.instance, dict) else []
            for k in extra or ["?"]:
                out.append(RowError(0, None, _pointer(path + [k]), "invalid_value", "Unbekanntes Feld."))
        elif v == "type":
            out.append(RowError(0, None, ptr, "invalid_value", f"Falscher Datentyp in {_label(ptr)} (erwartet: {e.validator_value})."))
        else:
            out.append(RowError(0, None, ptr, "invalid_value", f"Unzulässiger Wert in {_label(ptr)}."))
    return out


def iban_ok(iban: str) -> bool:
    s = iban.replace(" ", "").upper()
    if not (15 <= len(s) <= 34) or not s[:2].isalpha() or not s[2:4].isdigit() or not s.isalnum():
        return False
    if s[:2] == "DE" and len(s) != 22:
        return False
    digits = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(digits) % 97 == 1


def normalise(inv: dict) -> dict:
    """Apply schema defaults. Input must already be schema-valid."""
    inv = copy.deepcopy(inv)
    inv.setdefault("type_code", "380")
    inv.setdefault("currency", "EUR")
    inv["payment"].setdefault("means_code", "58")
    for line in inv["lines"]:
        line.setdefault("unit", "C62")
    return inv


def check_invoice(inv, profile: str = "xrechnung") -> dict:
    """Validate the invoice; return a normalised copy or raise InvoiceInputError."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; expected one of {PROFILES}")
    if not isinstance(inv, dict):
        raise InvoiceInputError([RowError(0, None, "", "invalid_value", "Rechnung muss ein JSON-Objekt sein.")])
    errors = _schema_errors(inv)
    if errors:
        raise InvoiceInputError(errors)
    inv = normalise(inv)

    if profile == "xrechnung" and not inv.get("buyer_reference"):
        errors.append(RowError(0, None, "/buyer_reference", "missing_required",
                               "Käuferreferenz bzw. Leitweg-ID (BT-10) ist für XRechnung Pflicht (BR-DE-15)."))
    seller = inv["seller"]
    if not seller.get("vat_id") and not seller.get("company_id") and not (seller.get("seller_id") or {}).get("id"):
        # BR-CO-26 needs BT-29, BT-30 or BT-31; a tax number (BT-32) alone is not enough. (Normally caught by the
        # schema's anyOf already; kept as a guard for empty values.)
        errors.append(RowError(0, None, "/seller/seller_id", "missing_required",
                               "Ohne USt-IdNr. (BT-31) braucht der Verkäufer eine Registernummer (BT-30, z. B. HRB) "
                               "oder eine Verkäuferkennung (BT-29); die Steuernummer allein reicht nach EN 16931 "
                               "nicht (BR-CO-26)."))
    pay = inv["payment"]
    if pay.get("iban") and not iban_ok(pay["iban"]):
        errors.append(RowError(0, None, "/payment/iban", "bad_iban",
                               "IBAN (BT-84) ist ungültig (Prüfsumme oder Länge falsch, BR-DE-19)."))
    if profile == "xrechnung" and not pay.get("iban"):
        errors.append(RowError(0, None, "/payment/iban", "missing_required",
                               "Für Überweisung braucht XRechnung ein Konto (BG-17, BR-DE-23-a): IBAN angeben."))
    used = {line["vat_category"] for line in inv["lines"]}
    exemptions = inv.get("vat_exemptions") or {}
    for cat in EXEMPT_CATEGORIES:
        if cat in used and cat not in exemptions:
            rule = {"E": "BR-E-10", "AE": "BR-AE-10", "K": "BR-IC-10", "G": "BR-G-10", "O": "BR-O-10"}[cat]
            errors.append(RowError(0, None, f"/vat_exemptions/{cat}", "missing_exemption",
                                   f"Für USt-Kategorie {cat} ist ein Befreiungsgrund (BT-120 oder BT-121) Pflicht ({rule})."))
    if inv["type_code"] == "381" and not inv.get("preceding_invoice"):
        pass  # BG-3 is expected for credit notes but not mandatory in EN 16931; the validator decides.
    if errors:
        raise InvoiceInputError(errors)
    return inv
