"""Shared fixtures for engine tests. Fictional data only (.example addresses, test IBAN)."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Run from the repo root with `python -m pytest` (puts the root on sys.path for `engine` and `contracts`).

HERE = str(Path(__file__).resolve().parent)
if HERE not in sys.path:  # for helpers_engine.py
    sys.path.insert(0, HERE)

SAMPLES = ROOT / "engine" / "samples"


REAL_TOOLS = os.environ.get("ENGINE_REAL_TOOLS") == "1"  # opt-in: keep KOSIT_*/MUSTANG_JAR for real-tool tests


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, request):
    if REAL_TOOLS and request.node.get_closest_marker("real_tools"):
        return
    for var in ("KOSIT_VALIDATOR_JAR", "KOSIT_CONFIG_DIR", "MUSTANG_JAR", "APP_ENV"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def sample():
    data = json.loads((SAMPLES / "schreinerei.json").read_text(encoding="utf-8"))
    return lambda: copy.deepcopy(data)


@pytest.fixture
def sample_files():
    return sorted(SAMPLES.glob("*.json"))


def pytest_configure(config):
    config.addinivalue_line("markers", "real_tools: runs real KoSIT/Mustang; only with ENGINE_REAL_TOOLS=1")
