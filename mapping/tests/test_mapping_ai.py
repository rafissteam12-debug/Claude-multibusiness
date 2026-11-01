from __future__ import annotations

import json
import logging
import os
from types import SimpleNamespace

import pytest

from mapping import apply, propose
from mapping import ai
from mapping.scoring import expected_for, score


class FakeClient:
    def __init__(self, reply: str | Exception):
        self.reply = reply
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


def _expected_as_reply(name: str) -> str:
    exp = expected_for(name)
    fields = [dict(f, confidence=0.9, reason_de="KI-Vorschlag") for f in exp["fields"]]
    return "```json\n" + json.dumps({"grouping": exp["grouping"], "fields": fields}, ensure_ascii=False) + "\n```"


def test_valid_ai_response_is_used(load, seller_profile):
    t = load("lexware_like.csv")
    client = FakeClient(_expected_as_reply("lexware_like.csv"))
    m = propose(t, seller_profile, provider="anthropic", client=client)
    assert m["provider"] == "anthropic"
    assert score(m, expected_for("lexware_like.csv"))["all_score"] == 1.0
    invoices, errors = apply(t, m, seller_profile)
    assert errors == [] and len(invoices) == 5


def test_only_value_shapes_are_sent_by_default(load, seller_profile, monkeypatch):
    monkeypatch.setenv("AI_MAX_SAMPLE_ROWS", "2")
    t = load("lexware_like.csv")
    client = FakeClient(_expected_as_reply("lexware_like.csv"))
    propose(t, seller_profile, provider="anthropic", client=client)
    user = json.loads(client.calls[0]["messages"][0]["content"])
    sent = json.dumps(user["sample_rows"], ensure_ascii=False)  # columns are allowed, cell values are not
    assert all(k in ("columns", "column_hints", "sample_rows", "sample_kind", "row_count", "seller_defaults") for k in user)
    hints = json.dumps(user["column_hints"], ensure_ascii=False)
    assert user["column_hints"]["Rechnungsdatum"] == "Werte sehen aus wie Datum (TT.MM.JJJJ)"
    for row in t.rows:
        for cell in row:
            if len(cell) > 2 and cell not in t.columns:
                assert f'"{cell}"' not in hints and f" {cell}" not in hints, cell
    assert user["columns"] == t.columns
    assert len(user["sample_rows"]) == 2
    assert user["sample_rows"][0][t.columns.index("Rechnungsdatum")] == "dd.dd.dddd"
    assert user["sample_rows"][0][t.columns.index("Kunde")] == "Xxxxxxxx Xxxxxxxxxxxx XxxX"
    for row in t.rows:
        for cell in row:
            if len(cell) > 2 and any(ch.isalnum() for ch in cell):
                assert cell not in sent, cell
    whole = json.dumps(client.calls[0], ensure_ascii=False)
    assert "DE89370400440532013000" not in whole and seller_profile["seller"]["name"] not in whole
    assert "Bäckerei" not in whole


def test_real_values_only_with_flag(load, seller_profile):
    t = load("lexware_like.csv")
    client = FakeClient(_expected_as_reply("lexware_like.csv"))
    propose(t, seller_profile, provider="anthropic", client=client, send_real_values=True)
    user = json.loads(client.calls[0]["messages"][0]["content"])
    assert user["sample_rows"][0][t.columns.index("Kunde")] == "Bäckerei Sonnenschein GmbH"
    assert user["sample_kind"] == "real values"


def test_model_is_configurable(load, seller_profile, monkeypatch):
    t = load("lexware_like.csv")
    monkeypatch.delenv("AI_MODEL", raising=False)
    client = FakeClient(_expected_as_reply("lexware_like.csv"))
    propose(t, seller_profile, provider="anthropic", client=client)
    assert client.calls[0]["model"] == ai.DEFAULT_MODEL
    monkeypatch.setenv("AI_MODEL", "claude-test-model")
    propose(t, seller_profile, provider="anthropic", client=client)
    assert client.calls[1]["model"] == "claude-test-model"


@pytest.mark.parametrize("reply", [
    "Ich denke, die Spalte Kunde ist der Käufer.",                     # no JSON
    '{"grouping": {"mode": "row_per_invoice"}}',                        # no fields list
    '[1, 2, 3]',                                                        # not an object
    TimeoutError("timeout"),
    RuntimeError("API down"),
])
def test_unusable_responses_fall_back_to_heuristic(reply, load, seller_profile, caplog):
    t = load("lexware_like.csv")
    with caplog.at_level(logging.DEBUG, logger="mapping.ai"):
        m = propose(t, seller_profile, provider="anthropic", client=FakeClient(reply))
    assert m["provider"] == "heuristic-fallback"
    assert score(m, expected_for("lexware_like.csv"))["required_score"] >= 0.8
    for rec in caplog.records:  # never log prompts or values
        assert "Bäckerei" not in rec.getMessage() and "Kunde" not in rec.getMessage()


