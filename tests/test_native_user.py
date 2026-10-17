from copy import deepcopy

import pytest

from egpr.native_user import DisclosureBudget, DisclosureBudgetExceeded, NativeUser
from egpr.schema import canonical


def spec():
    return {"case_id": "SECRET_TASK", "ground_truth_resources": ["SECRET_TARGET"],
            "needs": [{"need_id": "SECRET_NEED", "ground_truth_resource_id": "SECRET_TARGET",
                       "service_categories": ["Food Assistance"],
                       "location": {"cities": ["Fixturetown"]}, "schedule": {},
                       "intake_methods": ["walk_in"], "available_documents": [],
                       "eligibility": None}]}


def test_requested_fields_only_and_labels_never_reach_public_view():
    user = NativeUser(spec(), source_snapshot="fixture-v1")
    before = canonical(user.public_view())
    assert "SECRET" not in before and "Fixturetown" not in before and "walk_in" not in before
    reply = user.ask("need:0", ("location",))
    assert [a["field"] for a in reply["answers"]] == ["location"]
    after = canonical(user.public_view())
    assert "Fixturetown" in after and "walk_in" not in after and "SECRET" not in after
    reply["answers"][0]["observation"]["value"]["cities"][0] = "tampered"
    assert "tampered" not in canonical(user.public_view())
    again = user.ask("need:0", ("location",))
    assert again["answers"][0]["observation"]["value"]["cities"] == ["Fixturetown"]
    assert user.counters == {"requested_information_items": 2, "distinct_information_items": 1, "user_rounds": 2}


def test_empty_missing_and_placeholder_answers_remain_unresolved():
    data = spec()
    data["needs"][0]["intake_methods"] = ["unknown"]
    user = NativeUser(data, source_snapshot="fixture-v1")
    reply = user.ask("need:0", ("schedule", "available_documents", "eligibility", "intake_methods"))
    assert all(a["observation"]["status"] == "unknown" for a in reply["answers"])
    assert all(a["observation"]["value"] is None for a in reply["answers"])
    assert all(a["observation"]["source_span"] for a in reply["answers"])
    assert user.counters["requested_information_items"] == 4 and user.counters["user_rounds"] == 1


def test_preferred_profile_does_not_reveal_future_fallback_fields():
    data = spec()
    data["needs"][0]["preferred"] = {"service_categories": ["Food Assistance"],
                                     "location": {"cities": ["Preferredtown"]}}
    user = NativeUser(data, source_snapshot="fixture-v1")
    reply = user.ask("need:0", ("location", "intake_methods"))
    text = canonical(reply)
    assert "Preferredtown" in text and "Fixturetown" not in text and "walk_in" not in text
    assert reply["answers"][1]["observation"]["status"] == "unknown"
    assert "/preferred/" in reply["answers"][0]["observation"]["source_span"]
    data["needs"][0]["preferred"] = {}
    with pytest.raises(ValueError, match="categories"):
        NativeUser(data, source_snapshot="fixture-v1")


def test_budget_rejection_is_atomic_and_invalid_fields_do_not_charge():
    user = NativeUser(spec(), source_snapshot="fixture-v1", budget=DisclosureBudget(2, 2))
    with pytest.raises(ValueError):
        user.ask("need:0", ("ground_truth_resource_id",))
    with pytest.raises(ValueError):
        user.ask("need:other", ("location",))
    user.ask("need:0", ("location",))
    before = deepcopy(user.public_view())
    with pytest.raises(DisclosureBudgetExceeded):
        user.ask("need:0", ("location", "eligibility"))
    assert user.public_view() == before
    user.ask("need:0", ("location",))
    assert user.counters["requested_information_items"] == 2
    assert user.counters["distinct_information_items"] == 1
    with pytest.raises(DisclosureBudgetExceeded):
        user.ask("need:0", ("location",))
