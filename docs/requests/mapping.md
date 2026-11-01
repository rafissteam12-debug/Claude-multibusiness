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
