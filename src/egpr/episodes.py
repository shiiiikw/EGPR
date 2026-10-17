"""Bounded sequential execution and a separate controlled simulator.

The controller sees public states only. Search exposes a predeclared public
candidate batch, never a target-specific oracle plan. This is a deterministic
integration environment, not a live service or learned user simulator.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as F
from typing import Callable

from .schema import Plan, Query, State
from .solver import Controller, Evaluator, guard, revise


@dataclass(frozen=True)
class EpisodeBudget:
    steps: int = 16
    information_actions: int = 8
    counterfactual_branches: int = 200
    search_actions: int = 1

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in asdict(self).values()):
            raise ValueError("Budgets must be nonnegative integers")


class ControlledEnvironment:
    """Hidden answers are stored here, never in the planner's public context."""
    def __init__(self, truth: dict[str, bool], *, unresolved=(), search_batches=()):
        if any(type(v) is not bool for v in truth.values()):
            raise ValueError("Controlled truth must be Boolean")
        self._truth = dict(truth)
        self._unresolved = set(unresolved)
        self._search_batches = list(search_batches)

    def observe(self, query):
        return None if query.query_id in self._unresolved else self._truth[query.condition_id]

    def search(self):
        return self._search_batches.pop(0) if self._search_batches else None

    def score(self, state, plan_id):
        if plan_id is None:
            return {"truth_correct": False, "supported_completion": False}
        p = next(p for p in state.plans if p.plan_id == plan_id)
        return {"truth_correct": all(self._truth[c] == v for c, v in p.requirements),
                "supported_completion": guard(state, plan_id)["allowed"]}


def run_episode(state: State, queries: tuple[Query, ...], environment: ControlledEnvironment,
                *, policy="P", budget=EpisodeBudget(), finalizer: Callable | None = None):
    controller = Controller(policy)
    remaining = list(queries)
    actions = []
    information = branches = searches = rejected = 0
    cost, delivered = F(0), None
    termination = "step_budget_exhausted"
    finalizer = finalizer or (lambda s: Evaluator().terminal(s)[1])
    last_certificates = ()

    def finalize(reason):
        nonlocal delivered, rejected, termination
        proposal = finalizer(state)
        check = guard(state, proposal) if proposal is not None else None
        if check and not check["allowed"]:
            rejected += 1
        delivered = proposal if check and check["allowed"] else None
        actions.append({"kind": "RECOMMEND_SUPPORTED" if delivered else "REPORT_UNRESOLVED",
                        "proposal": proposal, "checker": check, "reason": reason,
                        "state_fingerprint": state.fingerprint})
        termination = reason

    for _ in range(budget.steps):
        branch_remaining = budget.counterfactual_branches - branches
        decision = controller.decide(state, tuple(remaining), branch_budget=branch_remaining)
        branches += decision.work.branch_evaluations
        actions.append({"kind": "DECIDE", "state_fingerprint": state.fingerprint, "decision": asdict(decision)})
        last_certificates = tuple(decision.certificates)
        if not decision.exact_selection:
            # Budget exhaustion or an unavailable observation model does not
            # become a proof that every remaining question is worthless.
            finalize(decision.fallback or "nonexact_decision")
            break
        if decision.selected != "STOP" and information < budget.information_actions:
            query = next(q for q in remaining if q.query_id == decision.selected)
            answer = environment.observe(query)
            new = state.observe_query(query, answer)
            actions.append({"kind": query.kind, "query_id": query.query_id, "observation": answer,
                            "revision": asdict(revise(state, new, last_certificates))})
            state = new
            remaining = [q for q in remaining if q.query_id != query.query_id]
            information += 1
            cost += query.cost
            continue
        supported = Evaluator().terminal(state)[1]
        if decision.selected == "STOP" and supported is None and searches < budget.search_actions:
            batch = environment.search()
            searches += 1  # Empty search results still consume a tool action.
            if batch is not None:
                new = state.replace_candidates(tuple(batch))
                actions.append({"kind": "SEARCH_OR_REVISE", "new_candidate_ids": [p.plan_id for p in batch],
                                "revision": asdict(revise(state, new, last_certificates))})
                state = new
                continue
            actions.append({"kind": "SEARCH_OR_REVISE", "new_candidate_ids": [], "empty": True})
        finalize("information_budget_exhausted" if decision.selected != "STOP" else "one_step_stop")
        break
    else:
        finalize("step_budget_exhausted")
    return {"policy": policy, "termination": termination, "delivered_plan_id": delivered,
            "score": environment.score(state, delivered), "information_actions": information,
            "search_actions": searches, "counterfactual_branches": branches,
            "modeled_information_cost": cost, "rejected_final_proposals": rejected,
            "unresolved_conditions": sorted(c for c, (v, _) in state.facts.items() if v is None),
            "actions": actions, "final_state": state}
