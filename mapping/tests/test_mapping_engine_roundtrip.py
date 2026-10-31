"""mapping -> engine round trip: every fixture invoice builds as XRechnung CII and validates."""
from __future__ import annotations

import copy

import pytest

from mapping import apply, propose
from mapping.fixtures.make_fixtures import FIXTURES

pytestmark = pytest.mark.integration


def _invoices(name, load, seller_profile):
    t = load(name)
    invoices, errors = apply(t, propose(t, seller_profile), seller_profile)
    assert errors == []
    return invoices


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_invoices_build_and_validate(name, load, seller_profile):
    engine = pytest.importorskip("engine")
    for inv in _invoices(name, load, seller_profile):
        inv = copy.deepcopy(inv)
        inv.setdefault("buyer_reference", "TEST-REFERENZ")  # the app asks the user when the file has none
        xml = engine.build_cii(inv, profile="xrechnung")
        report = engine.validate(xml, f"{inv['number']}.xml")
        failed = [(l["name"], e["id"], e.get("text_en") or e.get("message_de"))
                  for l in report["layers"] for e in l["errors"]]
        assert failed == [], (inv["number"], failed)
        ran = {l["name"]: l["ran"] for l in report["layers"]}
        assert ran.get("XSD") and ran.get("EN16931") and ran.get("XRechnung"), ran
        assert engine.totals_warning(inv) is None, (inv["number"], engine.totals_warning(inv))
