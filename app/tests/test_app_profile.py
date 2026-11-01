"""Seller profile GET/PUT with schema validation and German messages (BR-CO-26 explained)."""
from __future__ import annotations

import copy

from app.profile import validate_profile
from app.tests.helpers import login


def test_profile_get_put(client, app, seller_profile):
    h = {"X-CSRF-Token": login(client, app)}
    r = client.get("/api/v1/seller-profile")
    assert r.status_code == 404 and r.json()["error"]["code"] == "profile_missing"
    r = client.put("/api/v1/seller-profile", json=seller_profile, headers=h)
    assert r.status_code == 200 and "hints_de" in r.json()
    got = client.get("/api/v1/seller-profile").json()
    assert got["seller"]["vat_id"] == "DE123456789"
    page = client.get("/app/profile").text
    assert "BR-CO-26" in page and "Steuernummer allein reicht nicht" in page
    assert 'value="Erika Mustermann"' in page


def test_profile_errors_in_german(client, app, seller_profile):
    h = {"X-CSRF-Token": login(client, app)}
    p = copy.deepcopy(seller_profile)
    del p["seller"]["vat_id"]
    p["seller"]["tax_number"] = "12/345/67890"
    p["seller"]["country"] = "Deutschland"
    p["payment_defaults"]["iban"] = "DE00370400440532013000"
    p["seller"]["contact"]["phone"] = ""
    r = client.put("/api/v1/seller-profile", json=p, headers=h)
    assert r.status_code == 422
    e = r.json()["error"]
    assert e["code"] == "invalid_profile" and e["message_de"]
    by = {f["field"]: f["message_de"] for f in e["fields"]}
    assert "BR-CO-26" in by["/seller/vat_id"] and "Steuernummer allein" in by["/seller/vat_id"]
    assert "zweistellig" in by["/seller/country"]
    assert "IBAN" in by["/payment_defaults/iban"]
    assert "Angabe fehlt" in by["/seller/contact/phone"]
    for msg in by.values():
        assert "12/345/67890" not in msg and "Deutschland" not in msg


def test_seller_id_satisfies_br_co_26(seller_profile):
    p = copy.deepcopy(seller_profile)
    del p["seller"]["vat_id"]
    p["seller"]["seller_id"] = {"id": "KU-4711"}
    assert validate_profile(p) == []
    p["seller"]["company_id"] = "HRB 12345"
    del p["seller"]["seller_id"]
    assert validate_profile(p) == []


def test_exemption_needed_for_category_e(seller_profile):
    p = copy.deepcopy(seller_profile)
    p["defaults"]["vat_category"] = "E"
    assert any("Befreiungsgrund" in e["message_de"] for e in validate_profile(p))
    p["defaults"]["vat_exemptions"] = {"E": {"text": "Steuerbefreit (Testtext)"}}
    assert validate_profile(p) == []


def test_iban_required_for_sepa(seller_profile):
    p = copy.deepcopy(seller_profile)
    del p["payment_defaults"]["iban"]
    assert any(e["field"] == "/payment_defaults/iban" for e in validate_profile(p))
    p["payment_defaults"]["means_code"] = "30"
    assert validate_profile(p) == []


def test_profile_rejects_unknown_fields(client, app, seller_profile):
    h = {"X-CSRF-Token": login(client, app)}
    p = dict(seller_profile, extra={"x": 1})
    assert client.put("/api/v1/seller-profile", json=p, headers=h).status_code == 422
    assert client.put("/api/v1/seller-profile", content="[1,2]", headers=dict(h, **{"Content-Type": "application/json"})).status_code == 400
