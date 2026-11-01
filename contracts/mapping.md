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
  "provider": "heuristic" | "anthropic" | "heuristic-fallback",
  "model": "claude-... (only when provider is anthropic)",
  "field_sources": {"/number": "heuristic", "/buyer/name": "ai"},
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
  `strip`, `upper`, `doc_type` (document-type word -> BT-3: Gutschrift/GS/Storno/Stornorechnung/Rechnungskorrektur/
  Korrektur/credit note/credit/Erstattung/381 -> "381"; Rechnung/RE/Ausgangsrechnung/Abschlags-/Teil-/Schlussrechnung/
  invoice/380 -> "380"; case, spaces, `-_.` ignored; anything else -> RowError `invalid_value`; used on target `/type_code`).
- Transform semantics: `date_dmy` and `date_iso` each accept the other format as fallback. `rate_to_category`: a 0 % rate
  with seller default category S is never guessed (RowError `missing_exemption`, the user picks the category); other
  defaults (E, Z, …) apply as given. A mapped 381 makes negative quantity/price cells positive; a mapped 380 whose lines
  are all negative -> `invalid_value`. One source column may feed several targets (e.g. `/issue_date` and `/delivery_date`).
- `propose()` results also carry `"unmapped_required": [pointer, ...]` (required targets not mapped; includes
  `/buyer_reference` for the XRechnung profile) and `"warnings": [{"target", "code", "reason_de"}]` with codes
  `no_delivery_date` and `zero_rate_category`. The app blocks conversion in the UI while `unmapped_required` is non-empty.
- Seller fields are NEVER mapped: they come from the seller profile.
- Saved mappings store column names, constants and transforms only — never cell values.

## RowError (mapping -> app -> UI)
`RowError(row: int, column: str|None, field: str (JSON Pointer), code: str, message_de: str)`
Codes: `missing_required`, `bad_number`, `bad_date`, `unknown_unit`, `inconsistent_invoice` (line rows disagree on header fields), `negative_amount`, `buyer_address_missing`, `invalid_value`, `bad_iban`, `missing_exemption`, `forbidden_exemption`.

## Report (engine -> app -> UI and /check)
```json
{"valid": true, "profile": "xrechnung" | "zugferd" | "unknown", "guideline_id": "<BT-24 as found>" | null,
 "layers": [{"name": "XSD" | "EN16931" | "XRechnung" | "KoSIT" | "PDF/A", "ran": true, "skipped_reason": null,
             "errors": [{"id": "BR-DE-15", "message_de": "...", "text_en": "...", "location": "/xpath"}],
             "warnings": [...]}],
 "totals_warning": null | {"expected": {...}, "computed": {...}}}
```
**Validity rule:** `valid` = XSD, EN16931 and XRechnung layers ran with zero errors (XRechnung layer only for the
XRechnung profile) AND, when `APP_ENV` is `staging` or `prod`, the KoSIT layer ran with zero errors.
`profile` must be `xrechnung` or `zugferd`: `unknown` (error `PROFILE-UNKNOWN`) is never valid; ZUGFeRD MINIMUM and BASIC-WL
carry `PROFILE-NOT-EINVOICE` and are invalid (BMF 15.10.2024 excludes them); BASIC, EN16931, EXTENDED and XRechnung IDs are accepted.
For PDF input a `PDF/A` layer follows; without `MUSTANG_JAR` it is skipped ("PDF/A-3-Konformität nicht geprüft").
A skipped layer is always shown with its reason; it never counts as passed.

## Engine API (frozen signatures; engine agent implements, others call)
```python
from engine import build_cii, build_zugferd, validate, render_pdf, FeatureUnavailable
build_cii(invoice: dict, profile: str = "xrechnung") -> bytes      # raises InvoiceInputError with RowError-like details
build_zugferd(invoice: dict) -> bytes                              # raises FeatureUnavailable if PDF/A-3 not possible
validate(data: bytes, filename: str = "") -> Report (dict as above)
validate_many(items: list[tuple[bytes, str]]) -> list[Report]       # same order; one KoSIT JVM per chunk; bounded by KOSIT_MAX_PARALLEL
render_pdf(invoice: dict) -> bytes
totals_warning(invoice: dict) -> dict | None   # compares source.expected_totals with computed totals; the app puts it into Report.totals_warning
```

## Mapping API (frozen signatures)
```python
from mapping import read_table, propose, apply
read_table(data: bytes, filename: str) -> Table
propose(table: Table, seller_profile: dict, provider: str = "heuristic", *, send_real_values: bool = False, client=None) -> dict  # Mapping
# raises mapping.TableReadError (unreadable file) / mapping.MappingError (invalid mapping); UI shows "Vorschlag ohne KI" when provider != "anthropic"
apply(table: Table, mapping: dict, seller_profile: dict) -> tuple[list[dict], list[RowError]]
# an invoice with any RowError is left out of the list; only its errors are returned
# read_table limits: 10 MB input, 20 000 data rows, 200 columns; XLSX zip <= 50 MB unpacked, <= 1000 members,
# ratio <= 100 for members > 1 MiB. TableReadError and MappingError are ValueError subclasses with message_de (no cell values).
```

## AI policy
Hybrid: the heuristic decides first; the AI may only fill unmapped fields or replace fields with confidence < 0.6, and AI fields that make the sample worse are dropped. The AI can never lower mapping quality.

## AI data rule
By default the AI provider receives column headers plus value SHAPES of up to `AI_MAX_SAMPLE_ROWS` rows
(letters -> `X`/`x`, digits -> `d`, punctuation kept: "Müller GmbH" -> "Xxxxxx XxxX", "31.10.2026" -> "dd.dd.dddd").
Real values only if the user switches on "Echte Beispielwerte senden" in the app. Never log prompts with values.
