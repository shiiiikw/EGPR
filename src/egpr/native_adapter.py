"""Typed discovery projection for the pinned FoodPath/HoosierHelp interface.

Unknown, explicit absence and waived preferences are different states. The
legacy tool collapses some of them to no filter; that cannot certify a match.
This module contains no upstream code, raw data, or hidden task labels.
"""
from dataclasses import dataclass
from typing import Literal


FIELDS = ("schedule", "location", "intake_methods", "available_documents", "eligibility")
PREFERENCES = {"schedule", "location"}
PLACEHOLDERS = {"unknown", "none", "varies", "empty"}


@dataclass(frozen=True)
class FieldObservation:
    subject_scope: str
    status: Literal["unknown", "values", "explicit_none", "unrestricted", "conflict"]
    value: tuple[str, ...] | dict | None = None
    source_id: str | None = None
    source_span: str | None = None

    def __post_init__(self):
        if not self.subject_scope:
            raise ValueError("A field needs explicit subject scope")
        if self.status not in {"unknown", "values", "explicit_none", "unrestricted", "conflict"}:
            raise ValueError("Unknown observation status")
        if self.status != "unknown" and (not self.source_id or not self.source_span):
            raise ValueError("A resolved or conflicting observation needs provenance")
        if self.status == "values":
            if not isinstance(self.value, (tuple, dict)) or not self.value:
                raise ValueError("Empty values must be typed as absence or unrestricted")
        elif self.value is not None:
            raise ValueError("Only a values observation carries a filter value")


@dataclass(frozen=True)
class SearchProjection:
    arguments: dict
    unresolved_fields: tuple[str, ...]
    unsupported_semantics: tuple[str, ...]
    source_records: tuple[tuple[str, str | None, str | None], ...]

    @property
    def native_evidence_complete(self):
        return not self.unresolved_fields and not self.unsupported_semantics


def _strings(value):
    if not isinstance(value, (list, tuple)) or not value or any(
            not isinstance(v, str) or not v.strip() or v.strip().casefold() in PLACEHOLDERS for v in value):
        raise ValueError("Use explicit meaningful string values, not empty lists or placeholder tags")
    return list(value)


def project_search(need_scope: str, service_categories: tuple[str, ...], observations: dict[str, FieldObservation]):
    """Build discovery arguments plus obligations that a caller MUST retain.

    A resource returned by a permissive search is not thereby recommended. Even
    native_evidence_complete is only a projection property, not evidence of live
    availability, genuine eligibility, travel feasibility or a completed plan.
    """
    if set(observations) - set(FIELDS):
        raise ValueError("Unknown field")
    arguments = {"service_categories": _strings(service_categories)}
    unresolved, unsupported, sources = [], [], []
    for field in FIELDS:
        observation = observations.get(field, FieldObservation(need_scope, "unknown"))
        if observation.subject_scope != need_scope:
            raise ValueError("Unverified cross-need scope sharing")
        sources.append((field, observation.source_id, observation.source_span))
        if observation.status in {"unknown", "conflict"}:
            unresolved.append(field)
            continue
        if observation.status == "explicit_none":
            # [] would disable a legacy capability filter, not express absence.
            unsupported.append(field + ":explicit_none_not_representable")
            continue
        if observation.status == "unrestricted":
            if field not in PREFERENCES:
                unsupported.append(field + ":capability_cannot_be_waived")
            continue
        value = observation.value
        if field == "location":
            if not isinstance(value, dict) or set(value) - {"counties", "cities", "zipcodes"}:
                raise ValueError("Location must use native counties/cities/zipcodes")
            arguments.update({key: _strings(values) for key, values in value.items()})
        elif field == "schedule":
            if not isinstance(value, dict) or set(value) - {"day", "start_time", "end_time", "time", "requires_24_hours"}:
                raise ValueError("Schedule must use native schedule fields")
            if not value.get("day") and value.get("requires_24_hours") is not True:
                unsupported.append("schedule:missing_day_or_24_hour_requirement")
            else:
                arguments[field] = dict(value)
        else:
            arguments[field] = _strings(value)
    return SearchProjection(arguments, tuple(unresolved), tuple(unsupported), tuple(sources))
