from dataclasses import replace
from decimal import Decimal
import io
import json
import urllib.error

import pytest

from egpr.api import (ChatBackend, ENDPOINTS, ModelResponseError, Tariff, call_json,
                      load_credentials, parse_completion, payload)
from egpr.ledger import AccessBlocked, BudgetExceeded, Ledger, Receipt, Request


def request():
    return Request("openai", "frozen-model", ({"role": "user", "content": "JSON please"},),
                   generation=(("max_completion_tokens", 40),),
                   response_format={"type": "json_object"}, endpoint=ENDPOINTS["openai"])


class Response(io.BytesIO):
    status = 200
    headers = {"x-request-id": "req-test"}


def test_http_cache_survives_invalid_model_output_and_replicates_are_distinct(tmp_path):
    calls = []
    def opener(req, **kwargs):
        calls.append(json.loads(req.data))
        return Response(json.dumps({"model": "resolved-snapshot", "choices": [{
            "finish_reason": "length", "message": {"content": '{"partial":'}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 40}}).encode())
    backend = ChatBackend({"OPENAI_API_KEY": "fake-key"}, Tariff("1", "2"), opener=opener)
    ledger = Ledger(tmp_path / "calls.jsonl", allow_paid_calls=True, max_new_paid_usd="1")
    q = request()
    for _ in range(2):
        with pytest.raises(ModelResponseError):
            call_json(ledger, q, backend, maximum_usd="0.1")
    assert len(calls) == 1
    assert ledger.occupancy == Decimal("0.0001")
    received = next(r for r in ledger.rows if r["status"] == "received")
    assert received["billed_usd"] is None and received["usage"]["completion_tokens"] == 40
    assert "fake-key" not in ledger.path.read_text()
    assert replace(q, replicate_id="replicate-1").key != q.key
    assert replace(q, response_format={"type": "json_schema"}).key != q.key


def test_http_access_errors_are_retained_and_stop_campaign(tmp_path):
    def opener(req, **_):
        raise urllib.error.HTTPError(req.full_url, 429, "quota", {}, io.BytesIO(b'{"error":"quota"}'))
    ledger = Ledger(tmp_path / "calls.jsonl", allow_paid_calls=True, max_new_paid_usd="1")
    backend = ChatBackend({"OPENAI_API_KEY": "fake"}, Tariff("1", "2"), opener=opener)
    with pytest.raises(AccessBlocked):
        call_json(ledger, request(), backend, maximum_usd="0.2")
    assert ledger.occupancy == Decimal("0.2")  # No made-up zero bill on failure.
    assert any("quota" in r.get("response", {}).get("raw_body", "") for r in ledger.rows)
    with pytest.raises(AccessBlocked):
        ledger.run(replace(request(), model_snapshot="other"), lambda _: pytest.fail("no switch"),
                   paid=True, maximum_usd="0.2")


def test_usage_cost_cache_write_and_reasoning_are_not_double_counted():
    tariff = Tariff("0.1", "0.5", "0.01", "0.125", 272000, "2", "1.5")
    estimate, logical = tariff.estimate({"prompt_tokens": 2000, "completion_tokens": 100,
        "prompt_tokens_details": {"cached_tokens": 1000},
        "completion_tokens_details": {"reasoning_tokens": 80}})
    assert Decimal(estimate) == Decimal("0.000185")
    assert Decimal(logical) == Decimal("0.00025")
    assert Decimal(tariff.reserve(400000, 100)) >= Decimal(estimate)
    assert tariff.estimate({"prompt_tokens": 2, "completion_tokens": 1,
                            "prompt_tokens_details": {"cached_tokens": 3}}) == (None, None)
    assert tariff.estimate(None) == (None, None)


def test_fail_closed_request_and_json_validation():
    with pytest.raises(ValueError):
        payload(replace(request(), endpoint="https://unconfigured.example"))
    with pytest.raises(ValueError):
        payload(replace(request(), generation=(("model", "other"),)))
    for value in ['{"x":1,"x":2}', '{"x":NaN}', '[1]', 'not JSON']:
        envelope = {"http_status": 200, "raw_body": json.dumps({"choices": [
            {"finish_reason": "stop", "message": {"content": value}}]})}
        with pytest.raises(ModelResponseError):
            parse_completion(envelope)


def test_credentials_are_parsed_without_shell_execution(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = tmp_path / "keys"
    p.write_text("export OPENAI_API_KEY='literal-$(touch should-not-exist)'\nIGNORED_KEY=x\n")
    assert load_credentials(p)["OPENAI_API_KEY"] == "literal-$(touch should-not-exist)"
    assert "IGNORED_KEY" not in load_credentials(p)


def test_response_is_not_lost_on_cost_overrun_and_budget_is_finite(tmp_path):
    with pytest.raises(ValueError):
        Ledger(tmp_path / "bad", max_new_paid_usd="NaN")
    ledger = Ledger(tmp_path / "calls", allow_paid_calls=True, max_new_paid_usd="1")
    with pytest.raises(BudgetExceeded):
        ledger.run(request(), lambda _: Receipt({"valuable": 1}, "0.3"), paid=True, maximum_usd="0.2")
    assert ledger.occupancy == Decimal("0.3")
    assert ledger.run(request(), lambda _: pytest.fail("must reuse"), paid=True) == {"valuable": 1}


def test_two_instances_refresh_ledger_and_reject_concurrent_writers(tmp_path):
    a = Ledger(tmp_path / "calls", allow_paid_calls=True, max_new_paid_usd="1")
    b = Ledger(a.path, allow_paid_calls=True, max_new_paid_usd="1")
    a.run(request(), lambda _: Receipt({"ok": 1}, "0.1"), paid=True, maximum_usd="0.2")
    assert b.run(request(), lambda _: pytest.fail("must reload"), paid=True) == {"ok": 1}
    with a.locked():
        with pytest.raises(RuntimeError, match="Another process"):
            b.run(request(), lambda _: None, paid=True)
