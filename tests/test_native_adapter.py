import pytest

from egpr.native_adapter import FieldObservation, project_search


def observed(status, value=None, scope="need:food"):
    return FieldObservation(scope, status, value, "user-turn-1", "explicit fixture statement")


def test_unknown_absence_and_unrestricted_never_collapse_to_supported_evidence():
    unknown = project_search("need:food", ("Food Assistance",), {})
    absent = project_search("need:food", ("Food Assistance",), {"available_documents": observed("explicit_none")})
    assert unknown.arguments == absent.arguments  # Same permissive discovery.
    assert unknown.unresolved_fields != absent.unresolved_fields
    assert absent.unsupported_semantics == ("available_documents:explicit_none_not_representable",)
    assert not unknown.native_evidence_complete and not absent.native_evidence_complete
    waived = project_search("need:food", ("Food Assistance",), {"eligibility": observed("unrestricted")})
    assert waived.unsupported_semantics == ("eligibility:capability_cannot_be_waived",)


def test_meaningful_values_are_projected_without_invented_filters():
    p = project_search("need:food", ("Food Assistance",), {
        "schedule": observed("unrestricted"), "location": observed("values", {"cities": ["Exampletown"]}),
        "intake_methods": observed("values", ("walk_in",)),
        "available_documents": observed("values", ("photo_id",)),
        "eligibility": observed("values", ("resident",)),
    })
    assert p.native_evidence_complete
    assert p.arguments["cities"] == ["Exampletown"] and "schedule" not in p.arguments
    assert len(p.source_records) == 5


def test_scope_conflicts_and_placeholder_values_are_not_silently_accepted():
    with pytest.raises(ValueError, match="scope"):
        project_search("need:food", ("Food Assistance",), {"eligibility": observed("values", ("resident",), "need:other")})
    with pytest.raises(ValueError, match="Empty"):
        observed("values", ())
    with pytest.raises(ValueError, match="placeholder"):
        project_search("need:food", ("Food Assistance",), {"eligibility": observed("values", ("unknown",))})
    p = project_search("need:food", ("Food Assistance",), {"eligibility": observed("conflict")})
    assert "eligibility" in p.unresolved_fields
