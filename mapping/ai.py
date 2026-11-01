"""Anthropic mapping provider: HYBRID of heuristic + AI.

The heuristic runs first and stays authoritative. The AI may only
  * fill targets the heuristic left unmapped, or
  * replace heuristic fields with confidence < AI_OVERRIDE_BELOW (0.6),
and an AI field may not reuse a column the heuristic mapped with confidence >= 0.6
(except the known shared uses: VAT-rate column -> category, amounts -> expected totals).
A final guard runs `apply` on a sample: if the hybrid yields fewer valid invoices or more
row errors than the heuristic alone, the AI contributions are dropped.

Data rule (contracts/mapping.md): by default only column headers, value SHAPES of up to
AI_MAX_SAMPLE_ROWS rows and value-free column hints leave the machine. Real values only
with send_real_values=True. Prompts are never logged. Any failure -> heuristic mapping with
provider "heuristic-fallback".

Debug: with MAPPING_AI_DEBUG=1 the mapping carries `debug_ai` = the model's raw field list
(target, source_column, constant, transform, confidence; no reasons, no cell values) plus the
rejected fields with the reason. Never store a mapping with `debug_ai`.
"""
from __future__ import annotations

import json
import logging
import os
import re

from contracts.types import Table

from .apply import MappingError, apply, validate_mapping
from .heuristic import describe_profile, profile_column, propose_heuristic
from .shapes import value_shape
from .targets import ALLOWED_TARGETS, GERMAN_LABELS, TRANSFORMS

log = logging.getLogger("mapping.ai")

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_MAX_SAMPLE_ROWS = 5
TIMEOUT_SECONDS = 30.0
MAX_TOKENS = 4000
AI_OVERRIDE_BELOW = 0.6
AI_MAX_CONFIDENCE = 0.9
GUARD_ROWS = 200
# Targets that legitimately reuse a column another target already uses.
SHARED_COLUMN_TARGETS = frozenset({
    "/lines/*/vat_category", "/buyer/electronic_address_scheme",
    "/source/expected_totals/net", "/source/expected_totals/vat", "/source/expected_totals/gross",
})


def model_id() -> str:
    return os.environ.get("AI_MODEL", "").strip() or DEFAULT_MODEL


def max_sample_rows() -> int:
    try:
        return max(0, min(50, int(os.environ.get("AI_MAX_SAMPLE_ROWS", DEFAULT_MAX_SAMPLE_ROWS))))
    except ValueError:
        return DEFAULT_MAX_SAMPLE_ROWS


def debug_enabled() -> bool:
    return os.environ.get("MAPPING_AI_DEBUG", "").strip().lower() in ("1", "true", "yes")


SYSTEM_PROMPT = """You map columns of a German invoice export (CSV/XLSX) to an invoice model.
Answer with ONE JSON object only, no prose, no code fences, in exactly this format:
{"grouping": {"mode": "row_per_invoice" | "row_per_line", "invoice_number_column": "<column name or null>"},
 "fields": [{"target": "<target>", "source_column": "<column name>", "transform": ["..."], "confidence": 0.0-1.0, "reason_de": "<short German reason>"},
            {"target": "<target>", "constant": "<text>", "confidence": 0.0-1.0, "reason_de": "<short German reason>"}]}
Rules:
- Each field has exactly one of source_column (an existing column name, copied character for character) or constant.
- Each target at most once. Allowed targets (JSON Pointer, * = every line):
{targets}
- Allowed transforms, applied in order: {transforms}.
  Cells are already trimmed: do NOT use strip. Use the fewest transforms needed:
  * numbers: exactly one of de_decimal ("1.234,56", "19 %") or en_decimal ("1,234.56"); add abs only if the column has negative values (credit notes)
  * dates: exactly one of date_dmy ("31.10.2026", also with a time) or date_iso ("2026-10-31")
  * /lines/*/vat_rate: the VAT-rate column with de_decimal or en_decimal
  * /lines/*/vat_category: the SAME VAT-rate column with ["rate_to_category"] only
  * /lines/*/unit: the unit column with ["unit_map"] only
  * /lines/*/net_price: the NET UNIT price; add gross_to_net only when the column holds GROSS unit prices
  * text fields (names, street, city, description, numbers/references): transform []
  * /buyer/country: the country column with transform [] (names like "Deutschland" are converted later)
  * /type_code: a document-type column (Belegart: Rechnung/Gutschrift/Storno) with ["doc_type"] only
  * /preceding_invoice/number: the original invoice a credit note refers to (Bezug, Ursprungsrechnung), transform []
- If there is no unit-price column but one amount per row, map that amount to /lines/*/net_price and set /lines/*/quantity to constant "1".
- Per-invoice totals columns (net, VAT amount, gross) go to /source/expected_totals/* (only when one row = one invoice).
- Use row_per_line when invoice numbers repeat across rows.
- Never map seller data, IBANs or customer numbers. If there is no column for /buyer_reference, leave it out.
- Values are shown as SHAPES unless stated otherwise: X = uppercase letter, x = lowercase letter, d = digit, other characters kept.
  `column_hints` describes each column's detected value type without showing values."""


