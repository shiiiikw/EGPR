"""Field-limited disclosure of stored native task data, with no inferred answers.

This is a deterministic adapter, not a learned user simulator. A preferred
profile, when present, is the initial profile; the later alternative is not
revealed without a separately implemented and justified preference transition.
The public view contains only declared service categories and answers already
requested. Target resources and source-derived task identifiers never enter it.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass

from .native_adapter import FIELDS, FieldObservation, project_search
from .schema import digest


class DisclosureBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class DisclosureBudget:
    information_items: int = 8
    user_rounds: int = 8

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in asdict(self).values()):
            raise ValueError("Disclosure budgets must be nonnegative integers")


class NativeUser:
    def __init__(self, spec: dict, *, source_snapshot: str, source_pointer: str = "",
                 budget: DisclosureBudget = DisclosureBudget()):
        if not source_snapshot or not isinstance(spec.get("needs"), list) or not spec["needs"]:
            raise ValueError("A source snapshot and nonempty native needs are required")
        if source_pointer and not source_pointer.startswith("/"):
            raise ValueError("Source pointer must be an absolute JSON pointer")
        self._budget = budget
        self._answers = {}
        self._needs = []
        self._observed = {}
        self._history = []
        self._distinct = set()
        self._items = 0
        # Do not retain the original spec, target labels, or future alternatives.
        for index, need in enumerate(spec["needs"]):
            scope = f"need:{index}"
            preferred = need.get("preferred")
            if preferred is not None and not isinstance(preferred, dict):
                raise ValueError("Preferred profile must be a dictionary or null")
            profile = preferred if preferred is not None else need
            categories = profile.get("service_categories")
            if not isinstance(categories, list):
                raise ValueError("Native service categories must be a list")
            categories = tuple(categories)
            project_search(scope, categories, {})  # Validate declared categories.
            self._needs.append({"need_scope": scope, "service_categories": categories})
            self._observed[scope] = {}
            prefix = source_pointer + f"/needs/{index}" + ("/preferred" if preferred is not None else "")
            for field in FIELDS:
                raw = deepcopy(profile.get(field))
                # Empty/missing fields have no reliable absence/waiver semantics.
                # An unresolved answer carries a source pointer, not a made-up fact.
                span = prefix + "/" + field
                source_id = "native-field:" + digest((source_snapshot, span, raw))
                reason = None
                if not raw:
                    observation = FieldObservation(scope, "unknown", source_id=source_id, source_span=span)
                    reason = "missing_or_ambiguous_empty_field"
                else:
                    value = tuple(raw) if isinstance(raw, list) else raw
                    try:
                        observation = FieldObservation(scope, "values", value, source_id, span)
                        projection = project_search(scope, categories, {field: observation})
                        if projection.unsupported_semantics:
                            raise ValueError("Unsupported native field semantics")
                    except ValueError:
                        observation = FieldObservation(scope, "unknown", source_id=source_id, source_span=span)
                        reason = "unsupported_native_field_semantics"
                self._answers[scope, field] = {"field": field, "observation": asdict(observation),
                                              "unresolved_reason": reason}

    @property
    def counters(self):
        return {"requested_information_items": self._items,
                "distinct_information_items": len(self._distinct),
                "user_rounds": len(self._history)}

    def public_view(self):
        return deepcopy({"needs": self._needs, "observations": self._observed,
                         "counters": self.counters})

    def ask(self, need_scope: str, fields: tuple[str, ...]):
        if need_scope not in self._observed:
            raise ValueError("Unknown need scope")
        if not fields or len(set(fields)) != len(fields) or any(f not in FIELDS for f in fields):
            raise ValueError("Ask for one or more distinct supported fields")
        if self._items + len(fields) > self._budget.information_items or (
                len(self._history) >= self._budget.user_rounds):
            raise DisclosureBudgetExceeded("Requested disclosure exceeds the shared user budget")
        answers = [deepcopy(self._answers[need_scope, field]) for field in fields]
        self._items += len(fields)  # Repeated questions still cost information items.
        for answer in answers:
            self._observed[need_scope][answer["field"]] = deepcopy(answer)
            self._distinct.add((need_scope, answer["field"]))
        reply = {"need_scope": need_scope, "answers": answers,
                 "user_round": len(self._history) + 1, "information_items": len(fields)}
        self._history.append(deepcopy(reply))
        return reply
