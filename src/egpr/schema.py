"""Public state, scoped evidence and a finite, exact joint observation model.

The v0 domain is deliberately bounded: Boolean conditions, fixed candidate pools,
one-field Ask/Verify, and fixed reward plus optional Boolean preference bonuses.
Required conditions need public evidence, even when their posterior is one.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from fractions import Fraction as F
from functools import cached_property
import hashlib
import json
from typing import Literal


def canonical(value) -> str:
    def encode(obj):
        if isinstance(obj, F):
            return {"numerator": obj.numerator, "denominator": obj.denominator}
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        raise TypeError(type(obj).__name__)
    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Condition:
    condition_id: str
    subject_scope: str
    predicate: str


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    condition_id: str
    subject_scope: str
    source_id: str
    source_version: str
    source_span: str
    observed_value: bool | None
    retrieved_at: str = "controlled-fixture"
    valid_time_scope: str = "fixed-snapshot"

    def __post_init__(self):
        if self.observed_value is not None and type(self.observed_value) is not bool:
            raise ValueError("Use a Boolean or None; empty lists/strings are not negation")
        if not self.source_id or not self.source_span:
            raise ValueError("Evidence requires source identity and a traceable span")


@dataclass(frozen=True)
class Belief:
    """Joint world weights, not a product of inferred independent marginals."""
    condition_ids: tuple[str, ...]
    worlds: tuple[int, ...]
    weights: tuple[int, ...]

    def __post_init__(self):
        if len(set(self.condition_ids)) != len(self.condition_ids):
            raise ValueError("Duplicate condition ID")
        if not self.worlds or len(self.worlds) != len(self.weights):
            raise ValueError("Nonempty aligned worlds/weights required")
        if len(set(self.worlds)) != len(self.worlds):
            raise ValueError("Duplicate worlds")
        if any(type(w) is not int or w <= 0 for w in self.weights):
            raise ValueError("Use positive integer mass; scale rational weights first")
        if any(w < 0 or w >= 1 << len(self.condition_ids) for w in self.worlds):
            raise ValueError("World outside condition domain")

    @cached_property
    def probabilities(self) -> dict[str, F]:
        total = sum(self.weights)
        return {cid: F(sum(mass for world, mass in zip(self.worlds, self.weights)
                           if world & (1 << i)), total)
                for i, cid in enumerate(self.condition_ids)}

    @cached_property
    def _posteriors(self) -> dict[tuple[int, int], Belief | None]:
        # Computational cache only: cached_property is excluded from dataclass
        # serialization, equality and the public state's provenance fingerprint.
        return {}

    def condition(self, observed: dict[str, bool]) -> Belief | None:
        if not observed:
            return self
        mask = value = 0
        for cid, answer in observed.items():
            bit = 1 << self.condition_ids.index(cid)
            mask |= bit
            if answer:
                value |= bit
        key = (mask, value)
        if key in self._posteriors:
            return self._posteriors[key]
        rows = [(w, p) for w, p in zip(self.worlds, self.weights) if w & mask == value]
        if not rows:
            self._posteriors[key] = None
            return None  # The public observation contradicts the modeled support.
        if len(rows) == len(self.worlds):
            self._posteriors[key] = self
            return self
        result = Belief(self.condition_ids, tuple(w for w, _ in rows), tuple(p for _, p in rows))
        self._posteriors[key] = result
        return result


@dataclass(frozen=True)
class Plan:
    plan_id: str
    components: tuple[str, ...]
    covered_needs: tuple[str, ...]
    requirements: tuple[tuple[str, bool], ...]
    reward: F = F(1)
    bonuses: tuple[tuple[str, F], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "reward", F(self.reward))
        object.__setattr__(self, "bonuses", tuple((c, F(v)) for c, v in self.bonuses))
        if not self.components or len(dict(self.requirements)) != len(self.requirements):
            raise ValueError("Plans need components and unique scoped constraints")
        if any(type(v) is not bool for _, v in self.requirements):
            raise ValueError("Plan requirements must be Boolean")


@dataclass(frozen=True)
class Query:
    query_id: str
    condition_id: str
    kind: Literal["ASK_USER", "VERIFY_SOURCE"] = "ASK_USER"
    cost: F = F(1, 20)
    resolution_probability: F = F(1)
    observation_model_id: str = "truthful-or-unresolved-v1"
    trusted_model: bool = True

    def __post_init__(self):
        object.__setattr__(self, "cost", F(self.cost))
        object.__setattr__(self, "resolution_probability", F(self.resolution_probability))
        if self.kind not in {"ASK_USER", "VERIFY_SOURCE"}:
            raise ValueError("v0 supports one-field Ask/Verify only")
        if self.cost < 0 or not 0 <= self.resolution_probability <= 1:
            raise ValueError("Invalid cost or observation probability")


@dataclass(frozen=True)
class State:
    conditions: tuple[Condition, ...]
    plans: tuple[Plan, ...]
    prior: Belief
    evidence: tuple[Evidence, ...] = ()
    required_needs: tuple[str, ...] = ("food",)
    source_snapshot: str = "controlled-v1"
    candidate_pool_version: int = 0
    utility_version: int = 0
    version: int = 0
    dependencies_complete: bool = True
    structure_trusted: bool = True

    def __post_init__(self):
        scopes = {c.condition_id: c.subject_scope for c in self.conditions}
        if len(scopes) != len(self.conditions) or tuple(scopes) != self.prior.condition_ids:
            raise ValueError("Unique condition IDs must match the joint model's order")
        if len({p.plan_id for p in self.plans}) != len(self.plans):
            raise ValueError("Duplicate plan ID")
        if len({e.evidence_id for e in self.evidence}) != len(self.evidence):
            raise ValueError("Duplicate evidence ID")
        for e in self.evidence:
            if e.condition_id not in scopes or e.subject_scope != scopes[e.condition_id]:
                raise ValueError("Evidence subject/condition scope mismatch")
        for p in self.plans:
            if any(cid not in scopes for cid, _ in p.requirements + p.bonuses):
                raise ValueError("Plan references an unknown condition")

    @cached_property
    def condition_map(self) -> dict[str, Condition]:
        return {c.condition_id: c for c in self.conditions}

    @cached_property
    def evidence_map(self) -> dict[str, tuple[Evidence, ...]]:
        result = {c.condition_id: [] for c in self.conditions}
        for e in self.evidence:
            result[e.condition_id].append(e)
        return {k: tuple(v) for k, v in result.items()}

    @cached_property
    def facts(self) -> dict[str, tuple[bool | None, bool]]:
        result = {}
        for c in self.conditions:
            values = {e.observed_value for e in self.evidence_map[c.condition_id]
                      if e.observed_value is not None}
            result[c.condition_id] = (next(iter(values)) if len(values) == 1 else None,
                                      len(values) > 1)
        return result

    def status(self, cid: str) -> str:
        value, _ = self.facts[cid]
        return "unknown" if value is None else ("supported" if value else "refuted")

    @cached_property
    def belief(self) -> Belief | None:
        # Recompute from the original prior, so a conflicting/retracted fact does
        # not leave a stale, overconfident posterior behind.
        return self.prior.condition({c: v for c, (v, conflict) in self.facts.items()
                                     if v is not None and not conflict})

    @cached_property
    def fingerprint(self) -> str:
        return digest(self)

    def condition_token(self, cid: str):
        return self.evidence_map[cid]

    def observe(self, cid: str, value: bool | None, *, source_id: str,
                source_version: str = "v1", span: str = "typed observation") -> State:
        scope = next(c.subject_scope for c in self.conditions if c.condition_id == cid)
        e = Evidence(digest((cid, scope, value, source_id, source_version, span)),
                     cid, scope, source_id, source_version, span, value)
        # A new version from the SAME source supersedes that source's earlier
        # claim. Disagreement between sources remains an explicit conflict.
        prior = tuple(x for x in self.evidence
                      if (x.condition_id, x.source_id) != (cid, source_id))
        return replace(self, evidence=prior + (e,), version=self.version + 1)

    def observe_query(self, query: Query, value: bool | None) -> State:
        return self.observe(query.condition_id, value, source_id="query:" + query.query_id,
                            source_version=query.observation_model_id)

    def retract(self, evidence_id: str) -> State:
        if evidence_id not in {e.evidence_id for e in self.evidence}:
            raise ValueError("Unknown evidence ID")
        return replace(self, evidence=tuple(e for e in self.evidence if e.evidence_id != evidence_id),
                       version=self.version + 1)

    def replace_candidates(self, plans: tuple[Plan, ...]) -> State:
        return replace(self, plans=plans, candidate_pool_version=self.candidate_pool_version + 1,
                       version=self.version + 1)


def outcomes(state: State, query: Query) -> tuple[tuple[bool | None, F], ...]:
    if not query.trusted_model or state.belief is None:
        raise ValueError("No trustworthy finite observation model")
    p = state.belief.probabilities[query.condition_id]
    r = query.resolution_probability
    return tuple((o, prob) for o, prob in ((False, r * (1 - p)), (True, r * p), (None, 1 - r))
                 if prob > 0)