def build_request(table: Table, seller_profile: dict, send_real_values: bool = False) -> dict:
    """The exact payload sent to the model (exposed for tests of the data rule)."""
    n = max_sample_rows()
    samples = [[cell if send_real_values else value_shape(cell) for cell in row] for row in table.rows[:n]]
    hints = {}
    for i, col in enumerate(table.columns):
        p = profile_column([r[i] if i < len(r) else "" for r in table.rows])
        hint = describe_profile(p)
        if p.negative:
            hint += "; enthält negative Werte"
        hints[col] = hint
    defaults = (seller_profile or {}).get("defaults", {}) or {}
    user = {
        "columns": table.columns,
        "column_hints": hints,
        "sample_rows": samples,
        "sample_kind": "real values" if send_real_values else "shapes",
        "row_count": len(table.rows),
        "seller_defaults": {k: defaults[k] for k in ("vat_rate", "vat_category", "unit") if k in defaults},
    }
    targets = "\n".join(f"  {t}  ({GERMAN_LABELS.get(t, '')})" for t in sorted(ALLOWED_TARGETS))
    system = SYSTEM_PROMPT.replace("{targets}", targets).replace("{transforms}", ", ".join(TRANSFORMS))
    return {
        "model": model_id(),
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    }


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("response is not an object")
    return data


def _make_client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SECONDS, max_retries=1)


def _fallback(table: Table, seller_profile: dict, why: str) -> dict:
    log.warning("anthropic mapping provider unavailable (%s); using heuristic", why)  # never the prompt
    m = propose_heuristic(table, seller_profile)
    m["provider"] = "heuristic-fallback"
    m["field_sources"] = {f["target"]: "heuristic" for f in m["fields"]}
    return m


def _clean_ai_field(f) -> dict | None:
    """Normalise one AI field (drop the no-op 'strip', defaults); None if unusable."""
    if not isinstance(f, dict):
        return None
    out = {k: f[k] for k in ("target", "source_column", "constant", "transform", "confidence", "reason_de") if k in f}
    if out.get("source_column") is not None:
        tr = out.get("transform") or []
        out["transform"] = [t for t in tr if t != "strip"] if isinstance(tr, list) else tr
        if out.get("constant") is None:
            out.pop("constant", None)  # an explicit null is fine; a real constant too -> rejected by validation
    else:
        out.pop("source_column", None)
        out.pop("transform", None)
        if isinstance(out.get("constant"), (int, float)) and not isinstance(out.get("constant"), bool):
            out["constant"] = str(out["constant"])
    conf = out.get("confidence", 0.5)
    out["confidence"] = round(min(AI_MAX_CONFIDENCE, float(conf)), 2) if isinstance(conf, (int, float)) else 0.5
    out["reason_de"] = "KI: " + str(out.get("reason_de") or "Vorschlag der KI")[:200]
    return out


def _same(f: dict) -> tuple:
    return (f.get("source_column"), f.get("constant"), tuple(f.get("transform") or []))


def _debug_view(f) -> dict:
    if not isinstance(f, dict):
        return {"invalid": type(f).__name__}
    return {k: f.get(k) for k in ("target", "source_column", "constant", "transform", "confidence") if k in f}


def _quality(table: Table, mapping: dict, seller_profile: dict) -> tuple[int, int] | None:
    """(valid invoices, row errors) on a sample; None if apply cannot run."""
    sample = Table(columns=table.columns, rows=table.rows[:GUARD_ROWS], row_numbers=table.row_numbers[:GUARD_ROWS],
                   encoding=table.encoding, delimiter=table.delimiter, sheet=table.sheet)
    try:
        invoices, errors = apply(sample, mapping, seller_profile)
    except (MappingError, KeyError, TypeError, ValueError):
        return None
    return len(invoices), len(errors)


