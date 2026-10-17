import json

import pytest

from egpr.api import Tariff
from egpr.ledger import Ledger, Receipt
from egpr.mas import ModelRoles, diagnostic_cases


def test_output_style_separates_cached_requests_without_removing_public_context(tmp_path):
    model = {"provider": "openai", "model": "mock", "context_tokens": 32,
             "generation": {"max_completion_tokens": 30}}
    state = dict(diagnostic_cases())["supported"]
    requests = []

    def backend(request):
        requests.append(request)
        value = ({"valid": True, "issues": []} if "role is Reviewer:" in request.messages[0]["content"]
                 else {"plan_id": "pantry_a", "reason": "Supported by scoped evidence."})
        return Receipt({"http_status": 200, "raw_body": json.dumps({"choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(value)}}]})})

    ledger = Ledger(tmp_path / "ledger", allow_paid_calls=True, max_new_paid_usd="1")
    default = ModelRoles(ledger, model, backend, Tariff("1", "1")).recommend(state)
    concise_model = {**model, "output_style": "concise-v1"}
    concise = ModelRoles(ledger, concise_model, backend, Tariff("1", "1")).recommend(state)
    assert default["delivered_plan_id"] == concise["delivered_plan_id"] == "pantry_a"
    assert len(requests) == 6
    for before, after in zip(requests[:3], requests[3:]):
        assert before.key != after.key
        assert before.messages[1] == after.messages[1]
        assert before.generation == after.generation
        assert before.response_format == after.response_format
    ModelRoles(ledger, concise_model, backend, Tariff("1", "1")).recommend(state)
    assert len(requests) == 6


def test_unknown_output_style_is_rejected_before_any_request():
    with pytest.raises(ValueError, match="output style"):
        ModelRoles(None, {"output_style": "unregistered-style"}, None, None)
