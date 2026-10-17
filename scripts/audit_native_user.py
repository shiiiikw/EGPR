"""Audit disclosure on development groups only; no API calls or policy scores."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.native_adapter import FIELDS
from egpr.native_user import DisclosureBudget, NativeUser
from egpr.schema import canonical


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foodpath", type=Path, required=True)
    ap.add_argument("--qualification", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    source = args.foodpath / "experiments/exploration_2026_10_15_round25/generated_specs.json"
    qualified = json.loads((args.qualification / "data_manifest.json").read_text())
    if sha(source) != qualified["input_sha256"]["private/generated_specs.json"]:
        raise ValueError("Native spec no longer matches the qualified source")
    split_path = args.qualification / "local_split.json"
    split = json.loads(split_path.read_text())
    dev_ids = {case for group in split["development"] for case in group}
    specs = [(index, s) for index, s in enumerate(json.loads(source.read_text())) if s["case_id"] in dev_ids]
    if len(specs) != len(dev_ids):
        raise ValueError("Development allocation did not map one-to-one to native cases")
    args.output.mkdir(parents=True, exist_ok=False)
    counts, by_field, records = Counter(), {f: Counter() for f in FIELDS}, []
    snapshot_hash = sha(source)
    for index, spec in specs:
        n = len(spec["needs"])
        # Exhaustive adapter audit, not the paper's eight-item policy budget.
        user = NativeUser(spec, source_snapshot=snapshot_hash, source_pointer=f"/{index}",
                          budget=DisclosureBudget(n * (len(FIELDS) + 1), n * 2))
        initial = user.public_view()
        assert all(not observations for observations in initial["observations"].values())
        case = {"case_id": spec["case_id"], "disclosures": []}
        for need in initial["needs"]:
            scope = need["need_scope"]
            reply = user.ask(scope, FIELDS)
            case["disclosures"].append(reply)
            for answer in reply["answers"]:
                status = answer["observation"]["status"]
                counts[status] += 1
                by_field[answer["field"]][status] += 1
            repeated = user.ask(scope, (FIELDS[0],))
            assert repeated["answers"][0] == reply["answers"][0]
            counts["repeat_checks"] += 1
        assert user.counters["distinct_information_items"] == n * len(FIELDS)
        counts.update(user.counters)
        counts["needs"] += n
        counts["preferred_profile_cases"] += any(need.get("preferred") for need in spec["needs"])
        case["counters"] = user.counters
        records.append(case)
    report = {"scope": "exhaustive native development disclosure audit, not a policy or effectiveness experiment",
              "development_source_groups": len(split["development"]), "development_cases": len(specs),
              "reserved_cases_evaluated": 0, "counts": dict(counts),
              "field_statuses": {k: dict(v) for k, v in by_field.items()},
              "api_calls": 0, "paid_usd": 0,
              "initial_public_context": "service categories and opaque within-task need scopes only",
              "empty_field_semantics": "unresolved; never inferred absence or waived preference",
              "preference_transition": "initial preferred profile only; later alternative and consent are not modeled",
              "limitations": ["No free-text extraction, query valuation, live source check, or real-user validation",
                              "Coverage of stored fields cannot establish supported operational completion"]}
    manifest = {"source_sha256": sha(source), "split_sha256": sha(split_path),
                "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in
                                  [Path(__file__), ROOT / "src/egpr/native_user.py", ROOT / "src/egpr/native_adapter.py"]},
                "raw_source_redistributed": False}
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (args.output / "private_disclosures.jsonl").write_text("".join(canonical(r) + "\n" for r in records))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
