from fractions import Fraction as F

import pytest

from egpr.episodes import ControlledEnvironment, EpisodeBudget, run_episode
from egpr.model_voi import GuardedModelEvaluator
from egpr.schema import Belief, Condition, Plan, Query, State
from egpr.solver import Controller, POLICIES


def fixture():
    cs = (Condition("x", "person", "x"), Condition("y", "person", "y"))
    prior = Belief(("x", "y"), (0, 1, 2, 3), (1, 1, 1, 1))
    ps = (Plan("fallback", ("fallback",), ("food",), (), F(1, 5)),
          Plan("px", ("x-plan",), ("food",), (("x", True),)),
          Plan("py", ("y-plan",), ("food",), (("y", True),)))
    return State(cs, ps, prior), (Query("ask-x", "x"), Query("ask-y", "y"))


class FallibleRoles:
    def recommend(self, public_state):
        # This fixed model mapping overlooks px, even when px is admissible.
        selected = "py" if public_state.facts["y"] == (True, False) else "fallback"
        return {"delivered_plan_id": selected, "request_hashes": []}


@pytest.mark.parametrize("policy", tuple(POLICIES))
def test_sequential_controller_and_finalizer_use_the_fallible_model(policy):
    state, queries = fixture()
    assert Controller("B2").decide(state, queries).selected == "ask-x"
    ev = GuardedModelEvaluator(FallibleRoles, cache=POLICIES[policy][1], value_model_fingerprint="test-fallible-v1")
    result = run_episode(state, queries, ControlledEnvironment({"x": False, "y": True}),
                         policy=policy, evaluator=ev)
    actions = [a for a in result["actions"] if a["kind"] == "ASK_USER"]
    assert [a["query_id"] for a in actions] == ["ask-y"]
    assert result["delivered_plan_id"] == "py" and result["score"]["supported_completion"]
    assert result["finalization_work"]["terminal_evaluations"] == 1


def test_budget_termination_keeps_model_finalization_and_evidence_guard():
    state, queries = fixture()
    ev = GuardedModelEvaluator(FallibleRoles, cache=True, value_model_fingerprint="test-fallible-v1")
    result = run_episode(state, queries, ControlledEnvironment({"x": True, "y": True}),
                         policy="B2", evaluator=ev, budget=EpisodeBudget(counterfactual_branches=0))
    assert result["termination"] == "counterfactual_budget_exhausted"
    assert result["information_actions"] == 0 and result["delivered_plan_id"] == "fallback"
    assert result["final_state"].evidence == ()
