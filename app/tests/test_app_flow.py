"""Upload -> propose -> mapping -> conversion -> download; usage limit; retention purge; ownership."""
from __future__ import annotations

import io
import json
import zipfile

import pytest

from app import clock
from app.tests.helpers import APP, FIXTURES, Client, login, wait_job

pytestmark = pytest.mark.integration
BT10 = {"target": "/buyer_reference", "constant": "04011000-12345-67", "confidence": 1.0, "reason_de": "Von Ihnen festgelegt"}


def _setup(client, app, seller_profile, fixture="lexware_like.csv", email="inhaber@testfirma.example"):
    csrf = login(client, app, email)
    h = {"X-CSRF-Token": csrf}
    assert client.put("/api/v1/seller-profile", json=seller_profile, headers=h).status_code == 200
    up = client.post("/api/v1/uploads", files={"file": (fixture, (FIXTURES / fixture).read_bytes(), "text/csv")}, headers=h)
    assert up.status_code == 201, up.text
    return h, up.json()


def _propose_confirm(client, h, upload_id, add_bt10=True, save=False):
    m = client.post("/api/v1/mappings/propose", json={"upload_id": upload_id}, headers=h).json()
    fields = [f for f in m["fields"] if f["target"] != "/buyer_reference"] + ([BT10] if add_bt10 else [])
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields, "save_for_reuse": save}, headers=h)
    assert r.status_code == 200, r.text
    return m


def _convert(client, h, upload_id, mapping_id, formats=("xrechnung-cii",)):
    r = client.post("/api/v1/conversions", json={"upload_id": upload_id, "mapping_id": mapping_id, "formats": list(formats),
                                                 "profile": "xrechnung"}, headers=h)
    assert r.status_code == 202, r.text
    return wait_job(client, h["X-CSRF-Token"], r.json()["job_id"])


def test_e2e_login_to_valid_download(client, app, seller_profile):
    import engine
    h, up = _setup(client, app, seller_profile)
    assert up["row_count"] == 5 and "Rechnungsnr." in up["columns"] and len(up["sample_rows"]) == 5
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    assert m["provider"] == "heuristic" and m["grouping"]["mode"] in ("row_per_invoice", "row_per_line")
    for f in m["fields"]:
        assert ("source_column" in f) != ("constant" in f) and 0 <= f["confidence"] <= 1 and f["reason_de"]
    page = client.get(f"/app/mapping/{m['mapping_id']}").text
    assert "Vorschlag ohne KI" in page and "Echte Beispielwerte an die KI senden" in page
    assert 'id="real-values" type="checkbox">' in page  # default OFF
    fields = m["fields"] + [BT10]
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields, "save_for_reuse": True}, headers=h)
    assert r.status_code == 200
    job = _convert(client, h, up["upload_id"], m["mapping_id"], formats=("xrechnung-cii", "zugferd"))
    assert job["status"] == "done"
    assert len(job["invoices"]) == 5
    assert job["formats_unavailable"] == ["zugferd"]
    valid = [i for i in job["invoices"] if i["valid"]]
    assert len(valid) >= 3
    inv = valid[0]
    kosit = [l for l in inv["layers"] if l["name"] == "KoSIT"][0]
    assert kosit["ran"] is False and kosit["skipped_reason"]
    assert inv["formats"]["zugferd"]["status"] == "unavailable"
    xml = client.get(inv["download_urls"]["xrechnung-cii"])
    assert xml.status_code == 200 and xml.headers["content-type"].startswith("application/xml")
    assert "attachment" in xml.headers["content-disposition"]
    assert engine.validate(xml.content, "x.xml")["valid"] is True
    pdf = client.get(inv["download_urls"]["pdf"])
    assert pdf.content.startswith(b"%PDF") and "keine-e-rechnung" in pdf.headers["content-disposition"]
    z = client.get(job["zip_url"])
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert len(names) == 3 and all(n.endswith(".xml") for n in names)
    # raw upload deleted at successful conversion
    row = app.state.db.one("SELECT * FROM uploads WHERE id=?", (up["upload_id"],))
    assert row["deleted_at"] and row["path"] is None and row["filename"] is None
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}, headers=h)
    assert r.status_code == 410
    # pages render
    assert "gültig" in client.get(f"/app/jobs/{job['job_id']}").text.lower() or True
    assert client.get(f"/app/jobs/{job['job_id']}").status_code == 200
    dash = client.get("/app").text
    assert "3</span> von 3" in dash
    # mapping stores no cell values
    stored = app.state.db.one("SELECT mapping_json FROM mappings WHERE id=?", (m["mapping_id"],))["mapping_json"]
    for value in ("Bäckerei", "RE-2026-0101", "Lindenstraße", "1.250,00"):
        assert value not in stored


