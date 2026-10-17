"""Read-only qualification of the existing cohort; no raw source redistribution.

The upstream author matcher is imported at its pinned revision, never copied.
Ground truth is used only in this qualification program, not by EGPR policies.
Outputs under results/ are local. Only aggregate reports should be published.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

PIN = "7f6b5ec955bcb4b3ba861fcd86f80269b61f692a"
FOOD = {"Food Assistance", "Food and Meals"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def groups(tokens):
    parent = {case: case for case in tokens}
    def root(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c
    owner = {}
    for case, keys in tokens.items():
        for key in keys:
            if key in owner:
                parent[root(case)] = root(owner[key])
            else:
                owner[key] = case
    result = {}
    for case in tokens:
        result.setdefault(root(case), []).append(case)
    return sorted([sorted(v) for v in result.values()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foodpath", type=Path, required=True)
    ap.add_argument("--upstream", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    upstream = args.upstream.resolve()
    actual = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if actual != PIN:
        raise ValueError("Upstream revision differs from the frozen source")
    cohort_dir = args.foodpath / "experiments/exploration_2026_10_15_round25"
    old_manifest = json.loads((cohort_dir / "source_manifest.json").read_text())
    verified = {name: sha(upstream / name) == expected for name, expected in old_manifest["input_sha256"].items()}
    if not all(verified.values()):
        raise ValueError("Upstream source/data hash mismatch")
    sys.path.insert(0, str(upstream))
    from tools.indiana211 import load_filtered_resources, request_from_tool_args, _match_resource
    from eval.spec_generation import expected_tool_args_for_need
    index = load_filtered_resources(upstream / "data/benchmark/filtered_resources_tagged.csv")
    with (upstream / "data/benchmark/filtered_resources_raw.csv").open() as f:
        raw = {r["resource_id"]: r for r in csv.DictReader(f)}
    all_specs = json.loads((cohort_dir / "generated_specs.json").read_text())
    specs = [s for s in all_specs if any(FOOD.intersection(n["service_categories"]) for n in s["needs"])]

    def match(call):
        request = request_from_tool_args(call)
        # Public tool is top-20 capped. Qualification requires all alternatives;
        # apply the pinned author's predicate to every row, without changing it.
        return {r.resource_id for r in index.resources if _match_resource(r, request) is not None}

    def provenance(ids):
        out = set()
        for rid in ids:
            out.add("resource:" + rid)
            provider = raw[rid].get("agency_name", "").strip().casefold()
            if provider:
                out.add("agency:" + provider)
            url = raw[rid].get("service_website", "").strip().rstrip("/").casefold()
            if url and url not in {"none", "n/a"}:
                out.add("document:" + url)
        return out

    rows, reference_tokens, provider_tokens, candidate_tokens = [], {}, {}, {}
    for spec in specs:
        case = spec["case_id"]
        initial_sets, final_sets, preferred_counts = [], [], []
        needs = []
        for need in spec["needs"]:
            initial = match({"service_categories": need["service_categories"]})
            final = match(expected_tool_args_for_need(need))
            initial_sets.append(initial)
            final_sets.append(final)
            expected = need["ground_truth_resource_id"]
            if expected not in final:
                raise ValueError("Native final target fails its unchanged matcher")
            if need.get("preferred"):
                preferred = match(expected_tool_args_for_need(need["preferred"]))
                preferred_counts.append(len(preferred))
                if preferred:
                    raise ValueError("Native preferred-empty assertion failed")
            needs.append({"need_id": need["need_id"], "initial_alternatives": len(initial),
                          "native_final_alternatives": len(final), "target_is_accepted": True,
                          "empty_generated_fields": [k for k in ("schedule", "location", "intake_methods", "available_documents", "eligibility") if not need.get(k)]})
        refs = set(spec["source_resource_ids"])
        initial_all = set().union(*initial_sets)
        reference_tokens[case] = {"resource:" + r for r in refs}
        provider_tokens[case] = provenance(refs)
        candidate_tokens[case] = provenance(initial_all)
        shared_fields = [k for k in ("schedule", "location", "intake_methods", "available_documents", "eligibility")
                         if len(spec["needs"]) > 1 and all(n.get(k) for n in spec["needs"])
                         and len({json.dumps(n[k], sort_keys=True) for n in spec["needs"]}) == 1]
        # Equal values are not a certified shared subject-level fact. Scope is
        # absent from native specs; no cross-service transit/time gold exists.
        rows.append({"case_id": case, "needs": needs, "case_type": spec["case_type"],
                     "fallback_required": bool(preferred_counts),
                     "initial_service_combinations_without_joint_validation": math.prod(map(len, initial_sets)),
                     "final_service_combinations_under_native_independent_matcher": math.prod(map(len, final_sets)),
                     "equal_nonempty_fields_across_needs": shared_fields,
                     "verified_cross_need_shared_condition_scope": False,
                     "within_need_scope_available": True,
                     "joint_operational_plan_gold": False})
    reference_groups = groups(reference_tokens)
    provider_groups = groups(provider_tokens)
    candidate_groups = groups(candidate_tokens)
    historical = json.loads((cohort_dir / "resource_groups.json").read_text())
    if reference_groups != sorted([sorted(g) for g in historical]):
        raise ValueError("Historical resource grouping did not reproduce")
    known_fields = set().union(*(n.keys() for s in specs for n in s["needs"]))
    source_info = json.loads((upstream / "data/indiana211/README.json").read_text())
    split_groups = list(provider_groups)
    random.Random(13).shuffle(split_groups)
    nd = max(1, math.ceil(.2 * len(split_groups)))
    split = {"status": "development allocation only; E3 operational qualification not passed",
             "seed": 13, "grouping": "referenced resource + provider + exact source URL",
             "development": split_groups[:nd], "reserved": split_groups[nd:],
             "candidate_exposure_warning": "All initially retrievable candidates are a separate stricter leakage audit; see group counts."}
    report = {"scope": "static qualification; no policy, LLM or live-provider experiment",
              "all_cases": len(all_specs), "food_cases": len(specs),
              "composite_cases": sum(len(s["needs"]) > 1 for s in specs),
              "needs": sum(len(s["needs"]) for s in specs),
              "food_source_resources": len({n["ground_truth_resource_id"] for s in specs for n in s["needs"] if FOOD.intersection(n["service_categories"])}),
              "historical_resource_groups_reproduced": len(reference_groups),
              "provider_document_groups": len(provider_groups),
              "all_initial_candidate_exposure_groups": len(candidate_groups),
              "development_groups": len(split["development"]), "reserved_groups": len(split["reserved"]),
              "multi_initial_service_combination_cases": sum(r["initial_service_combinations_without_joint_validation"] >= 2 for r in rows),
              "multi_final_native_service_combination_cases": sum(r["final_service_combinations_under_native_independent_matcher"] >= 2 for r in rows),
              "equal_field_multineed_cases": sum(bool(r["equal_nonempty_fields_across_needs"]) for r in rows),
              "verified_cross_need_shared_scope_cases": 0,
              "within_need_candidate_scope_cases": len(specs), "qualified_joint_operational_plan_cases": 0,
              "native_need_fields": sorted(known_fields), "source_snapshot": source_info["retrieved_date"],
              "source_hashes_matched": verified,
              "endpoint_status": {"native_independent_tag_matching": "supported within author semantics",
                                  "cross_service_travel_time": "not labeled",
                                  "current_inventory_or_actual_eligibility": "not labeled",
                                  "user_burden_or_food_receipt": "not labeled",
                                  "EGPR_interactive_benefit": "not evaluated"},
              "decision": "Keep the cohort for native matching and adapter development; do not claim an operational complete-plan E3 result or 45 independent provider groups.",
              "api_calls": 0, "paid_usd": 0}
    manifest = {"upstream_commit": actual, "input_sha256": {**old_manifest["input_sha256"],
                "private/generated_specs.json": sha(cohort_dir / "generated_specs.json"),
                "private/resource_groups.json": sha(cohort_dir / "resource_groups.json")},
                "script_sha256": sha(Path(__file__)),
                "raw_source_redistributed": False,
                "license_status": "No top-level LICENSE found in pinned author tree; no upstream code/data copied into this repository."}
    for name, value in {"qualification_report.json": report, "data_manifest.json": manifest,
                        "local_case_qualification.json": rows, "local_split.json": split,
                        "local_provenance_groups.json": {"resources": reference_groups, "providers_documents": provider_groups,
                                                         "initial_candidates": candidate_groups}}.items():
        (args.output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
