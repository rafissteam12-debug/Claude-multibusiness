from __future__ import annotations

import pytest

from mapping import read_table
from mapping.scoring import FIXTURES_DIR, seller_profile as _seller_profile


@pytest.fixture
def seller_profile() -> dict:
    return _seller_profile()


@pytest.fixture
def load():
    def _load(name: str):
        return read_table((FIXTURES_DIR / name).read_bytes(), name)
    return _load


@pytest.fixture
def csv_table():
    def _csv(text: str, encoding: str = "utf-8"):
        return read_table(text.encode(encoding), "test.csv")
    return _csv
