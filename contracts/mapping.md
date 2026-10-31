# Mapping, error and report contracts v1

Python types live in `contracts/types.py` (dataclasses, no logic). Every agent imports
them from there; nobody redefines them.

## Table (mapping -> app)
`Table(columns: list[str], rows: list[list[str]], row_numbers: list[int], encoding: str, delimiter: str|None, sheet: str|None)`
All cells are raw strings exactly as read (no type conversion). `row_numbers` are 1-based
source line numbers for error messages.

## Mapping (mapping <-> app; stored for reuse)
```json
{
  "mapping_id": "uuid",
  "version": 1,
  "grouping": {"mode": "row_per_invoice" | "row_per_line", "invoice_number_column": "Rechnungsnr."},
  "fields": [
    {"target": "/number", "source_column": "Rechnungsnr.", "transform": [], "confidence": 0.97, "reason_de": "Spaltenname enthält 'Rechnung' und 'Nr'"},
    {"target": "/lines/*/net_price", "source_column": "Einzelpreis", "transform": ["de_decimal"], "confidence": 0.9, "reason_de": "..."},
    {"target": "/buyer/electronic_address_scheme", "constant": "EM", "confidence": 1.0, "reason_de": "Standard: E-Mail"}
  ]
}
```
- `target`: JSON Pointer into `invoice.schema.json`; `*` = every line of the invoice.
- Exactly one of `source_column` or `constant`.
- `transform` (applied in order), closed list: `de_decimal` ("1.234,56" -> "1234.56"), `en_decimal`,
  `date_dmy` ("31.10.2026"), `date_iso`, `abs` (credit-note rows), `gross_to_net` (needs the line's vat_rate),
  `rate_to_category` ("19"->S, "0"->user default), `unit_map` (Stk->C62, Std->HUR, Tag->DAY, kg->KGM, m->MTR, l->LTR, m2->MTK, Pauschal->C62),
  `strip`, `upper`.
- Seller fields are NEVER mapped: they come from the seller profile.
- Saved mappings store column names, constants and transforms only — never cell values.

## RowError (mapping -> app -> UI)
`RowError(row: int, column: str|None, field: str (JSON Pointer), code: str, message_de: str)`
Codes: `missing_required`, `bad_number`, `bad_date`, `unknown_unit`, `inconsistent_invoice` (line rows disagree on header fields), `negative_amount`, `buyer_address_missing`.

## Report (engine -> app -> UI and /check)
```json
{"valid": true, "profile": "xrechnung" | "zugferd" | "unknown",
 "layers": [{"name": "XSD" | "EN16931" | "XRechnung" | "KoSIT", "ran": true, "skipped_reason": null,
             "errors": [{"id": "BR-DE-15", "message_de": "...", "text_en": "...", "location": "/xpath"}],
             "warnings": [...]}],
 "totals_warning": null | {"expected": {...}, "computed": {...}}}
```
**Validity rule:** `valid` = XSD, EN16931 and XRechnung layers ran with zero errors (XRechnung layer only for the
XRechnung profile) AND, when `APP_ENV` is `staging` or `prod`, the KoSIT layer ran with zero errors.
A skipped layer is always shown with its reason; it never counts as passed.

## Engine API (frozen signatures; engine agent implements, others call)
```python
from engine import build_cii, build_zugferd, validate, render_pdf, FeatureUnavailable
build_cii(invoice: dict, profile: str = "xrechnung") -> bytes      # raises InvoiceInputError with RowError-like details
build_zugferd(invoice: dict) -> bytes                              # raises FeatureUnavailable if PDF/A-3 not possible
validate(data: bytes, filename: str = "") -> Report (dict as above)
render_pdf(invoice: dict) -> bytes
```

## Mapping API (frozen signatures)
```python
from mapping import read_table, propose, apply
read_table(data: bytes, filename: str) -> Table
propose(table: Table, seller_profile: dict, provider: str = "heuristic") -> dict  # Mapping
apply(table: Table, mapping: dict, seller_profile: dict) -> tuple[list[dict], list[RowError]]
```

## AI data rule
By default the AI provider receives column headers plus value SHAPES of up to `AI_MAX_SAMPLE_ROWS` rows
(letters -> `X`/`x`, digits -> `d`, punctuation kept: "Müller GmbH" -> "Xxxxxx XxxX", "31.10.2026" -> "dd.dd.dddd").
Real values only if the user switches on "Echte Beispielwerte senden" in the app. Never log prompts with values.