def merge(table: Table, heur: dict, ai_grouping, ai_fields: list, seller_profile: dict) -> tuple[dict, list[dict]]:
    """Hybrid mapping from the heuristic mapping and the AI's raw fields. Returns (mapping, rejected)."""
    rejected: list[dict] = []
    valid: dict[str, dict] = {}
    probe_grouping = {"mode": "row_per_invoice", "invoice_number_column": None}
    for raw in ai_fields:
        f = _clean_ai_field(raw)
        if f is None:
            rejected.append({"field": _debug_view(raw), "problem": "kein Objekt"})
            continue
        problems = validate_mapping({"grouping": probe_grouping, "fields": [f]}, table.columns)
        if problems:
            rejected.append({"field": _debug_view(f), "problem": "; ".join(problems)})
            continue
        if f["target"] in valid:
            rejected.append({"field": _debug_view(f), "problem": "Ziel doppelt"})
            continue
        valid[f["target"]] = f

    strong_cols = {f["source_column"] for f in heur["fields"]
                   if f.get("source_column") is not None and f["confidence"] >= AI_OVERRIDE_BELOW}

    def col_free(f: dict) -> bool:
        return f.get("source_column") is None or f["target"] in SHARED_COLUMN_TARGETS or f["source_column"] not in strong_cols

    fields: list[dict] = []
    sources: dict[str, str] = {}
    heur_targets = set()
    for hf in heur["fields"]:
        heur_targets.add(hf["target"])
        af = valid.get(hf["target"])
        if af is not None and hf["confidence"] < AI_OVERRIDE_BELOW and col_free(af):
            fields.append(af)
            sources[hf["target"]] = "ai"
        else:
            fields.append(hf)
            sources[hf["target"]] = "heuristic"
            if af is not None and _same(af) != _same(hf):
                rejected.append({"field": _debug_view(af), "problem": "Heuristik ist sicher genug (behalten)"})
    for t, af in valid.items():
        if t in heur_targets:
            continue
        if col_free(af):
            fields.append(af)
            sources[t] = "ai"
        else:
            rejected.append({"field": _debug_view(af), "problem": "Spalte ist schon sicher zugeordnet"})

    grouping = dict(heur["grouping"])
    if (grouping.get("invoice_number_column") is None and isinstance(ai_grouping, dict)
            and ai_grouping.get("invoice_number_column") in table.columns
            and ai_grouping.get("mode") in ("row_per_invoice", "row_per_line")):
        grouping = {"mode": ai_grouping["mode"], "invoice_number_column": ai_grouping["invoice_number_column"]}
        sources["grouping"] = "ai"

    hybrid = dict(heur, fields=fields, grouping=grouping)
    if validate_mapping(hybrid, table.columns):
        return heur, rejected + [{"field": {}, "problem": "kombinierte Zuordnung ungültig; Heuristik behalten"}]

    # never lower quality: compare apply results on a sample
    if any(s == "ai" for s in sources.values()):
        q_h = _quality(table, heur, seller_profile)
        q_x = _quality(table, hybrid, seller_profile)
        if q_h is not None and (q_x is None or q_x[0] < q_h[0] or (q_x[0] == q_h[0] and q_x[1] > q_h[1])):
            rejected.append({"field": {}, "problem": "KI-Felder verschlechtern das Ergebnis; Heuristik behalten"})
            hybrid = dict(heur)
            sources = {f["target"]: "heuristic" for f in heur["fields"]}
    hybrid["field_sources"] = sources
    return hybrid, rejected


def propose_anthropic(table: Table, seller_profile: dict, send_real_values: bool = False, client=None) -> dict:
    try:
        client = client or _make_client()
    except Exception as exc:
        return _fallback(table, seller_profile, type(exc).__name__)
    try:
        req = build_request(table, seller_profile, send_real_values)
        resp = client.messages.create(**req)
        text = "".join(getattr(b, "text", "") for b in getattr(resp, "content", []) if getattr(b, "type", "text") == "text")
        data = _extract_json(text)
        ai_fields = data.get("fields")
        if not isinstance(ai_fields, list):
            raise ValueError("fields missing")
    except Exception as exc:  # timeout, API error, bad JSON ...
        return _fallback(table, seller_profile, type(exc).__name__)

    heur = propose_heuristic(table, seller_profile)
    mapping, rejected = merge(table, heur, data.get("grouping"), ai_fields, seller_profile)
    mapping["provider"] = "anthropic"
    mapping["model"] = req["model"]
    n_ai = sum(1 for s in mapping["field_sources"].values() if s == "ai")
    log.info("anthropic mapping: %d AI fields used, %d rejected", n_ai, len(rejected))  # counts only
    if debug_enabled():
        mapping["debug_ai"] = {
            "grouping": data.get("grouping") if isinstance(data.get("grouping"), dict) else None,
            "fields": [_debug_view(f) for f in ai_fields],
            "rejected": rejected,
        }
    return mapping
