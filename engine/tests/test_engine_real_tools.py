"""Opt-in checks against the real KoSIT validator and Mustang (CI/Docker only).

Run with ENGINE_REAL_TOOLS=1 plus KOSIT_VALIDATOR_JAR (+ KOSIT_CONFIG_DIR) and/or MUSTANG_JAR.
Skipped otherwise; the autouse env cleaner leaves these variables alone for tests marked real_tools.
"""
from __future__ import annotations

import os

import pytest
from helpers_engine import ids

from engine import build_cii, validate, validate_many

pytestmark = [pytest.mark.real_tools,
              pytest.mark.skipif(os.environ.get("ENGINE_REAL_TOOLS") != "1", reason="ENGINE_REAL_TOOLS=1 not set")]

needs_kosit = pytest.mark.skipif(not os.environ.get("KOSIT_VALIDATOR_JAR"), reason="KOSIT_VALIDATOR_JAR not set")
needs_mustang = pytest.mark.skipif(not os.environ.get("MUSTANG_JAR"), reason="MUSTANG_JAR not set")


@needs_kosit
def test_real_kosit_single_and_batch(sample):
    good = build_cii(sample())
    bad = good.replace(b"<ram:BuyerReference>KD-10234</ram:BuyerReference>", b"")
    one = validate(good)
    assert one["layers"][3]["ran"] and not one["layers"][3]["errors"], ids(one, "KoSIT")
    many = validate_many([(good, "a.xml"), (bad, "b.xml"), (good, "c.xml")])
    kosit = [r["layers"][3] for r in many]
    assert all(l["ran"] for l in kosit), [l["skipped_reason"] for l in kosit]
    assert not kosit[0]["errors"] and not kosit[2]["errors"] and kosit[1]["errors"]


@needs_mustang
def test_real_mustang_zugferd_roundtrip(sample):
    from engine import build_zugferd
    inv = sample()
    del inv["buyer_reference"]
    r = validate(build_zugferd(inv), "rechnung.pdf")
    pdfa = r["layers"][-1]
    assert pdfa["name"] == "PDF/A" and pdfa["ran"] and not pdfa["errors"], pdfa
