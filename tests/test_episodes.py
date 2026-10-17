from dataclasses import replace
from fractions import Fraction as F

import pytest

from egpr.episodes import ControlledEnvironment, EpisodeBudget, run_episode
from egpr.mas import diagnostic_cases
from egpr.schema import Plan, Query


def setup():
    state = dict(diagnostic_cases())["missing_evidence"]
    qs = (Query("ask-a", "eligible_a", cost=F(1, 20)), Query("ask-b", "eligible_b", cost=F(1, 20)))
    truth = {"eligible_a": True, "eligible_b": False, "connection": True}
    return state, qs, truth


@pytest.mark.parametrize("policy", ["B1", "B2", "B3", "A1", "P"])
def test_sequential_query_revision_and_guard(policy):
    state, qs, truth = setup()
    result = run_episode(state, qs, ControlledEnvironment(truth), policy=policy)
    assert result["score"] == {"truth_correct": True, "supported_completion": True}
    assert result["information_actions"] == 1
    observation = next(a for a in result["actions"] if a["kind"] == "ASK_USER")
    assert observation["revision"]["affected_plans"] == ("pantry_a",)
    if policy in {"P", "A1", "B3"}:
        assert observation["revision"]["invalidated_certificates"]


def test_unresolved_answer_is_not_repeated_forever_or_treated_as_false():
    state, qs, truth = setup()
    result = run_episode(state, qs, ControlledEnvironment(truth, unresolved={"ask-a"}),
                         budget=EpisodeBudget(search_actions=0))
    assert result["information_actions"] == 1 and not result["score"]["supported_completion"]
    assert result["final_state"].facts["eligible_a"] == (None, False)


def test_search_revision_invalidates_old_pool_and_enables_new_supported_plan():
    state, qs, truth = setup()
    state = state.replace_candidates(())
    public_alternative = Plan("walk-in", ("open-meal",), ("food",), (), F(1))
    result = run_episode(state, qs, ControlledEnvironment(truth, search_batches=[(public_alternative,)]))
    assert result["delivered_plan_id"] == "walk-in" and result["search_actions"] == 1
    action = next(a for a in result["actions"] if a["kind"] == "SEARCH_OR_REVISE")
    assert action["revision"]["full_recompute"]


def test_budgets_and_adversarial_finalizer_cannot_force_unsupported_commit():
    state, qs, truth = setup()
    result = run_episode(state, qs, ControlledEnvironment(truth),
        budget=EpisodeBudget(information_actions=0), finalizer=lambda _: "pantry_a")
    assert result["termination"] == "information_budget_exhausted"
    assert result["rejected_final_proposals"] == 1 and result["delivered_plan_id"] is None
    result = run_episode(state, qs, ControlledEnvironment(truth), budget=EpisodeBudget(counterfactual_branches=0), policy="B2")
    assert result["counterfactual_branches"] == 0
    assert result["termination"] == "counterfactual_budget_exhausted"
    assert not result["actions"][0]["decision"]["exact_selection"]


def test_untrusted_observation_model_does_not_trigger_hidden_oracle_fallback():
    state, qs, truth = setup()
    qs = tuple(replace(q, trusted_model=False) for q in qs)
    result = run_episode(state, qs, ControlledEnvironment(truth))
    assert result["termination"] == "observation_model_unavailable"
    assert result["information_actions"] == 0 and not result["score"]["supported_completion"]
