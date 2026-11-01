"""H3: the validity rule requires a recognised, EN 16931 compliant profile (BT-24)."""
from __future__ import annotations

import pytest
from helpers_engine import dump, ids, set_text, tree

from engine import build_cii, validate
from engine import validation as V

GID = "/rsm:CrossIndustryInvoice/rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID"


def _with_gid(sample, gid: str, profile: str = "zugferd") -> bytes:
    inv = sample()
    if profile == "zugferd":
        del inv["buyer_reference"]
    return dump(set_text(tree(build_cii(inv, profile=profile)), GID, gid))


@pytest.mark.parametrize("gid,level", [
    ("urn:factur-x.eu:1p0:basicwl", "BASIC-WL"),
    ("urn:factur-x.eu:1p0:minimum", "MINIMUM"),
    ("urn:zugferd.de:2p0:basicwl", "BASIC-WL"),
])
def test_minimum_and_basicwl_are_never_valid(sample, gid, level):
    r = validate(_with_gid(sample, gid))
    assert r["valid"] is False
    assert r["profile"] == "zugferd" and r["guideline_id"] == gid
    cen = r["layers"][1]
    err = cen["errors"][0]
    assert err["id"] == "PROFILE-NOT-EINVOICE"
    assert level in err["message_de"] and "§ 14 UStG" in err["message_de"] and "https://" in err["message_de"]
    assert V.describe_guideline(gid) == ("zugferd", level, False)


@pytest.mark.parametrize("gid", [
    "urn:beliebig:irgendwas",
    "",
    "urn:cen.eu:en16931:2017#compliant#urn:beliebig",
    "urn:cen.eu:en16931:2017-extra",
    "xx urn:xeinkauf.de:kosit:xrechnung_3.0",
    "urn:factur-x.eu:1p0:basicwl-extended",
    "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0#compliant#urn:beliebig",
    "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0#conformant#urn:xeinkauf.de:kosit:extension:",
    "urn:cen.eu:en16931:2017#conformant#urn:xeinkauf.de:kosit:extension:xrechnung_3.0",
])
def test_unknown_guideline_is_never_valid(sample, gid):
    r = validate(_with_gid(sample, gid))
    assert r["valid"] is False and r["profile"] == "unknown"
    assert r["guideline_id"] == (gid or None)
    err = r["layers"][1]["errors"][0]
    assert err["id"] == "PROFILE-UNKNOWN"
    assert err["message_de"].startswith("Unbekanntes Profil") and "keine E-Rechnung nach EN 16931" in err["message_de"]


def test_unknown_profile_never_valid_even_with_clean_layers():
    layers = [V._layer("XSD"), V._layer("EN16931"), V._layer("XRechnung", ran=False, skipped_reason="x"),
              V._layer("KoSIT", ran=False, skipped_reason="y")]
    assert V.is_valid(layers, "unknown", "dev") is False
    assert V.is_valid(layers, "zugferd", "dev") is True


@pytest.mark.parametrize("gid,profile,level", [
    ("urn:cen.eu:en16931:2017", "zugferd", "EN16931"),
    ("urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended", "zugferd", "EXTENDED"),
    ("urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic", "zugferd", "BASIC"),
    ("urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0", "xrechnung", "XRECHNUNG"),
    ("urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
     "#conformant#urn:xeinkauf.de:kosit:extension:xrechnung_3.0", "xrechnung", "XRECHNUNG"),
    ("urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
     "#compliant#urn:xeinkauf.de:kosit:xrechnung:cvd_0.9", "xrechnung", "XRECHNUNG"),
])
def test_recognised_guidelines(gid, profile, level):
    assert V.describe_guideline(gid) == (profile, level, True)


def test_compliant_profiles_stay_valid(sample):
    xr = validate(build_cii(sample()))
    assert xr["valid"] and xr["profile"] == "xrechnung" and xr["guideline_id"] == V_XR()
    zf = validate(_with_gid(sample, "urn:cen.eu:en16931:2017"))
    assert zf["valid"] and zf["profile"] == "zugferd" and zf["guideline_id"] == "urn:cen.eu:en16931:2017", ids(zf)
    ext = validate(_with_gid(sample, "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"))
    assert ext["profile"] == "zugferd" and "PROFILE-UNKNOWN" not in ids(ext) and "PROFILE-NOT-EINVOICE" not in ids(ext)


def V_XR():
    from engine.cii import XRECHNUNG_ID
    return XRECHNUNG_ID


def test_input_error_reports_have_no_guideline():
    r = validate(b"<x")
    assert r["guideline_id"] is None and r["profile"] == "unknown" and not r["valid"]


@pytest.mark.parametrize("suffix", ["#conformant#urn:xeinkauf.de:kosit:extension:xrechnung_3.0",
                                    "#compliant#urn:xeinkauf.de:kosit:xrechnung:cvd_0.9"])
def test_extension_and_cvd_ids_are_xrechnung(sample, suffix):
    gid = V_XR() + suffix
    r = validate(_with_gid(sample, gid, profile="xrechnung"))
    assert r["profile"] == "xrechnung" and r["guideline_id"] == gid
    assert not {"PROFILE-UNKNOWN", "PROFILE-NOT-EINVOICE"} & ids(r)
    assert r["layers"][2]["ran"]