@pytest.mark.parametrize("bad_field", [
    {"target": "/seller/name", "constant": "X"},                                   # seller field
    {"target": "/lines/*/gross", "source_column": "Brutto"},                       # unknown target
    {"target": "/number", "source_column": "Rechnungsnr.", "transform": ["magic"]},  # unknown transform
    {"target": "/number", "source_column": "Gibt es nicht"},                       # unknown column
    {"target": "/number", "source_column": "Kunde", "constant": "X"},              # both
    "kein Objekt",
])
def test_invalid_ai_fields_are_rejected_individually(bad_field, load, seller_profile, monkeypatch):
    monkeypatch.setenv("MAPPING_AI_DEBUG", "1")
    t = load("lexware_like.csv")
    heur = propose(t, seller_profile)
    reply = json.dumps({"grouping": {"mode": "sometimes"}, "fields": [bad_field]}, ensure_ascii=False)
    m = propose(t, seller_profile, provider="anthropic", client=FakeClient(reply))
    assert m["provider"] == "anthropic"
    assert [(f["target"], f.get("source_column"), f.get("constant")) for f in m["fields"]] == \
        [(f["target"], f.get("source_column"), f.get("constant")) for f in heur["fields"]]
    assert m["grouping"] == heur["grouping"]
    assert set(m["field_sources"].values()) == {"heuristic"}
    assert len(m["debug_ai"]["rejected"]) == 1


def test_ai_cannot_override_confident_heuristic(load, seller_profile, monkeypatch):
    monkeypatch.setenv("MAPPING_AI_DEBUG", "1")
    t = load("lexware_like.csv")
    wrong = [{"target": "/number", "source_column": "Kundennr.", "transform": [], "confidence": 0.99},
             {"target": "/lines/*/net_price", "source_column": "Netto", "transform": ["de_decimal"], "confidence": 0.99},
             {"target": "/buyer/company_id", "source_column": "Kunde", "transform": [], "confidence": 0.9}]  # column taken
    m = propose(t, seller_profile, provider="anthropic", client=FakeClient(json.dumps({"fields": wrong})))
    assert score(m, expected_for("lexware_like.csv"))["all_score"] == 1.0
    assert "/buyer/company_id" not in m["field_sources"]
    assert len(m["debug_ai"]["rejected"]) == 3


def test_ai_fills_gaps_and_weak_fields(csv_table, seller_profile):
    t = csv_table("Rechnungsnr;Datum;Kunde;Straße;PLZ;Ort;E-Mail;Info;Menge;Preis;Az.\n"
                  "R-1;01.10.2026;A GmbH;Weg 1;10115;Berlin;a@a.example;Wartung;1;10,00;AZ-77\n")
    heur = propose(t, seller_profile)
    hby = {f["target"]: f for f in heur["fields"]}
    assert hby["/lines/*/description"]["constant"] == "Leistung" and "/buyer_reference" not in hby
    ai_fields = [{"target": "/lines/*/description", "source_column": "Info", "transform": ["strip"], "confidence": 0.8},
                 {"target": "/buyer_reference", "source_column": "Az.", "transform": [], "confidence": 0.7}]
    m = propose(t, seller_profile, provider="anthropic", client=FakeClient(json.dumps({"fields": ai_fields})))
    by = {f["target"]: f for f in m["fields"]}
    assert by["/lines/*/description"] == {"target": "/lines/*/description", "source_column": "Info", "transform": [],
                                          "confidence": 0.8, "reason_de": "KI: Vorschlag der KI"}
    assert by["/buyer_reference"]["source_column"] == "Az."
    assert m["field_sources"]["/lines/*/description"] == "ai" and m["field_sources"]["/number"] == "heuristic"
    invoices, errors = apply(t, m, seller_profile)
    assert errors == [] and invoices[0]["buyer_reference"] == "AZ-77" and invoices[0]["lines"][0]["description"] == "Wartung"
    # unmapped_required is recomputed after the AI filled /buyer_reference
    assert "/buyer_reference" in heur["unmapped_required"] and "/buyer_reference" not in m["unmapped_required"]
    assert any(w["code"] == "no_delivery_date" for w in m["warnings"])


