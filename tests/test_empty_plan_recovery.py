from unittest.mock import Mock

import pytest

from egpr.mas import ModelRoles, diagnostic_cases


@pytest.mark.parametrize("recovered", ["pantry_a", None, ""])
def test_empty_plan_identifier_receives_bounded_guard_recovery(recovered):
    # Empty string is allowed by the JSON string type, but is not a known plan.
    roles = ModelRoles(None, {}, None, None)
    roles.ask = Mock(side_effect=[
        {"plan_id": "", "reason": "empty proposal"},
        {"valid": False, "issues": ["unknown plan"]},
        {"plan_id": "", "reason": "empty decision"},
        {"plan_id": recovered, "reason": "recovery"},
    ])
    result = roles.recommend(dict(diagnostic_cases())["supported"])
    assert roles.ask.call_count == 4
    assert result["initial_guard"]["reasons"] == ["unknown_plan"]
    assert result["delivered_plan_id"] == ("pantry_a" if recovered == "pantry_a" else None)
    if recovered == "":
        assert result["final_guard"]["reasons"] == ["unknown_plan"]
