"""Mappable targets (JSON Pointers into contracts/invoice.schema.json) and the closed transform list.

One place for both, so the heuristic, the AI provider's response validation and `apply`
agree. Seller fields and the seller's payment account are deliberately absent: they always
come from the seller profile (contracts/mapping.md).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"
INVOICE_SCHEMA_PATH = CONTRACTS_DIR / "invoice.schema.json"
SELLER_PROFILE_SCHEMA_PATH = CONTRACTS_DIR / "seller_profile.schema.json"

# Closed list from contracts/mapping.md. Nothing else is accepted in a Mapping.
TRANSFORMS: tuple[str, ...] = (
    "de_decimal", "en_decimal", "date_dmy", "date_iso", "abs",
    "gross_to_net", "rate_to_category", "unit_map", "strip", "upper",
)

# Header-level targets (one value per invoice).
HEADER_TARGETS: tuple[str, ...] = (
    "/number",
    "/issue_date",
    "/delivery_date",
    "/period/start",
    "/period/end",
    "/currency",
    "/buyer_reference",
    "/order_reference",
    "/note",
    "/buyer/name",
    "/buyer/street",
    "/buyer/postcode",
    "/buyer/city",
    "/buyer/country",
    "/buyer/vat_id",
    "/buyer/electronic_address",
    "/buyer/electronic_address_scheme",
    "/buyer/company_id",
    "/payment/due_date",
    "/payment/terms",
    "/preceding_invoice/number",
    "/preceding_invoice/issue_date",
    "/source/expected_totals/net",
    "/source/expected_totals/vat",
    "/source/expected_totals/gross",
)

# Line-level targets (`*` = every line of the invoice).
LINE_TARGETS: tuple[str, ...] = (
    "/lines/*/id",
    "/lines/*/description",
    "/lines/*/quantity",
    "/lines/*/unit",
    "/lines/*/net_price",
    "/lines/*/vat_category",
    "/lines/*/vat_rate",
)

ALLOWED_TARGETS: frozenset[str] = frozenset(HEADER_TARGETS + LINE_TARGETS)

# Targets whose values are money/decimal strings (schema $defs/money).
MONEY_TARGETS = frozenset({
    "/lines/*/quantity", "/lines/*/net_price", "/lines/*/vat_rate",
    "/source/expected_totals/net", "/source/expected_totals/vat", "/source/expected_totals/gross",
})
DATE_TARGETS = frozenset({
    "/issue_date", "/delivery_date", "/period/start", "/period/end",
    "/payment/due_date", "/preceding_invoice/issue_date",
})
# Amount fields whose sign decides invoice (380) vs credit note (381).
SIGNED_LINE_TARGETS = frozenset({"/lines/*/quantity", "/lines/*/net_price"})

# Fields that must be filled for a schema-valid invoice (used for scoring and RowErrors).
REQUIRED_TARGETS: tuple[str, ...] = (
    "/number",
    "/issue_date",
    "/buyer/name",
    "/buyer/street",
    "/buyer/postcode",
    "/buyer/city",
    "/buyer/country",
    "/buyer/electronic_address",
    "/buyer/electronic_address_scheme",
    "/lines/*/description",
    "/lines/*/quantity",
    "/lines/*/net_price",
    "/lines/*/vat_category",
    "/lines/*/vat_rate",
)

GERMAN_LABELS: dict[str, str] = {
    "/number": "Rechnungsnummer",
    "/issue_date": "Rechnungsdatum",
    "/delivery_date": "Leistungsdatum",
    "/period/start": "Leistungszeitraum (Beginn)",
    "/period/end": "Leistungszeitraum (Ende)",
    "/currency": "Währung",
    "/buyer_reference": "Käuferreferenz / Leitweg-ID",
    "/order_reference": "Bestellnummer",
    "/note": "Bemerkung",
    "/buyer/name": "Name des Kunden",
    "/buyer/street": "Straße des Kunden",
    "/buyer/postcode": "PLZ des Kunden",
    "/buyer/city": "Ort des Kunden",
    "/buyer/country": "Land des Kunden",
    "/buyer/vat_id": "USt-IdNr. des Kunden",
    "/buyer/electronic_address": "E-Mail-Adresse des Kunden",
    "/buyer/electronic_address_scheme": "Art der elektronischen Adresse",
    "/buyer/company_id": "Registernummer des Kunden",
    "/payment/due_date": "Fälligkeitsdatum",
    "/payment/terms": "Zahlungsbedingungen",
    "/payment/iban": "IBAN",
    "/preceding_invoice/number": "Nummer der Ursprungsrechnung",
    "/preceding_invoice/issue_date": "Datum der Ursprungsrechnung",
    "/source/expected_totals/net": "Nettosumme laut Quelle",
    "/source/expected_totals/vat": "Steuerbetrag laut Quelle",
    "/source/expected_totals/gross": "Bruttosumme laut Quelle",
    "/lines/*/id": "Positionsnummer",
    "/lines/*/description": "Positionsbeschreibung",
    "/lines/*/quantity": "Menge",
    "/lines/*/unit": "Einheit",
    "/lines/*/net_price": "Einzelpreis netto",
    "/lines/*/vat_category": "Steuerkategorie",
    "/lines/*/vat_rate": "Steuersatz",
}


def is_line_target(target: str) -> bool:
    return target.startswith("/lines/*/")


@lru_cache(maxsize=1)
def invoice_schema() -> dict:
    return json.loads(INVOICE_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def seller_profile_schema() -> dict:
    return json.loads(SELLER_PROFILE_SCHEMA_PATH.read_text(encoding="utf-8"))


def pointer_exists_in_schema(target: str) -> bool:
    """True if the JSON Pointer (with `*` for array items) resolves to a property in the invoice schema."""
    schema = invoice_schema()
    defs = schema.get("$defs", {})

    def resolve(node: dict) -> dict:
        seen = 0
        while "$ref" in node and seen < 10:
            node = defs[node["$ref"].split("/")[-1]]
            seen += 1
        if "allOf" in node:  # party_seller
            merged: dict = {"properties": {}}
            for part in node["allOf"]:
                part = resolve(part)
                merged["properties"].update(part.get("properties", {}))
            return merged
        return node

    node = schema
    for part in target.strip("/").split("/"):
        node = resolve(node)
        if part == "*":
            if node.get("type") != "array":
                return False
            node = node["items"]
            continue
        props = node.get("properties", {})
        if part not in props:
            return False
        node = props[part]
    return True
