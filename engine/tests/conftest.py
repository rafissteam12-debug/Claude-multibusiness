"""Shared fixtures for engine tests. Fictional data only (.example addresses, test IBAN)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Run from the repo root with `python -m pytest` (puts the root on sys.path for `engine` and `contracts`).

HERE = str(Path(__file__).resolve().parent)
if HERE not in sys.path:  # for helpers_engine.py
    sys.path.insert(0, HERE)

SAMPLES = ROOT / "engine" / "samples"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("KOSIT_VALIDATOR_JAR", "KOSIT_CONFIG_DIR", "MUSTANG_JAR", "APP_ENV"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def sample():
    data = json.loads((SAMPLES / "schreinerei.json").read_text(encoding="utf-8"))
    return lambda: copy.deepcopy(data)


@pytest.fixture
def sample_files():
    return sorted(SAMPLES.glob("*.json"))
