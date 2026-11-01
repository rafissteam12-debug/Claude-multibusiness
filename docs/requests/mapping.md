# Requests from the mapping agent

1. **Mapping contract: add `provider`** (`"heuristic" | "anthropic" | "heuristic-fallback"`) and, for the AI provider only, an optional `model`. Both are already emitted. The UI needs `provider` to show "Vorschlag ohne KI".
2. **`propose` keyword-only extras**: `send_real_values: bool = False` ("Echte Beispielwerte senden") and `client=None` (tests). This is backwards compatible with the frozen signature. The app agent should pass `send_real_values` from the user's toggle. It cannot go into `seller_profile`, because that schema has `additionalProperties: false`.
3. **config.md `AI_MODEL` default**: the mapping falls back to `claude-sonnet-5-5` when `AI_MODEL` is empty. Please confirm this or set a value.
4. **Document the exceptions** in mapping.md: `read_table` raises `mapping.TableReadError` and `apply` raises `mapping.MappingError` for an invalid mapping. Both are `ValueError` subclasses with a German `message_de` that contains no cell values.
5. **Document the apply semantics**: an invoice with any RowError is left out of the returned list, and the app shows its errors.
6. **Optional schema addition**: a line-level `net_amount` (BT-131, informational) so line totals from exports can be cross-checked per line. At present only `source/expected_totals` is possible, and only for one row per invoice.
7. **Optional transform for the closed list**: a way to set `type_code` 381 from a document-type column ("Gutschrift") with positive amounts.

## Status (orchestrator, 31 Oct)
provider/model keys, kw-only extras, TableReadError/MappingError, left-out rule: in contracts. AI_MODEL default claude-sonnet-5-5 confirmed. Optional items -> docs/ideas.md (after beta data).
8. **Mapping contract: per-field provenance.** The hybrid AI provider records which source decided each field. For now this is a top-level `field_sources: {"<target>": "heuristic"|"ai", "grouping"?: "ai"}`, because the field object in mapping.md has no such key. Proposal: allow an optional per-field `"source": "heuristic"|"ai"` (or bless `field_sources`). The app should not store `debug_ai` (present only with `MAPPING_AI_DEBUG=1`).
9. **config.md: `MAPPING_AI_DEBUG`** (mapping, default unset). `1` attaches the model's raw target list (no cell values) to the mapping. The network test sets it itself; it is meant for CI diagnosis only.

## Wave 4 fix round (review H1, M3–M6, L6) — contract additions, all implemented in mapping already
10. **New transform `doc_type`** for the closed list in mapping.md: document-type word -> BT-3 code.
    "Gutschrift", "GS", "Storno", "Stornorechnung", "Rechnungskorrektur", "Korrektur", "credit note", "credit", "Erstattung", "381" -> `"381"`;
    "Rechnung", "RE", "Ausgangsrechnung", "Abschlags-/Teil-/Schlussrechnung", "invoice", "380" -> `"380"`
    (case, spaces, `-`, `_`, `.` ignored); anything else -> RowError `invalid_value`. Used on target `/type_code`
    (now an allowed mapping target). Semantics in apply: a mapped 381 makes negative quantity/price cells positive
    (as if `abs` were set); a mapped 380 whose lines are all negative -> RowError `invalid_value` on `/type_code`;
    an empty cell -> type decided by amount signs as before.
11. **`propose()` result key `unmapped_required`**: `list[str]` of target pointers that are required but not mapped
    (REQUIRED_TARGETS; plus `/buyer_reference` when `seller_profile.defaults.profile` is `xrechnung`, the default).
    `/number` counts as mapped when `grouping.invoice_number_column` is set. Recomputed after the AI merge.
12. **`propose()` result key `warnings`**: `list[{"target": str, "code": str, "reason_de": str}]`. Codes:
    `no_delivery_date` (target `/delivery_date`, reason "Kein Leistungsdatum gefunden"; neither `/delivery_date` nor
    `/period/*` mapped; the app offers "Leistungsdatum = Rechnungsdatum" = add a `/delivery_date` field with the same
    `source_column` and `transform` as `/issue_date` — apply supports two targets from one column) and
    `zero_rate_category` (target `/lines/*/vat_category`; the rate column has 0 % values, the category comes from
    `rate_to_category` and the profile default is S).
13. **`rate_to_category` semantics change** (mapping.md says "0"->user default): 0 % with default S is no longer
    guessed as Z; it gives RowError `missing_exemption` "Zeile N: 0 % Umsatzsteuer: Bitte wählen Sie die Kategorie
    (z. B. steuerfrei, innergemeinschaftlich, Kleinunternehmer) in der Zuordnung." Other defaults (E, Z, …) are used as before.
14. **Date transforms**: `date_dmy` and `date_iso` each accept the other format as a fallback (they cannot overlap).
15. **read_table limits** (for api.md/help texts): 10 MB input, 20 000 data rows, 200 columns; XLSX zip: ≤ 50 MB
    unpacked in total, ≤ 1000 members, compression ratio ≤ 100 for members > 1 MiB. Each raises `TableReadError`
    with a German `message_de`. The app part of H1 (run read_table/propose/validate in a thread pool) is still open.

## Status (orchestrator, 1 Nov, wave 4)
Wave 4 items merged into contracts/ (mapping.md, api.md, config.md), .env.example and .github/workflows/ci.yml; deferred items in docs/ideas.md.
