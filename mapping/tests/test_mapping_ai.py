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
    assert all(k in ("columns", "sample_rows", "sample_kind", "row_count", "seller_defaults") for k in user)
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
    "Ich denke, die Spalte Kunde ist der Käufer.",                                    # no JSON
    '{"grouping": {"mode": "row_per_invoice"}, "fields": [{"target": "/seller/name", "constant": "X"}]}',  # seller field
    '{"grouping": {"mode": "row_per_invoice"}, "fields": [{"target": "/lines/*/gross", "source_column": "Brutto"}]}',  # unknown target
    '{"grouping": {"mode": "row_per_invoice"}, "fields": [{"target": "/number", "source_column": "Rechnungsnr.", "transform": ["magic"]}]}',
    '{"grouping": {"mode": "row_per_invoice"}, "fields": [{"target": "/number", "source_column": "Gibt es nicht"}]}',
    '{"grouping": {"mode": "sometimes"}, "fields": []}',
    TimeoutError("timeout"),
    RuntimeError("API down"),
])
def test_bad_responses_fall_back_to_heuristic(reply, load, seller_profile, caplog):
    t = load("lexware_like.csv")
    with caplog.at_level(logging.DEBUG, logger="mapping.ai"):
        m = propose(t, seller_profile, provider="anthropic", client=FakeClient(reply))
    assert m["provider"] == "heuristic-fallback"
    assert score(m, expected_for("lexware_like.csv"))["required_score"] >= 0.8
    for rec in caplog.records:  # never log prompts or values
        assert "Bäckerei" not in rec.getMessage() and "Kunde" not in rec.getMessage()


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
def test_real_anthropic_call(load, seller_profile):
    t = load("lexware_like.csv")
    m = propose(t, seller_profile, provider="anthropic")
    assert m["provider"] == "anthropic", "real call fell back to the heuristic"
    s = score(m, expected_for("lexware_like.csv"))
    print(f"anthropic score lexware_like: required {s['required_score']:.0%}, all {s['all_score']:.0%}")
    assert s["required_score"] >= 0.8