def test_quality_guard_drops_harmful_ai_fields(csv_table, seller_profile, monkeypatch):
    monkeypatch.setenv("MAPPING_AI_DEBUG", "1")
    t = csv_table("Rechnungsnr;Datum;Kunde;Straße;PLZ;Ort;E-Mail;Bezeichnung;Menge;Preis;Zahlweise\n"
                  "R-1;01.10.2026;A GmbH;Weg 1;10115;Berlin;a@a.example;Wartung;1;10,00;sofort\n")
    harmful = [{"target": "/payment/due_date", "source_column": "Zahlweise", "transform": ["date_dmy"], "confidence": 0.9}]
    m = propose(t, seller_profile, provider="anthropic", client=FakeClient(json.dumps({"fields": harmful})))
    assert "/payment/due_date" not in {f["target"] for f in m["fields"]}
    assert any("verschlechtern" in r["problem"] for r in m["debug_ai"]["rejected"])
    assert apply(t, m, seller_profile)[1] == []


def test_strip_everywhere_is_harmless(load, seller_profile):
    """Likely cause of the poor raw score in CI run 41255736670: 'strip' added to every field."""
    t = load("lexware_like.csv")
    exp = expected_for("lexware_like.csv")
    fields = [dict(f, transform=["strip"] + f["transform"]) if "source_column" in f else f for f in exp["fields"]]
    assert score({"grouping": exp["grouping"], "fields": fields}, exp)["all_score"] == 1.0
    m = propose(t, seller_profile, provider="anthropic", client=FakeClient(json.dumps({"grouping": exp["grouping"], "fields": fields})))
    assert score(m, exp)["all_score"] == 1.0


def test_debug_off_by_default(load, seller_profile, monkeypatch):
    monkeypatch.delenv("MAPPING_AI_DEBUG", raising=False)
    m = propose(load("lexware_like.csv"), seller_profile, provider="anthropic", client=FakeClient(_expected_as_reply("lexware_like.csv")))
    assert "debug_ai" not in m


def test_no_key_falls_back(load, seller_profile, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    m = propose(load("sevdesk_like.csv"), seller_profile, provider="anthropic")
    assert m["provider"] == "heuristic-fallback"


def test_missing_constants_completed_from_heuristic(load, seller_profile):
    t = load("no_vat_column.csv")
    exp = expected_for("no_vat_column.csv")
    fields = [dict(f, confidence=0.8, reason_de="KI") for f in exp["fields"] if "constant" not in f]
    m = propose(t, seller_profile, provider="anthropic",
                client=FakeClient(json.dumps({"grouping": exp["grouping"], "fields": fields})))
    assert m["provider"] == "anthropic"
    by = {f["target"]: f for f in m["fields"]}
    assert by["/lines/*/vat_rate"]["constant"] == "19"
    invoices, errors = apply(t, m, seller_profile)
    assert errors == [] and len(invoices) == 3


@pytest.mark.network
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_real_anthropic_call(load, seller_profile, monkeypatch, capsys):
    """Exactly ONE API call: the hybrid result and the raw AI answer come from the same response."""
    monkeypatch.setenv("MAPPING_AI_DEBUG", "1")
    name = "lexware_like.csv"
    t = load(name)
    exp = expected_for(name)
    heur_score = score(propose(t, seller_profile), exp)  # offline
    m = propose(t, seller_profile, provider="anthropic")  # the only network call
    raw = m.get("debug_ai") or {"grouping": None, "fields": [], "rejected": []}
    raw_score = score({"grouping": raw["grouping"] or {}, "fields": [f for f in raw["fields"] if "target" in f]}, exp)
    hybrid_score = score(m, exp)
    with capsys.disabled():  # visible in CI output even when the test passes
        print(f"\n[mapping-ai] model={m.get('model')} provider={m['provider']}")
        print(f"[mapping-ai] heuristic required={heur_score['required_score']:.0%} | raw AI required={raw_score['required_score']:.0%} "
              f"all={raw_score['all_score']:.0%} wrong={raw_score['all_wrong']} | hybrid required={hybrid_score['required_score']:.0%}")
        print("[mapping-ai] raw AI grouping: " + json.dumps(raw["grouping"], ensure_ascii=False))
        for f in raw["fields"]:
            print("[mapping-ai] raw AI field: " + json.dumps(f, ensure_ascii=False))
        for r in raw["rejected"]:
            print("[mapping-ai] rejected: " + json.dumps(r, ensure_ascii=False))
        print("[mapping-ai] field sources: " + json.dumps(m.get("field_sources"), ensure_ascii=False))
    assert m["provider"] == "anthropic", "real call fell back to the heuristic"
    assert hybrid_score["required_score"] >= heur_score["required_score"]
    assert hybrid_score["required_score"] >= 0.8
