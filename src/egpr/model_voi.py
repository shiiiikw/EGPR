"""One-step VOI for a fallible, guarded model pipeline on a frozen state bank.

Certificates concern a fixed request/replicate response mapping, not expected
performance of future stochastic calls. No model confidence is used as a bound.
The safe terminal range is zero to the best publicly supported fixed reward.
"""
from fractions import Fraction as F
import hashlib
from pathlib import Path

from .api import ModelResponseError
from .schema import digest
from .solver import BoundIndex, Evaluator, Interval, guard


def model_value_fingerprint(model, replicate_id):
    # Include the actual role implementation and API parser, not just a label.
    here = Path(__file__).parent
    code = {name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in ("mas.py", "api.py", "model_voi.py")}
    return digest({"model": model, "replicate_id": replicate_id, "code": code,
                   "objective": "guarded fixed nonnegative reward under frozen model responses"})


class GuardedModelBoundIndex(BoundIndex):
    def bounds(self, query, base):
        structural = super().bounds(query, base)
        # The exact finite solver's positive lower bound is unsound here: an
        # LLM can fail even when a high-value supported plan exists.
        branches = tuple((o, p, F(0), hi) for o, p, _, hi in structural.branches)
        return Interval(-base - query.cost, structural.upper, branches)


class GuardedModelEvaluator(Evaluator):
    def __init__(self, roles_factory, *, cache, value_model_fingerprint):
        super().__init__(cache)
        self.roles_factory = roles_factory
        self.value_model_fingerprint = value_model_fingerprint
        self.traces = []
        self._terminal_values = {}

    def bound_index(self, state):
        return GuardedModelBoundIndex(state, self)

    def terminal(self, state):
        if any(p.bonuses or p.reward < 0 for p in state.plans):
            raise ValueError("Model VOI pilot supports nonnegative fixed rewards only")
        self.work.terminal_evaluations += 1
        key = (state.fingerprint, self.value_model_fingerprint)
        if self.cache and state.dependencies_complete and key in self._terminal_values:
            self.work.cache_hits += 1
            return self._terminal_values[key]
        roles = self.roles_factory()
        try:
            trace = roles.recommend(state)
        except ModelResponseError as exc:
            # This predeclared failure policy is shared by all methods. The raw
            # failure is cached; no extra sample is bought to hide it.
            trace = {"delivered_plan_id": None, "error_type": type(exc).__name__,
                     "request_hashes": roles.requests}
        selected = trace["delivered_plan_id"]
        allowed = selected is not None and guard(state, selected)["allowed"]
        value = next(p.reward for p in state.plans if p.plan_id == selected) if allowed else F(0)
        selected = selected if allowed else None
        self.traces.append({"state_fingerprint": state.fingerprint, "terminal_utility": value,
                            "selected_plan_id": selected, "trace": trace})
        result = (value, selected)
        if self.cache and state.dependencies_complete:
            self._terminal_values[key] = result
        return result
