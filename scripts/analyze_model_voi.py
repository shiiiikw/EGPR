"""Descriptive model-pilot tables, including failures; no population inference."""
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path


POLICIES = ("B1", "B2", "B3", "A1", "P")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=Path, nargs="+", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    seen, groups, audits, manifests = set(), defaultdict(list), [], []
    for folder in args.inputs:
        manifest = json.loads((folder / "manifest.json").read_text())
        summary = json.loads((folder / "summary.json").read_text())
        if summary["status"] != "complete":
            raise ValueError("Do not silently pool incomplete paid queues into paired tables")
        replicate = manifest["replicate_id"]
        files = [folder / "manifest.json", folder / "summary.json"]
        for g in summary["groups"]:
            key = (g["model"], tuple(g["setting"]), replicate)
            if key in seen:
                raise ValueError("Duplicate model/state/replicate; replay is not a new sample")
            seen.add(key)
            if set(g["policies"]) != set(POLICIES):
                raise ValueError("Expected all five methods in every paired state")
            groups[g["model"]].append(g)
        trace_path = folder / "traces.jsonl"
        if trace_path.exists():
            files.append(trace_path)
            for line in trace_path.read_text().splitlines():
                row = json.loads(line)
                if row["policy"] != "B2":
                    continue
                for terminal in row["terminal_traces"]:
                    trace = terminal["trace"]
                    audits.append({"model": row["model"], "setting": row["setting"],
                        "replicate_id": replicate, "state_fingerprint": terminal["state_fingerprint"],
                        "terminal_utility": terminal["terminal_utility"],
                        "initial_guard_rejected": bool(trace.get("initial_guard") and not trace["initial_guard"]["allowed"]),
                        "final_guard_rejected": bool(trace.get("final_guard") and not trace["final_guard"]["allowed"]),
                        "parse_failure": bool(trace.get("error_type")),
                        "no_delivery": trace["delivered_plan_id"] is None})
        manifests.append({"run": folder.name, "replicate_id": replicate,
                          "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})
    result = {"scope": "descriptive development model/state pairs; counterfactual branches are not independent cases",
              "source_runs": manifests, "models": {},
              "cost_note": "Logical cost prices each unique request once without provider cache discounts; not a bill.",
              "guard_note": "B2 enumerated terminal evaluations only, including abstentions and failed recovery. Not an online task success rate."}
    for model, gs in sorted(groups.items()):
        methods = {}
        for p in POLICIES:
            methods[p] = {
                "unique_requests_summed_over_states": sum(g["policies"][p]["unique_model_requests"] for g in gs),
                "logical_usd": str(sum((Decimal(g["policies"][p]["undiscounted_logical_usd"]) for g in gs), Decimal(0))),
                "unpriced_requests": sum(g["policies"][p]["unpriced_requests"] for g in gs)}
        selected = [a for a in audits if a["model"] == model]
        guard_audit = {"terminal_evaluations": len(selected)}
        guard_audit.update({key: sum(a[key] for a in selected) for key in
                           ("initial_guard_rejected", "final_guard_rejected", "parse_failure", "no_delivery")})
        result["models"][model] = {"model_state_pairs": len(gs), "methods": methods,
            "audit_errors": {k: sum(g[k] for g in gs) for k in
                             ("action_disagreements", "bound_violations", "false_pruning")},
            "B2_terminal_audit": guard_audit if selected else None,
            "P_B3_equal": all(g["policies"]["P"] == g["policies"]["B3"] for g in gs)}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "terminal_audit.jsonl").write_text("".join(json.dumps(a, sort_keys=True) + "\n" for a in audits))
    table = ["# Model VOI development results", "",
        "Each row aggregates the recorded synthetic development states for that model. These are not independent FoodPath outcomes.", "",
        "| Model | States | B2 requests | P requests | P/B2 logical cost | B2 no delivery / terminal evaluations |",
        "|---|---:|---:|---:|---:|---:|"]
    for model, row in result["models"].items():
        b, p = row["methods"]["B2"], row["methods"]["P"]
        ratio = Decimal(p["logical_usd"]) / Decimal(b["logical_usd"]) if Decimal(b["logical_usd"]) else None
        a = row["B2_terminal_audit"]
        failure = f"{a['no_delivery']} / {a['terminal_evaluations']}" if a else "not available"
        ratio_text = f"{ratio:.3f}" if ratio is not None else "undefined"
        table.append(f"| {model} | {row['model_state_pairs']} | {b['unique_requests_summed_over_states']} | {p['unique_requests_summed_over_states']} | {ratio_text} | {failure} |")
    table += ["", "All five methods use the same roles and final evidence guard. P and B3 remain the same algorithm; this table does not establish a novelty advantage.", "",
        "Request counts are summed per state, not new network calls or independent samples. Local cache reuse and provider prompt discounts do not determine the logical cost comparison.", "",
        "The B2 terminal audit keeps every enumerated branch. No-delivery includes abstention and rejected recovery; the final guard blocks unsupported commitments. These branches are correlated counterfactual evaluations, not an online task-success denominator.", ""]
    (args.output / "table.md").write_text("\n".join(table))
    print(json.dumps({"models": len(groups), "paired_model_states": len(seen), "B2_terminal_audits": len(audits)}))


if __name__ == "__main__":
    main()
