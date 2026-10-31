"""Belegbrücke engine: invoice model -> XRechnung 3.0 CII / ZUGFeRD, and validation.

Frozen API (contracts/mapping.md):
    build_cii(invoice, profile="xrechnung") -> bytes
    build_zugferd(invoice) -> bytes
    validate(data, filename="") -> Report dict
    render_pdf(invoice) -> bytes
Helper (requested as contract addition, docs/requests/engine.md):
    totals_warning(invoice) -> dict | None   # for Report["totals_warning"]

Note: engine/generate.py and engine/validate.py are CLI scripts; do not import
them as `engine.generate` / `engine.validate` (the latter would shadow the
`validate` function on the package).
"""
from contracts.types import FeatureUnavailable, InvoiceInputError

from .cii import build_cii, compute_totals, totals_warning
from .pdf import render_pdf
from .validation import validate
from .zugferd import build_zugferd

__all__ = ["build_cii", "build_zugferd", "validate", "render_pdf", "FeatureUnavailable", "InvoiceInputError",
           "totals_warning", "compute_totals"]
