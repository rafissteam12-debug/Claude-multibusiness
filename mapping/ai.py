"""Anthropic mapping provider.

Data rule (contracts/mapping.md): by default only column headers and value SHAPES of up to
AI_MAX_SAMPLE_ROWS rows leave the machine. Real values only with send_real_values=True.
Prompts are never logged. Any failure -> heuristic mapping with provider "heuristic-fallback".
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid

from contracts.types import Table

from .apply import validate_mapping
from .heuristic import propose_heuristic
from .shapes import value_shape
from .targets import ALLOWED_TARGETS, GERMAN_LABELS, TRANSFORMS

log = logging.getLogger("mapping.ai")

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_MAX_SAMPLE_ROWS = 5
TIMEOUT_SECONDS = 30.0
MAX_TOKENS = 4000


def model_id() -> str:
    return os.environ.get("AI_MODEL", "").strip() or DEFAULT_MODEL


def max_sample_rows() -> int:
    try:
        return max(0, min(50, int(os.environ.get("AI_MAX_SAMPLE_ROWS", DEFAULT_MAX_SAMPLE_ROWS))))
    except ValueError:
        return DEFAULT_MAX_SAMPLE_ROWS


SYSTEM_PROMPT = """You map columns of a German invoice export (CSV/XLSX) to an invoice model.
Answer with ONE JSON object only, no prose, no code fences, in exactly this format:
{"grouping": {"mode": "row_per_invoice" | "row_per_line", "invoice_number_column": "<column name or null>"},
 "fields": [{"target": "<target>", "source_column": "<column name>", "transform": ["..."], "confidence": 0.0-1.0, "reason_de": "<short German reason>"},
            {"target": "<target>", "constant": "<text>", "confidence": 0.0-1.0, "reason_de": "<short German reason>"}]}
Rules:
- Each field has exactly one of source_column (an existing column name, spelled exactly) or constant.
- Each target at most once. Allowed targets (JSON Pointer, * = every line):
{targets}
- Allowed transforms, applied in order: {transforms}.
  de_decimal "1.234,56"->"1234.56"; en_decimal "1,234.56"->"1234.56"; date_dmy "31.10.2026"; date_iso "2026-10-31";
  abs for negative credit-note amounts; gross_to_net only on /lines/*/net_price when the column holds GROSS unit prices;
  rate_to_category on the VAT-rate column for /lines/*/vat_category; unit_map for unit names (Stk, Std, Tag, kg ...).
- Never map seller data or IBANs: they come from the seller profile.
- If there is no unit-price column but one amount per invoice row, map that amount to /lines/*/net_price and set /lines/*/quantity to constant "1".
- Use row_per_line when invoice numbers repeat across rows.
- If there is no column for /buyer_reference, leave it out.
- Values are shown as SHAPES unless stated otherwise: X = uppercase letter, x = lowercase letter, d = digit, other characters kept."""


def build_request(table: Table, seller_profile: dict, send_real_values: bool = False) -> dict:
    """The exact payload sent to the model (exposed for tests of the data rule)."""
    n = max_sample_rows()
    samples = []
    for row in table.rows[:n]:
        samples.append([cell if send_real_values else value_shape(cell) for cell in row])
    defaults = (seller_profile or {}).get("defaults", {}) or {}
    user = {
        "columns": table.columns,
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
    return json.loads(text[start:end + 1])


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
    return m


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
        mapping = {
            "mapping_id": str(uuid.uuid4()),
            "version": 1,
            "provider": "anthropic",
            "model": req["model"],
            "grouping": data.get("grouping"),
            "fields": data.get("fields"),
        }
        for f in mapping["fields"] or []:
            if isinstance(f, dict) and f.get("source_column") is not None:
                f.setdefault("transform", [])
            if isinstance(f, dict):
                f.setdefault("confidence", 0.5)
                f.setdefault("reason_de", "Vorschlag der KI")
        problems = validate_mapping(mapping, table.columns)
        if problems:
            return _fallback(table, seller_profile, f"invalid response ({len(problems)} problems)")
    except Exception as exc:  # timeout, API error, bad JSON ...
        return _fallback(table, seller_profile, type(exc).__name__)

    # fill required defaults the model left out, from the heuristic (constants only, no columns)
    have = {f["target"] for f in mapping["fields"]}
    heur = propose_heuristic(table, seller_profile)
    for f in heur["fields"]:
        if f["target"] not in have and "constant" in f:
            mapping["fields"].append(f)
            have.add(f["target"])
    return mapping
