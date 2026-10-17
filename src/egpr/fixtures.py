"""Controlled algorithm instances, not FoodPath or real-user observations."""
from fractions import Fraction as F
import random

from .schema import Belief, Condition, Plan, Query, State


def instance(plan_count: int, condition_count: int, sharing: float, seed: int,
             *, preferences: bool = True, correlated: bool = False):
    rng = random.Random(f"{plan_count}:{condition_count}:{sharing}:{seed}:{preferences}:{correlated}")
    ids = tuple(f"c{i}" for i in range(condition_count))
    cs = tuple(Condition(cid, "synthetic-household", "Boolean fixture " + cid) for cid in ids)
    worlds = tuple(range(1 << condition_count))
    weights = tuple(5 if correlated and ((w & 1) == ((w >> 1) & 1)) else 1 for w in worlds)
    belief = Belief(ids, worlds, weights)
    plans = [Plan("p000", ("already-supported-option",), ("food",), (), reward=F(1, 5))]
    for i in range(1, plan_count):
        width = rng.choice([1, 1, 2, min(3, condition_count)])
        chosen = set(rng.sample(ids, width))
        if rng.random() < sharing:
            chosen.discard(sorted(chosen)[0])
            chosen.add(ids[0])
        requirements = tuple((cid, rng.choice([True, True, False])) for cid in sorted(chosen))
        bonuses = ((rng.choice(ids), F(rng.choice([-2, 2, 4]), 5)),) if preferences else ()
        plans.append(Plan(f"p{i:03d}", (f"fixture-service-{i}",), ("food",), requirements,
                          reward=F(rng.randint(3, 10), 5), bonuses=bonuses))
    state = State(cs, tuple(plans), belief)
    queries = tuple(Query(f"q{i:02d}", cid, kind="VERIFY_SOURCE" if i % 3 == 0 else "ASK_USER",
                          cost=F(1 + i % 3, 50), resolution_probability=F(4, 5))
                    for i, cid in enumerate(ids))
    sets = [set(dict(p.requirements)) for p in plans[1:]]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    actual = sum(bool(a & b) for a, b in pairs) / len(pairs) if pairs else 0
    # Fixed public collection policy: reveal the first two named fields, never
    # select collection actions by EGPR scores or test outcomes.
    hidden_world = rng.choices(worlds, weights=weights, k=1)[0]
    states = [state]
    for i in range(min(2, condition_count)):
        state = state.observe_query(queries[i], bool(hidden_world & (1 << i)))
        states.append(state)
    return states, queries, {"requested_anchor_reuse": sharing,
                            "realized_pairwise_hard_constraint_overlap": actual,
                            "preferences": preferences, "correlated": correlated}