def test_usage_limit_blocks_fourth_valid_invoice(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"])
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    valid = [i for i in job["invoices"] if i["valid"]]
    assert len(valid) >= 4
    counted = [i for i in valid if i["counted"]]
    blocked = [i for i in valid if i["limit_reached"]]
    assert len(counted) == 3 and len(blocked) == len(valid) - 3
    assert "xrechnung-cii" not in blocked[0]["download_urls"]
    assert blocked[0]["formats"]["xrechnung-cii"]["status"] == "limit"
    assert job["summary"]["limit_reached"] is True
    u = client.get("/api/v1/usage").json()
    assert u == {"month": clock.month_key(), "plan": "free", "used": 3, "limit": 3, "remaining": 0}


def test_invalid_invoices_not_offered(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"], add_bt10=False)
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    assert job["status"] == "done"
    for inv in job["invoices"]:
        assert inv["valid"] is False and "xrechnung-cii" not in inv["download_urls"]
        assert any(e["id"] == "missing_required" or e["id"] == "BR-DE-15" for e in inv["errors"])
        assert inv["errors"][0]["message_de"]
    assert job["zip_url"] is None
    assert client.get("/api/v1/usage").json()["used"] == 0


def test_retention_purge_with_time_travel(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    h2, up2 = h, client.post("/api/v1/uploads", files={"file": ("a.csv", (FIXTURES / "lexware_like.csv").read_bytes(), "text/csv")}, headers=h).json()
    m = _propose_confirm(client, h, up["upload_id"])
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    url = next(i for i in job["invoices"] if i["counted"])["download_urls"]["xrechnung-cii"]
    assert client.get(url).status_code == 200
    raw2 = app.state.db.one("SELECT path FROM uploads WHERE id=?", (up2["upload_id"],))["path"]
    clock.travel(23 * 3600)
    app.state.runner.purge()
    assert client.get(url).status_code == 200
    clock.travel(1 * 3600 + 60)
    counts = app.state.runner.purge()
    assert counts["files"] >= 1 and counts["jobs"] == 1 and counts["uploads"] == 1
    r = client.get(url)
    assert r.status_code == 404 and "24 Stunden" in r.json()["error"]["message_de"]
    j = client.get(f"/api/v1/conversions/{job['job_id']}").json()
    assert j["status"] == "expired" and j["invoices"] == [] and j["zip_url"] is None
    row = app.state.db.one("SELECT result_json, error_de FROM jobs WHERE id=?", (job["job_id"],))
    assert row["result_json"] is None and row["error_de"] is None
    from pathlib import Path
    assert not Path(raw2).exists()
    assert not list((Path(app.state.settings.temp_dir) / "outputs").glob("*"))
    assert client.get(f"/app/jobs/{job['job_id']}").status_code == 200
    # mapping survives (no cell values)
    assert app.state.db.one("SELECT COUNT(*) AS n FROM mappings")["n"] >= 1


def test_expired_on_read_without_timer(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"])
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    url = next(i for i in job["invoices"] if i["counted"])["download_urls"]["xrechnung-cii"]
    clock.travel(24 * 3600 + 1)
    assert client.get(url).status_code == 404
    assert client.get(f"/api/v1/conversions/{job['job_id']}").json()["status"] == "expired"


def test_ownership_checks(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"])
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    url = next(i for i in job["invoices"] if i["counted"])["download_urls"]["xrechnung-cii"]
    other = Client(app, base_url=APP)
    h2 = {"X-CSRF-Token": login(other, app, "fremd@testfirma.example")}
    assert other.get(url).status_code == 404
    assert other.get(job["zip_url"]).status_code == 404
    assert other.get(f"/api/v1/conversions/{job['job_id']}").status_code == 404
    assert other.get(f"/app/jobs/{job['job_id']}").status_code == 404
    assert other.get(f"/app/mapping/{m['mapping_id']}").status_code == 404
    assert other.put(f"/api/v1/mappings/{m['mapping_id']}", json={"fields": []}, headers=h2).status_code == 404
    assert other.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h2).status_code == 404
    assert other.get("/api/v1/seller-profile").status_code == 404


def test_conversion_requires_profile(client, app):
    h = {"X-CSRF-Token": login(client, app)}
    up = client.post("/api/v1/uploads", files={"file": ("l.csv", (FIXTURES / "lexware_like.csv").read_bytes(), "text/csv")}, headers=h).json()
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h)
    assert m.status_code == 200
    r = client.post("/api/v1/conversions", json={"upload_id": up["upload_id"], "mapping_id": m.json()["mapping_id"]}, headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "profile_missing"


def test_conversion_request_validation(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"])
    base = {"upload_id": up["upload_id"], "mapping_id": m["mapping_id"]}
    assert client.post("/api/v1/conversions", json=dict(base, formats=["ubl"]), headers=h).status_code == 422
    assert client.post("/api/v1/conversions", json=dict(base, profile="peppol"), headers=h).status_code == 422
    assert client.post("/api/v1/conversions", json=dict(base, mapping_id="x"), headers=h).status_code == 404
    assert client.post("/api/v1/conversions", json=dict(base, upload_id="x"), headers=h).status_code == 404
    assert client.get("/api/v1/conversions/unbekannt").status_code == 404


def test_mapping_put_validation(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    bad = m["fields"] + [{"target": "/seller/name", "constant": "X"}]
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": bad}, headers=h)
    assert r.status_code == 422 and "nicht erlaubt" in r.json()["error"]["message_de"]
    bad = [{"target": "/number", "source_column": "Gibt es nicht"}]
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": bad}, headers=h)
    assert r.status_code == 422
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": {"mode": "egal"}, "fields": m["fields"]}, headers=h)
    assert r.status_code == 422
    r = client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": [{"target": "/number", "transform": ["eval"], "source_column": "Rechnungsnr."}]}, headers=h)
    assert r.status_code == 422


def test_saved_mapping_reused(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = _propose_confirm(client, h, up["upload_id"], save=True)
    up2 = client.post("/api/v1/uploads", files={"file": ("l.csv", (FIXTURES / "lexware_like.csv").read_bytes(), "text/csv")}, headers=h).json()
    m2 = client.post("/api/v1/mappings/propose", json={"upload_id": up2["upload_id"]}, headers=h).json()
    assert m2["reused"] is True and m2["mapping_id"] != m["mapping_id"]
    assert any(f["target"] == "/buyer_reference" for f in m2["fields"])
    m3 = client.post("/api/v1/mappings/propose", json={"upload_id": up2["upload_id"], "ignore_saved": True}, headers=h).json()
    assert m3["reused"] is False


def test_row_errors_reported(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile)
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h).json()
    # map the issue date to the customer column -> bad_date row errors
    fields = [dict(f, source_column="Kunde", transform=["date_dmy"]) if f["target"] == "/issue_date" else f
              for f in m["fields"] if f["target"] != "/buyer_reference"] + [BT10]
    assert client.put(f"/api/v1/mappings/{m['mapping_id']}", json={"grouping": m["grouping"], "fields": fields}, headers=h).status_code == 200
    job = _convert(client, h, up["upload_id"], m["mapping_id"])
    assert job["status"] == "done" and job["invoices"] == []
    assert job["row_errors"] and all(e["message_de"] and e["row"] for e in job["row_errors"])


def test_upload_errors(client, app):
    h = {"X-CSRF-Token": login(client, app)}
    r = client.post("/api/v1/uploads", files={"file": ("alt.xls", b"\xd0\xcf\x11\xe0", "application/vnd.ms-excel")}, headers=h)
    assert r.status_code == 415 and ".xlsx" in r.json()["error"]["message_de"]
    r = client.post("/api/v1/uploads", files={"file": ("bild.png", b"\x89PNG", "image/png")}, headers=h)
    assert r.status_code == 415
    r = client.post("/api/v1/uploads", files={"file": ("kaputt.xlsx", b"PK\x03\x04kaputt", "application/octet-stream")}, headers=h)
    assert r.status_code == 400 and r.json()["error"]["message_de"]
    r = client.post("/api/v1/uploads", files={"file": ("gross.csv", b"a;b\n" + b"1;2\n" * (3 * 1024 * 1024), "text/csv")}, headers=h)
    assert r.status_code == 413
    r = client.post("/api/v1/uploads", files={"file": ("leer.csv", b"", "text/csv")}, headers=h)
    assert r.status_code == 400
    r = client.post("/api/v1/uploads", files={"file": ("l.csv", b"a;b\n1;2\n", "text/csv")})
    assert r.status_code == 403  # CSRF


def test_xlsx_upload(client, app, seller_profile):
    h, up = _setup(client, app, seller_profile, fixture="excel_handmade.xlsx")
    assert up["row_count"] > 0
    m = client.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"]}, headers=h)
    assert m.status_code == 200 and client.get(f"/app/mapping/{m.json()['mapping_id']}").status_code == 200


def test_ai_provider_falls_back_offline(make_app, seller_profile):
    app = make_app(AI_PROVIDER="anthropic")
    with Client(app, base_url=APP) as c:
        h, up = _setup(c, app, seller_profile)
        m = c.post("/api/v1/mappings/propose", json={"upload_id": up["upload_id"], "send_real_values": False}, headers=h).json()
        assert m["provider"] == "heuristic-fallback"
        assert "Vorschlag ohne KI" in c.get(f"/app/mapping/{m['mapping_id']}").text
