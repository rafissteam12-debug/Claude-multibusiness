"""Seller profile: validation against contracts/seller_profile.schema.json with German messages."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .settings import CONTRACTS_DIR

LABELS = {
    "/seller/name": "Firmenname",
    "/seller/street": "Straße und Hausnummer",
    "/seller/postcode": "PLZ",
    "/seller/city": "Ort",
    "/seller/country": "Land",
    "/seller/vat_id": "USt-IdNr.",
    "/seller/tax_number": "Steuernummer",
    "/seller/company_id": "Registernummer",
    "/seller/seller_id/id": "Verkäuferkennung",
    "/seller/seller_id/scheme": "Schema der Verkäuferkennung",
    "/seller/electronic_address": "Elektronische Adresse",
    "/seller/electronic_address_scheme": "Art der elektronischen Adresse",
    "/seller/contact": "Ansprechpartner",
    "/seller/contact/name": "Name des Ansprechpartners",
    "/seller/contact/phone": "Telefon des Ansprechpartners",
    "/seller/contact/email": "E-Mail des Ansprechpartners",
    "/payment_defaults": "Zahlungsangaben",
    "/payment_defaults/means_code": "Zahlungsart",
    "/payment_defaults/iban": "IBAN",
    "/payment_defaults/bic": "BIC",
    "/payment_defaults/account_name": "Kontoinhaber",
    "/payment_defaults/payment_days": "Zahlungsziel in Tagen",
    "/payment_defaults/terms": "Zahlungsbedingungen",
    "/defaults/vat_category": "Standard-Steuerkategorie",
    "/defaults/vat_rate": "Standard-Steuersatz",
    "/defaults/unit": "Standard-Einheit",
    "/defaults/profile": "Standard-Format",
    "/defaults/vat_exemptions": "Befreiungsgründe",
}
BR_CO_26 = ("Bitte geben Sie mindestens eine Kennung an: USt-IdNr., Registernummer (z. B. HRB) oder eine "
            "Verkäuferkennung. Eine Steuernummer allein reicht nicht (Regel BR-CO-26).")


@lru_cache(maxsize=1)
def validator() -> Draft202012Validator:
    inv = json.loads((CONTRACTS_DIR / "invoice.schema.json").read_text(encoding="utf-8"))
    prof = json.loads((CONTRACTS_DIR / "seller_profile.schema.json").read_text(encoding="utf-8"))
    res = Resource.from_contents(inv)
    registry = Registry().with_resources([(inv["$id"], res), ("invoice.schema.json", res)])
    return Draft202012Validator(prof, registry=registry, format_checker=FormatChecker())


def clean(value):
    """Drop empty strings, empty objects and None recursively (form fields left blank)."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            v = clean(v)
            if v is None or v == "" or v == {}:
                continue
            out[k] = v
        return out
    if isinstance(value, str):
        return value.strip()
    return value


def iban_ok(iban: str) -> bool:
    s = re.sub(r"\s+", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    num = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(num) % 97 == 1


def validate_profile(profile) -> list[dict]:
    """Return [{field, message_de}] (empty = valid). Messages never echo the values."""
    if not isinstance(profile, dict):
        return [{"field": "/", "message_de": "Das Profil muss ein Objekt sein."}]
    errors: list[dict] = []
    seen = set()

    def add(field, msg):
        if (field, msg) not in seen:
            seen.add((field, msg))
            errors.append({"field": field, "message_de": msg})

    for e in validator().iter_errors(profile):
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        if e.validator == "required":
            m = re.search(r"'([^']+)' is a required property", e.message)
            field = (path.rstrip("/") + "/" + m.group(1)) if m else path
            add(field, f"{LABELS.get(field, field)}: Angabe fehlt.")
        elif e.validator == "anyOf" and path == "/seller":
            add("/seller/vat_id", BR_CO_26)
        elif e.validator == "pattern" and path.endswith("/country"):
            add(path, "Land bitte als zweistelligen Code angeben, z. B. DE.")
        elif e.validator == "enum":
            add(path, f"{LABELS.get(path, path)}: Wert ist nicht zulässig.")
        elif e.validator in ("type", "minimum") and path.endswith("payment_days"):
            add(path, "Zahlungsziel bitte als ganze Zahl von Tagen (0 oder mehr) angeben.")
        elif e.validator == "additionalProperties":
            add(path or "/", "Das Profil enthält ein unbekanntes Feld.")
        elif e.validator == "minLength":
            add(path, f"{LABELS.get(path, path)}: Angabe fehlt.")
        elif e.validator == "anyOf" and "vat_exemptions" in path:
            add(path, "Befreiungsgrund: bitte Text oder Code (VATEX-…) angeben.")
        elif e.validator == "propertyNames":
            add("/defaults/vat_exemptions", "Befreiungsgründe gibt es nur für die Kategorien E, AE, K, G und O.")
        else:
            add(path, f"{LABELS.get(path, path)}: Angabe ist ungültig.")
    pay = profile.get("payment_defaults") if isinstance(profile.get("payment_defaults"), dict) else {}
    iban = pay.get("iban")
    if isinstance(iban, str) and iban and not iban_ok(iban):
        add("/payment_defaults/iban", "Die IBAN ist ungültig (Prüfziffer stimmt nicht).")
    if pay.get("means_code", "58") == "58" and not iban:
        add("/payment_defaults/iban", "Für SEPA-Überweisung (Zahlungsart 58) ist eine IBAN nötig.")
    defaults = profile.get("defaults") if isinstance(profile.get("defaults"), dict) else {}
    cat = defaults.get("vat_category")
    if cat in ("E", "AE", "K", "G", "O") and cat not in (defaults.get("vat_exemptions") or {}):
        add("/defaults/vat_exemptions", f"Für die Standard-Steuerkategorie {cat} ist ein Befreiungsgrund nötig "
                                        "(Regel BR-E-10 und verwandte Regeln).")
    return errors


def profile_hints(profile: dict) -> list[str]:
    """Non-blocking hints."""
    hints = []
    pay = profile.get("payment_defaults", {})
    if "payment_days" not in pay and "terms" not in pay:
        hints.append("Ohne Zahlungsziel oder Zahlungsbedingungen braucht jede Rechnung ein Fälligkeitsdatum in der Datei (Regel BR-CO-25).")
    if not profile.get("seller", {}).get("vat_id") and not profile.get("seller", {}).get("tax_number"):
        hints.append("Für XRechnung ist eine USt-IdNr. oder Steuernummer des Verkäufers üblich (Regel BR-DE-16 bei steuerpflichtigen Umsätzen).")
    return hints
