from dataclasses import replace
from fractions import Fraction as F
import itertools
import random

import pytest

from egpr.schema import Belief, Condition, Evidence, Plan, Query, State, outcomes
from egpr.solver import BoundIndex, Controller, Evaluator, guard, horizon_value, revise


def example(n=2, plans=None, worlds=None, weights=None):
    cs = tuple(Condition(f"c{i}", "person:a", f"condition {i}") for i in range(n))
    worlds = tuple(range(2**n)) if worlds is None else worlds
    belief = Belief(tuple(c.condition_id for c in cs), worlds, weights or (1,) * len(worlds))
    plans = plans if plans is not None else (Plan("p", ("meal",), ("food",), (("c0", True),)),)
    return State(cs, plans, belief)


def queries(n=2, cost=F(1, 20), resolution=F(1)):
    return tuple(Query(f"q{i}", f"c{i}", cost=cost, resolution_probability=resolution) for i in range(n))


def test_unknown_negative_conflict_and_scopes():
    s = example()
    assert s.status("c0") == "unknown"
    s = s.observe("c0", False, source_id="user")
    assert s.status("c0") == "refuted"
    s = s.observe("c0", True, source_id="document")
    assert s.facts["c0"] == (None, True)
    assert not guard(s, "p")["allowed"]
    s = s.retract(next(e.evidence_id for e in s.evidence if e.source_id == "user"))
    assert guard(s, "p")["allowed"]
    with pytest.raises(ValueError, match="scope"):
        replace(s, evidence=(replace(s.evidence[0], subject_scope="person:b"),))
    with pytest.raises(ValueError, match="Boolean"):
        s.observe("c0", [], source_id="user")


def test_corrections_replace_only_same_source_and_reset_posterior():
    s = example().observe("c0", True, source_id="user")
    s = s.observe("c0", False, source_id="user", source_version="v2")
    assert len(s.evidence) == 1 and s.belief.probabilities["c0"] == 0
    s = s.observe("c0", True, source_id="other")
    assert s.belief.probabilities["c0"] == F(1, 2)


def test_truth_probability_one_is_not_public_evidence():
    s = example(1, worlds=(1,), weights=(1,))
    assert s.belief.probabilities["c0"] == 1
    assert not guard(s, "p")["allowed"]
    assert Evaluator().terminal(s) == (0, None)
    decision = Controller().decide(s, queries(1))
    assert decision.selected == "q0"  # Same plan ID, but evidence changes admissibility.
    assert guard(s.observe_query(queries(1)[0], True), "p")["allowed"]


def test_full_need_coverage_and_cross_service_constraints():
    p = Plan("joint", ("meal", "bus"), ("food", "transport"), (("c0", True), ("c1", True)))
    s = replace(example(plans=(p,)), required_needs=("food", "transport"))
    s = s.observe("c0", True, source_id="meal-source")
    assert guard(s, "joint")["unresolved"] == ["c1"]
    assert not guard(s, "joint")["allowed"]
    s = s.observe("c1", True, source_id="connection-source")
    assert guard(s, "joint")["allowed"]
    partial = replace(p, covered_needs=("food",))
    assert not guard(s.replace_candidates((partial,)), "joint")["allowed"]


def test_ties_are_retained_exactly():
    s = example(2, plans=tuple(Plan(f"p{i}", ("meal",), ("food",), ((f"c{i}", True),)) for i in range(2)))
    d = Controller().decide(s, queries())
    assert d.selected == "q0" and not d.certificates
    no_plans = example(1, plans=())
    d = Controller().decide(no_plans, queries(1, cost=0))
    assert d.selected == "STOP" and not d.certificates


def test_correlated_belief_updates_indirect_preference_dependencies():
    p = Plan("meal", ("meal",), ("food",), (), reward=F(1, 4), bonuses=(("c1", F(1)),))
    s = example(plans=(p,), worlds=(0, 3), weights=(1, 1))
    e = Evaluator(cache=True)
    assert e.terminal(s)[0] == F(3, 4)
    new = s.observe("c0", True, source_id="user")
    assert e.terminal(new)[0] == F(5, 4)
    assert e.terminal(new) == Evaluator().terminal(new)
    assert revise(s, new).affected_plans == ("meal",)
    assert new.status("c1") == "unknown"  # Inference alone is not provenance.


