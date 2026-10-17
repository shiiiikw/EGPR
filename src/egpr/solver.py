"""Exact one-step VOI, ordinary dependency caching and certified interval search.

B3 and P intentionally use the same generic interval search in v0. This code
does not claim a new branch-and-bound algorithm. All strict comparisons use
rational arithmetic; statistical or heuristic scores never authorize pruning.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from fractions import Fraction as F
from typing import Any

from .schema import Plan, Query, State, digest, outcomes


@dataclass
class Work:
    terminal_evaluations: int = 0
    branch_evaluations: int = 0
    plan_evaluations: int = 0
    constraint_checks: int = 0
    cache_lookups: int = 0
    cache_hits: int = 0
    bound_plan_visits: int = 0
    bound_branches: int = 0
    posterior_updates: int = 0
    certificates: int = 0


@dataclass(frozen=True)
class PlanStatus:
    blocked: bool
    missing: tuple[str, ...]


class Evaluator:
    def __init__(self, cache: bool = False):
        self.cache = cache
        self.work = Work()
        self._statuses: dict[tuple, PlanStatus] = {}
        self._values: dict[tuple, F] = {}

    def _key(self, state: State, plan: Plan):
        return (plan, state.required_needs, state.source_snapshot,
                state.candidate_pool_version, state.utility_version,
                tuple((state.condition_map[cid], state.condition_token(cid)) for cid, _ in plan.requirements))

    def status(self, state: State, plan: Plan) -> PlanStatus:
        use_cache = self.cache and state.dependencies_complete
        key = self._key(state, plan) if use_cache else None
        if use_cache:
            self.work.cache_lookups += 1
            if key in self._statuses:
                self.work.cache_hits += 1
                return self._statuses[key]
        self.work.constraint_checks += len(plan.requirements)
        missing = []
        blocked = not set(state.required_needs).issubset(plan.covered_needs)
        for cid, required in plan.requirements:
            value, conflict = state.facts[cid]
            blocked |= conflict or (value is not None and value != required)
            if value is None:
                missing.append(cid)
        result = PlanStatus(blocked, tuple(missing))
        if use_cache:
            self._statuses[key] = result
        return result

    def plan_value(self, state: State, plan: Plan) -> F | None:
        status = self.status(state, plan)
        if status.blocked or status.missing:
            return None
        if plan.bonuses and state.belief is None:
            raise ValueError("Cannot compute expected preference utility without a valid belief")
        # Exact marginal signatures act as scoped belief versions. A correlated
        # observation invalidates every changed preference projection, even when
        # the observed field is absent from that plan's direct constraints.
        probabilities = tuple((cid, state.belief.probabilities[cid]) for cid, _ in plan.bonuses)
        use_cache = self.cache and state.dependencies_complete
        key = (self._key(state, plan), probabilities) if use_cache else None
        if use_cache:
            self.work.cache_lookups += 1
            if key in self._values:
                self.work.cache_hits += 1
                return self._values[key]
        self.work.plan_evaluations += 1
        value = plan.reward + sum((bonus * p for (_, bonus), (_, p) in zip(plan.bonuses, probabilities)), F(0))
        if use_cache:
            self._values[key] = value
        return value

    def terminal(self, state: State) -> tuple[F, str | None]:
        self.work.terminal_evaluations += 1
        best_value, best_id = F(0), None
        for plan in sorted(state.plans, key=lambda p: p.plan_id):
            value = self.plan_value(state, plan)
            if value is not None and (value > best_value or (value == best_value and best_id is None)):
                best_value, best_id = value, plan.plan_id
        return best_value, best_id

    def q_value(self, state: State, query: Query, base: F | None = None) -> F:
        return self.evaluate_query(state, query, base)[0]

    def evaluate_query(self, state: State, query: Query, base: F | None = None):
        if base is None:
            base = self.terminal(state)[0]
        total = F(0)
        witness = []
        for observation, probability in outcomes(state, query):
            self.work.branch_evaluations += 1
            self.work.posterior_updates += 1
            child = state.observe_query(query, observation)
            value = self.terminal(child)[0]
            total += probability * value
            witness.append((observation, probability, value, value))
        return total - base - query.cost, tuple(witness)


@dataclass(frozen=True)
class Interval:
    lower: F
    upper: F
    # Witness tuples: observation, probability, terminal lower, terminal upper.
    branches: tuple[tuple[bool | None, F, F, F], ...] = ()


class BoundIndex:
    """One structural pass shared by queries. No counterfactual planner calls.

