"""Belegbrücke mapping: CSV/XLSX export -> invoice model (contracts/invoice.schema.json).

Public API (frozen, contracts/mapping.md):
    read_table(data, filename) -> Table
    propose(table, seller_profile, provider="heuristic") -> Mapping dict
    apply(table, mapping, seller_profile) -> (invoices, row_errors)
"""
from __future__ import annotations

from contracts.types import RowError, Table

from .apply import MappingError, apply, validate_mapping
from .reader import TableReadError, read_table
from .shapes import value_shape

__all__ = ["read_table", "propose", "apply", "value_shape", "validate_mapping", "TableReadError", "MappingError", "Table", "RowError"]


def propose(table: Table, seller_profile: dict, provider: str = "heuristic", *,
            send_real_values: bool = False, client=None) -> dict:
    """Propose a Mapping. provider: 'heuristic' (offline) or 'anthropic' (falls back to heuristic).

    `send_real_values` ("Echte Beispielwerte senden") only affects the anthropic provider.
    The mapping dict carries `provider`: 'heuristic', 'anthropic' or 'heuristic-fallback'.
    """
    if provider == "anthropic":
        from .ai import propose_anthropic
        return propose_anthropic(table, seller_profile, send_real_values=send_real_values, client=client)
    if provider != "heuristic":
        raise ValueError(f"unknown provider {provider!r}")
    from .heuristic import propose_heuristic
    return propose_heuristic(table, seller_profile)
