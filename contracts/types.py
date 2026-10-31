"""Shared data types (contracts). Orchestrator-owned. No logic here."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Table:
    columns: list[str]
    rows: list[list[str]]
    row_numbers: list[int]
    encoding: str = "utf-8"
    delimiter: str | None = None
    sheet: str | None = None


@dataclass
class RowError:
    row: int
    column: str | None
    field: str
    code: str
    message_de: str


class FeatureUnavailable(Exception):
    """A capability needs a component that is not installed (e.g. Mustang for PDF/A-3)."""


class InvoiceInputError(Exception):
    def __init__(self, errors: list[RowError]):
        super().__init__(f"{len(errors)} input error(s)")
        self.errors = errors
