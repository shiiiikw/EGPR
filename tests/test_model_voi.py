from dataclasses import replace
from fractions import Fraction as F
import itertools

import pytest

from egpr.fixtures import instance
from egpr.model_voi import GuardedModelEvaluator
from egpr.schema import Plan, Query
from egpr.solver import Controller, Evaluator, POLICIES


class FallibleRoles:
    requests = []
    def recommend(self, state):
        valid = [p for p in state.plans if Evaluator().plan_value(state, p) is not None]
        # A fixed mapping can select a suboptimal supported plan or fail entirely.
        selected = (valid[int(state.fingerprint[0], 16) % len(valid)].plan_id
                    if valid and int(state.fingerprint[1], 16) % 3 else None)
        return {"delivered_plan_id": selected, "request_hashes": []}


def evaluator(policy="P"):
    return GuardedModelEvaluator(FallibleRoles, cache=POLICIES[policy][1],
                                 value_model_fingerprint="fixed-fallible-fixture-v1")


def test_bounds_cover_fallible_terminal_values_and_policies_agree():
    states, qs, _ = instance(8, 4, .5, 13, preferences=False, correlated=True)
    for answers in itertools.product([None, False, True], repeat=3):
        s = states[0]
        for i, answer in enumerate(answers):
            if answer is not None:
                s = s.observe(f"c{i}", answer, source_id="public")
        e = evaluator("B2")
        base = e.terminal(s)[0]
        index = e.bound_index(s)
        values = {"STOP": F(0)}
        for q in qs:
            if s.status(q.condition_id) == "unknown":
                value = e.q_value(s, q, base)
                bounds = index.bounds(q, base)
                assert bounds.lower <= value <= bounds.upper
                values[q.query_id] = value
        choices = []
        for policy in POLICIES:
            ev = evaluator(policy)
            decision = Controller(policy, evaluator=ev).decide(s, qs)
            choices.append(decision.selected)
            for cert in decision.certificates:
                assert cert.valid(s, qs, value_model_fingerprint=ev.value_model_fingerprint)
                assert not cert.valid(s, qs)  # Not a certificate for another evaluator/model.
                assert values[cert.query_id] < values[cert.comparator]
        assert len(set(choices)) == 1


def test_positive_oracle_lower_bound_is_not_transferred_to_llm():
    states, qs, _ = instance(8, 4, .5, 13, preferences=False)
    s = states[0]
    ev = evaluator()
    base = ev.terminal(s)[0]
    iv = ev.bound_index(s).bounds(qs[0], base)
    assert all(lo == 0 for _, _, lo, _ in iv.branches)
    assert iv.lower == -base - qs[0].cost


def test_common_cache_policy_and_supported_reward_domain_are_enforced():
    with pytest.raises(ValueError, match="cache"):
        Controller("B1", evaluator=evaluator("P"))
    states, _, _ = instance(8, 4, .5, 13, preferences=True)
    with pytest.raises(ValueError, match="fixed rewards"):
        evaluator().terminal(states[0])
