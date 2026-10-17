"""Descriptive sequential integration results; replay is not an extra sample."""
import argparse
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path

POLICIES = ("B1", "B2", "B3", "A1", "P")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    source = args.input
    summary = json.loads((source / "summary.json").read_text())
    manifest = json.loads((source / "manifest.json").read_text())
    if summary["status"] != "complete":
        raise ValueError("Report incomplete queues separately")
    grouped, seen = defaultdict(list), set()
    for group in summary["groups"]:
        identity = (group["model"], tuple(group["setting"]), manifest["replicate_id"])
        if identity in seen or set(group["policies"]) != set(POLICIES):
            raise ValueError("Duplicate or incomplete paired group")
        seen.add(identity)
        grouped[group["model"]].append(group)
    result = {
        "scope": manifest["scope"], "source_run": source.name,
        "input_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                         for name in ("manifest.json", "summary.json", "traces.jsonl")},
        "replicate_id": manifest["replicate_id"], "models": {},
        "cost_note": "Per-case complete unique request sets; undiscounted usage price, not a bill or cache-order saving.",
        "quality_note": "Supported fixture fallback; completion is an integration result, not operational FoodPath success. Cases are paired across models.",
    }
    table = ["# Sequential model integration", "", result["quality_note"], "",
             "| Model | Method | Cases | Supported | Reward sum | Information actions | Requests | Logical USD |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for model, groups in sorted(grouped.items()):
        methods = {}
        for policy in POLICIES:
            records = [g["policies"][policy] for g in groups]
            row = {"cases": len(records)}
            for key in ("supported_completion", "truth_correct", "information_actions", "ask_user_actions",
                        "verify_source_actions", "search_actions", "counterfactual_branches", "unique_model_requests",
                        "unpriced_requests", "terminal_evaluations", "parse_failures"):
                row[key] = sum(r[key] for r in records)
            row["final_reward_sum"] = str(sum((Fraction(r["final_reward"]) for r in records), Fraction(0)))
            row["undiscounted_logical_usd"] = str(sum((Decimal(r["undiscounted_logical_usd"]) for r in records), Decimal(0)))
            row["unsupported_deliveries"] = sum(r["delivered_plan_id"] is not None and not r["supported_completion"] for r in records)
            row["information_budget_violations"] = sum(r["information_actions"] > manifest["budget"]["information_actions"] for r in records)
            row["branch_budget_violations"] = sum(r["counterfactual_branches"] > manifest["budget"]["counterfactual_branches"] for r in records)
            methods[policy] = row
            table.append(f"| {model} | {policy} | {row['cases']} | {row['supported_completion']} | {row['final_reward_sum']} | {row['information_actions']} | {row['unique_model_requests']} | {Decimal(row['undiscounted_logical_usd']):.6f} |")
        result["models"][model] = {"methods": methods,
            "P_B2_trajectory_disagreements": sum(not g["P_B2_trajectory_equal"] for g in groups),
            "P_B3_trajectory_disagreements": sum(not g["P_B3_trajectory_equal"] for g in groups)}
    table += ["", result["cost_note"], "", "P remains the same algorithm as B3. Report failures and budget limits alongside request savings; this does not prove multi-step optimality.", ""]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "table.md").write_text("\n".join(table))
    print(json.dumps({"models": len(grouped), "model_case_pairs": len(seen)}))


if __name__ == "__main__":
    main()