Only already admissible plans and plans with precisely one missing condition
can become supported after a one-field query. Conflicted plans cannot become
supported just because a third source repeats one side of a disagreement.
"""
    def __init__(self, state: State, evaluator: Evaluator):
        self.state = state
        self.evaluator = evaluator
        self.supported: list[Plan] = []
        self.pending: dict[str, list[Plan]] = {}
        for p in state.plans:
            evaluator.work.bound_plan_visits += 1
            status = evaluator.status(state, p)
            if status.blocked:
                continue
            if not status.missing:
                self.supported.append(p)
            elif len(status.missing) == 1:
                self.pending.setdefault(status.missing[0], []).append(p)

    def bounds(self, query: Query, base: F) -> Interval:
        if self.state.status(query.condition_id) != "unknown":
            raise ValueError("Only unresolved queries are candidates for screening")
        branches = []
        for answer, probability in outcomes(self.state, query):
            self.evaluator.work.bound_branches += 1
            candidates = list(self.supported)
            if answer is not None:
                candidates += [p for p in self.pending.get(query.condition_id, ())
                               if dict(p.requirements)[query.condition_id] == answer]
            lo = hi = F(0)
            for p in candidates:
                self.evaluator.work.bound_plan_visits += 1
                pl = pu = p.reward
                for cid, bonus in p.bonuses:
                    observed = (answer if cid == query.condition_id and not self.state.facts[cid][1]
                                else self.state.facts[cid][0])
                    if observed is None:
                        pl += min(F(0), bonus)
                        pu += max(F(0), bonus)
                    else:
                        pl += bonus * observed
                        pu += bonus * observed
                lo, hi = max(lo, pl), max(hi, pu)
            branches.append((answer, probability, lo, hi))
        lower = sum((p * lo for _, p, lo, _ in branches), F(0)) - base - query.cost
        upper = sum((p * hi for _, p, _, hi in branches), F(0)) - base - query.cost
        return Interval(lower, upper, tuple(branches))


@dataclass(frozen=True)
class Certificate:
    query_id: str
    lower_bound: F
    upper_bound: F
    comparator: str
    comparator_lower: F
    state_fingerprint: str
    query_set_fingerprint: str
    witness: tuple
    proof_mode: str = "exact_modeled"
    assumptions: tuple[str, ...] = (
        "finite fixed candidate pool; trusted scoped constraints",
        "declared joint prior and truthful-or-unresolved observation model",
        "one-step VOI only; evidence required for unconditional delivery",
        "rational comparisons; equal bounds retained",
    )
    expiry_rule: str = "any public state, source, utility, candidate or query-model change"

    def valid(self, state: State, queries: tuple[Query, ...]) -> bool:
        return (self.proof_mode == "exact_modeled" and state.structure_trusted
                and self.state_fingerprint == state.fingerprint
                and self.query_set_fingerprint == digest(queries)
                and self.upper_bound < self.comparator_lower)


@dataclass
class Decision:
    selected: str  # STOP is the best currently admissible terminal response.
    intervals: dict[str, Interval]
    certificates: list[Certificate]
    work: Work
    fallback: str | None = None
    exact_selection: bool = True


POLICIES = {
    "B1": (False, False), "B2": (False, True),
    "A1": (True, False), "P": (True, True), "B3": (True, True),
}


class Controller:
    def __init__(self, policy: str = "P"):
        if policy not in POLICIES:
            raise ValueError(f"Implemented policies: {tuple(POLICIES)}")
        self.policy = policy
        self.screen, cache = POLICIES[policy]
        self.evaluator = Evaluator(cache)

    def decide(self, state: State, queries: tuple[Query, ...], *, branch_budget: int | None = None) -> Decision:
        if len({q.query_id for q in queries}) != len(queries) or any(q.query_id == "STOP" for q in queries):
            raise ValueError("Queries need unique non-STOP IDs")
        if any(q.condition_id not in state.facts for q in queries):
            raise ValueError("Query refers to absent condition")
        if branch_budget is not None and branch_budget < 0:
            raise ValueError("Negative budget")
        before = asdict(self.evaluator.work)

        def finish(selected, intervals, certificates, fallback=None, exact=True):
            work = Work(**{k: v - before[k] for k, v in asdict(self.evaluator.work).items()})
            return Decision(selected, intervals, certificates, work, fallback, exact)

        active = {q.query_id: q for q in queries if state.status(q.condition_id) == "unknown"}
        if state.belief is None or any(not q.trusted_model for q in active.values()):
            # No invented probabilities and no hard pruning. The caller can run
            # an ordinary adaptive clarifier; this core exposes that fallback.
            return finish("STOP", {}, [], "observation_model_unavailable", False)
        base, _ = self.evaluator.terminal(state)
        intervals: dict[str, Interval] = {}
        certificates: list[Certificate] = []
        query_set_fingerprint = None
        evaluated: set[str] = set()
        removed: set[str] = set()
        screen = self.screen and state.structure_trusted and state.dependencies_complete
        fallback = None if screen or not self.screen else "uncertified_structure_full_voi"
        if screen:
            index = BoundIndex(state, self.evaluator)
            intervals = {qid: index.bounds(q, base) for qid, q in active.items()}

        def best_lower():
            # STOP wins ties, then the lexicographically first query. All arms
            # have exactly the same rule, including the unscreened oracle.
            options = [(F(0), "STOP")] + [(iv.lower, qid) for qid, iv in intervals.items() if qid not in removed]
            return min(options, key=lambda x: (-x[0], x[1] != "STOP", x[1]))

        while True:
            if screen:
                lower, comparator = best_lower()
                for qid in sorted(active):
                    iv = intervals[qid]
                    if qid not in removed and qid != comparator and iv.upper < lower:
                        if query_set_fingerprint is None:
                            query_set_fingerprint = digest(queries)
                        certificates.append(Certificate(qid, iv.lower, iv.upper, comparator, lower,
                            state.fingerprint, query_set_fingerprint, iv.branches))
                        self.evaluator.work.certificates += 1
                        removed.add(qid)
            pending = [qid for qid in active if qid not in removed and qid not in evaluated
                       and (not screen or intervals[qid].lower != intervals[qid].upper)]
            if not pending:
                break
            qid = min(pending, key=lambda x: (-intervals[x].upper, x)) if screen else min(pending)
            q = active[qid]
            required = len(outcomes(state, q))
            spent = self.evaluator.work.branch_evaluations - before["branch_evaluations"]
            if branch_budget is not None and spent + required > branch_budget:
                selected = best_lower()[1]
                return finish(selected, intervals, certificates, "counterfactual_budget_exhausted", False)
            value, witness = self.evaluator.evaluate_query(state, q, base)
            intervals[qid] = Interval(value, value, witness)
            evaluated.add(qid)
        return finish(best_lower()[1], intervals, certificates, fallback)


@dataclass(frozen=True)
class Revision:
    affected_conditions: tuple[str, ...]
    affected_plans: tuple[str, ...]
    invalidated_certificates: tuple[str, ...]
    reusable_plans: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    full_recompute: bool


def revise(old: State, new: State, certificates: tuple[Certificate, ...] = ()) -> Revision:
    changed = {cid for cid in old.facts.keys() | new.facts.keys()
               if cid not in old.facts or cid not in new.facts
               or old.condition_token(cid) != new.condition_token(cid)
               or old.facts[cid] != new.facts[cid]}
    global_change = (not old.dependencies_complete or not new.dependencies_complete
        or old.source_snapshot != new.source_snapshot
        or old.utility_version != new.utility_version
        or old.candidate_pool_version != new.candidate_pool_version
        or old.conditions != new.conditions or old.required_needs != new.required_needs)
    old_plans = {p.plan_id: p for p in old.plans}
    affected = set()
    for p in new.plans:
        depends = any(cid in changed for cid, _ in p.requirements)
        belief_changed = any(old.belief is None or new.belief is None
            or old.belief.probabilities.get(cid) != new.belief.probabilities.get(cid)
            for cid, _ in p.bonuses)
        if global_change or old_plans.get(p.plan_id) != p or depends or belief_changed:
            affected.add(p.plan_id)
    affected.update(old_plans.keys() - {p.plan_id for p in new.plans})
    invalid = tuple(c.query_id for c in certificates if c.state_fingerprint != new.fingerprint)
    return Revision(tuple(sorted(changed)), tuple(sorted(affected)), invalid,
                    tuple(sorted(p.plan_id for p in new.plans if p.plan_id not in affected)),
                    tuple(sorted(cid for cid, (value, _) in new.facts.items() if value is None)),
                    global_change)


def guard(state: State, plan_id: str) -> dict[str, Any]:
    plan = next((p for p in state.plans if p.plan_id == plan_id), None)
    if plan is None:
        return {"allowed": False, "reasons": ["unknown_plan"], "unresolved": []}
    reasons, unresolved = [], []
    if not set(state.required_needs).issubset(plan.covered_needs):
        reasons.append("incomplete_need_coverage")
    for cid, required in plan.requirements:
        value, conflict = state.facts[cid]
        if value is None or conflict:
            unresolved.append(cid)
            reasons.append("conflict:" + cid if conflict else "missing_evidence:" + cid)
        elif value != required:
            reasons.append("violated:" + cid)
    return {"allowed": not reasons, "reasons": reasons, "unresolved": sorted(set(unresolved))}


def horizon_value(state: State, queries: tuple[Query, ...], horizon: int) -> tuple[F, str]:
    """Small exhaustive multi-step reference; never called an oracle if capped."""
    if len(state.conditions) > 8 or len(queries) > 8 or not 0 <= horizon <= 3:
        raise ValueError("Exact horizon reference restricted to <=8 fields/queries and horizon<=3")
    evaluator = Evaluator()
    best, chosen = evaluator.terminal(state)[0], "STOP"
    if not horizon:
        return best, chosen
    for query in sorted(queries, key=lambda q: q.query_id):
        if state.status(query.condition_id) != "unknown":
            continue
        value = -query.cost
        for answer, p in outcomes(state, query):
            value += p * horizon_value(state.observe_query(query, answer), queries, horizon - 1)[0]
        if value > best:
            best, chosen = value, query.query_id
    return best, chosen
