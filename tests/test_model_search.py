from fractions import Fraction as F

import pytest

from egpr.episodes import ControlledEnvironment, run_episode
from egpr.model_voi import GuardedModelEvaluator
from egpr.schema import Belief, Condition, Plan, State
from egpr.solver import POLICIES


class OverlooksExistingPlan:
    def recommend(self, state):
        # An admissible old plan does not imply that this model delivered it.
        selected = "public-alternative" if any(p.plan_id == "public-alternative" for p in state.plans) else None
        return {"delivered_plan_id": selected, "request_hashes": []}


@pytest.mark.parametrize("policy", tuple(POLICIES))
def test_model_abstention_can_recover_with_the_common_public_search(policy):
    state = State((Condition("x", "person", "x"),),
                  (Plan("overlooked", ("old",), ("food",), (), F(1)),),
                  Belief(("x",), (0, 1), (1, 1)))
    alternative = Plan("public-alternative", ("alternative",), ("food",), (), F(1))
    ev = GuardedModelEvaluator(OverlooksExistingPlan, cache=POLICIES[policy][1],
                               value_model_fingerprint="model-search-recovery-v1")
    environment = ControlledEnvironment({"x": True}, search_batches=[(alternative,)])
    result = run_episode(state, (), environment, policy=policy, evaluator=ev)
    assert result["search_actions"] == 1
    assert result["delivered_plan_id"] == "public-alternative"
    assert result["score"]["supported_completion"]
    assert result["final_state"].evidence == ()
    assert result["finalization_work"]["terminal_evaluations"] == 1