def test_complementarity_is_not_a_multistep_guarantee():
    p = Plan("p", ("meal",), ("food",), (("c0", True), ("c1", True)))
    s = example(plans=(p,))
    qs = queries()
    assert Controller().decide(s, qs).selected == "STOP"
    value, selected = horizon_value(s, qs, 2)
    assert selected == "q0" and value == F(7, 40)
    with pytest.raises(ValueError):
        horizon_value(s, qs, 4)


def test_untrusted_models_never_authorize_pruning():
    s = example()
    d = Controller().decide(s, (replace(queries()[0], trusted_model=False),))
    assert d.fallback == "observation_model_unavailable" and not d.certificates
    d = Controller().decide(replace(s, structure_trusted=False), queries())
    assert d.fallback == "uncertified_structure_full_voi" and not d.certificates
    impossible = example(1, worlds=(0,)).observe("c0", True, source_id="user")
    d = Controller().decide(impossible, queries(1))
    assert not d.exact_selection and not d.certificates


def test_versioned_certificates_and_query_models_expire():
    s, qs = example(), queries()
    d = Controller().decide(s, qs)
    cert = next(c for c in d.certificates if c.query_id == "q1")
    assert cert.valid(s, qs)
    changes = [replace(s, source_snapshot="new"), replace(s, utility_version=1),
               s.replace_candidates(s.plans), s.observe("c0", True, source_id="user")]
    for new in changes:
        assert not cert.valid(new, qs)
        assert "q1" in revise(s, new, (cert,)).invalidated_certificates
    assert not cert.valid(s, (replace(qs[0], cost=F(1)), qs[1]))


def test_unknown_dependency_falls_back_to_full_recompute():
    s = replace(example(), dependencies_complete=False)
    c = Controller()
    d = c.decide(s, queries())
    assert not d.certificates and not d.work.cache_hits
    assert revise(s, s.observe("c0", True, source_id="u")).full_recompute


def test_budget_is_not_a_certificate_of_optimality():
    p = Plan("p", ("meal",), ("food",), (), bonuses=(("c1", F(1)),))
    s = example(plans=(p,))
    d = Controller().decide(s, queries(), branch_budget=0)
    assert d.fallback == "counterfactual_budget_exhausted"
    assert not d.exact_selection and d.work.branch_evaluations == 0


@pytest.mark.parametrize("seed", [13, 37, 73, 101, 137])
def test_exhaustive_bounds_cache_and_action_agreement(seed):
    rng = random.Random(seed)
    n = 3
    ps = tuple(Plan(f"p{i}", ("meal",), ("food",),
                    tuple((f"c{j}", rng.choice([True, False])) for j in rng.sample(range(n), rng.randrange(n + 1))),
                    reward=F(rng.randint(1, 10), 10),
                    bonuses=((f"c{rng.randrange(n)}", F(rng.randint(-3, 5), 10)),)) for i in range(7))
    # Non-product masses exercise correlated posterior updates.
    s0 = example(n, plans=ps, weights=tuple(rng.randint(1, 9) for _ in range(2**n)))
    qs = queries(n, resolution=F(4, 5))
    cached = Evaluator(cache=True)
    for assignments in itertools.product([None, False, True], repeat=n):
        s = s0
        for i, answer in enumerate(assignments):
            if answer is not None:
                s = s.observe(f"c{i}", answer, source_id="user")
        exact = Evaluator()
        base = exact.terminal(s)[0]
        assert cached.terminal(s) == exact.terminal(s)
        ix = BoundIndex(s, Evaluator())
        oracle = {"STOP": F(0)}
        for q in qs:
            if s.status(q.condition_id) != "unknown":
                continue
            value = exact.q_value(s, q, base)
            oracle[q.query_id] = value
            bound = ix.bounds(q, base)
            assert bound.lower <= value <= bound.upper
        choices = []
        for policy in ("B1", "B2", "B3", "A1", "P"):
            d = Controller(policy).decide(s, qs)
            choices.append(d.selected)
            assert oracle[d.selected] == max(oracle.values())
            for cert in d.certificates:
                assert cert.valid(s, qs)
                assert oracle[cert.query_id] < oracle[cert.comparator]
        assert len(set(choices)) == 1


def test_conflicted_preference_bound_does_not_assume_resolution():
    p = Plan("p", ("meal",), ("food",), (), bonuses=(("c0", F(1)),))
    s = example(1, plans=(p,)).observe("c0", True, source_id="a").observe("c0", False, source_id="b")
    q = queries(1)[0]
    e = Evaluator()
    bound = BoundIndex(s, e).bounds(q, e.terminal(s)[0])
    assert bound.lower <= e.q_value(s, q) <= bound.upper
