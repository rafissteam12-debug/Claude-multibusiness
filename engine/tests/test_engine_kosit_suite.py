"""Regression over the official KoSIT XRechnung test suite (CII files only).

Read-only external folder; skipped when absent (e.g. in CI without the checkout).
Baseline 31 Oct 2026: 39/41 valid. The two known failures are code-list rules
(BR-CL-*) where the pinned CEN head differs from KoSIT's code lists.
"""
from __future__ import annotations

from pathlib import Path

import os

import pytest

from engine import validate

# XRECHNUNG_TESTSUITE_DIR: checkout root of itplr-kosit/xrechnung-testsuite (requested in docs/requests/engine.md)
SUITE = Path(os.environ.get("XRECHNUNG_TESTSUITE_DIR") or "/home/claude/itplr-kosit/xrechnung-testsuite") / "src" / "test"
BASELINE = 39
KNOWN_FAILURES = {"04.05a-INVOICE_uncefact.xml", "02.01a-cvd_INVOICE_uncefact.xml"}


@pytest.mark.skipif(not SUITE.is_dir(), reason="KoSIT test suite not present")
def test_kosit_suite_cii_regression():
    files = sorted(SUITE.rglob("*uncefact*.xml"))
    assert len(files) >= 41
    failed = {f.name for f in files if not validate(f.read_bytes(), f.name)["valid"]}
    assert len(files) - len(failed) >= BASELINE, sorted(failed)
    assert failed <= KNOWN_FAILURES, sorted(failed - KNOWN_FAILURES)
