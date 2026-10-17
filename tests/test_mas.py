import json

from egpr.api import Tariff
from egpr.ledger import Ledger, Receipt
from egpr.mas import ModelRoles, diagnostic_cases, public_view
from egpr.solver import Evaluator


MODEL = {"provider": "openai", "model": "mock", "context_tokens": 32,
         "generation": {"max_completion_tokens": 30}}


def response(value):
    return Receipt({"http_status": 200, "raw_body": json.dumps({"choices": [
        {"finish_reason": "stop", "message": {"content": json.dumps(value)}}]})})


def test_guard_rejects_consistent_multi_role_hallucination_and_recovery_is_bounded(tmp_path):
    state = dict(diagnostic_cases())["missing_evidence"]
    calls = []
    def backend(req):
        calls.append(req)
        if "role is Reviewer:" in req.messages[0]["content"]:
            return response({"valid": True, "issues": []})
        return response({"plan_id": "pantry_a", "reason": "Unsupported guess"})
    ledger = Ledger(tmp_path / "ledger", allow_paid_calls=True, max_new_paid_usd="1")
    roles = ModelRoles(ledger, MODEL, backend, Tariff("1", "1"))
    trace = roles.recommend(state)
    assert trace["delivered_plan_id"] is None
    assert trace["recovery"] and not trace["final_guard"]["allowed"]
    assert len(calls) == 4
    assert "checker_feedback" in calls[-1].messages[1]["content"]
    again = ModelRoles(ledger, MODEL, backend, Tariff("1", "1")).recommend(state)
    assert again == trace and len(calls) == 4


def test_successful_guard_recovery_retains_initial_failure(tmp_path):
    state = dict(diagnostic_cases())["supported"]
    def backend(req):
        system = req.messages[0]["content"]
        if "role is Reviewer:" in system:
            return response({"valid": False, "issues": ["unknown plan"]})
        plan = "pantry_a" if "repair the rejected" in system else "invented_plan"
        return response({"plan_id": plan, "reason": "test"})
    ledger = Ledger(tmp_path / "ledger", allow_paid_calls=True, max_new_paid_usd="1")
    trace = ModelRoles(ledger, MODEL, backend, Tariff("1", "1")).recommend(state)
    assert trace["delivered_plan_id"] == "pantry_a"
    assert not trace["initial_guard"]["allowed"] and trace["final_guard"]["allowed"]


def test_development_cases_cover_outcomes_and_no_hidden_world_enters_prompt():
    cases = diagnostic_cases()
    assert len(cases) == 8
    oracle = {name: Evaluator().terminal(s)[1] for name, s in cases}
    assert sum(p is not None for p in oracle.values()) == 3
    assert oracle["explicit_negative"] == "no_eligibility"
    for _, state in cases:
        assert not ({"prior", "worlds", "hidden_world", "expected_plan_id"} & set(public_view(state)))
