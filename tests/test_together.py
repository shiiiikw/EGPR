import json

import pytest

together = pytest.importorskip("together")
import httpx

from egpr.api import ENDPOINTS, Tariff, call_json
from egpr.ledger import AccessBlocked, Ledger, Request
from egpr.providers import TogetherBackend


def test_official_sdk_uses_identical_payload_without_hidden_retries(tmp_path):
    calls = []
    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "mock-request", "model": "mock", "choices": [
            {"finish_reason": "stop", "message": {"content": '{"ok":true}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
    client = together.Together(api_key="fake", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    backend = TogetherBackend({"TOGETHER_API_KEY": "fake"}, Tariff("1", "2"),
                              client=client, status_errors=(together.APIStatusError,))
    q = Request("together", "mock", ({"role": "user", "content": "JSON"},),
                generation=(("max_tokens", 100), ("reasoning", {"enabled": False})),
                response_format={"type": "json_object"}, endpoint=ENDPOINTS["together"])
    ledger = Ledger(tmp_path / "calls", allow_paid_calls=True, max_new_paid_usd="1")
    assert call_json(ledger, q, backend, maximum_usd="0.1") == {"ok": True}
    assert call_json(ledger, q, backend, maximum_usd="0.1") == {"ok": True}
    assert len(calls) == 1 and calls[0]["reasoning"] == {"enabled": False}
    assert calls[0]["max_tokens"] == 100 and not calls[0]["stream"]
    client.close()


def test_official_sdk_http_error_is_cached_before_raising(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(429, json={"error": {"message": "test quota", "type": "insufficient_quota"}})
    client = together.Together(api_key="fake", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    backend = TogetherBackend({"TOGETHER_API_KEY": "fake"}, Tariff("1", "2"),
                              client=client, status_errors=(together.APIStatusError,))
    ledger = Ledger(tmp_path / "calls", allow_paid_calls=True, max_new_paid_usd="1")
    q = Request("together", "mock", ({"role": "user", "content": "JSON"},),
                generation=(("max_tokens", 100),), endpoint=ENDPOINTS["together"])
    with pytest.raises(AccessBlocked):
        call_json(ledger, q, backend, maximum_usd="0.1")
    assert len(calls) == 1
    assert "test quota" in next(r for r in ledger.rows if r["status"] == "received")["response"]["raw_body"]
    client.close()


def test_request_pacing_applies_to_new_calls_but_not_cached_replay(tmp_path):
    from dataclasses import replace
    now, sleeps, starts = [100.0], [], []
    def sleep(delay):
        sleeps.append(delay)
        now[0] += delay
    def handle(request):
        starts.append(now[0])
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"content": '{"ok":true}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10}})
    client = together.Together(api_key="fake", max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    backend = TogetherBackend({"TOGETHER_API_KEY": "fake"}, Tariff("1", "2"), client=client,
        status_errors=(together.APIStatusError,), min_interval_seconds=2,
        monotonic=lambda: now[0], sleep=sleep)
    ledger = Ledger(tmp_path / "calls", allow_paid_calls=True, max_new_paid_usd="1")
    q = Request("together", "mock", ({"role": "user", "content": "JSON"},),
                generation=(("max_tokens", 100),), endpoint=ENDPOINTS["together"])
    call_json(ledger, q, backend, maximum_usd="0.1")
    call_json(ledger, q, backend, maximum_usd="0.1")
    call_json(ledger, replace(q, replicate_id="replicate-2"), backend, maximum_usd="0.1")
    assert starts == [100.0, 102.0] and sleeps == [2.0]
    client.close()
