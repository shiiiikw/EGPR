"""Compare declared settings of one base model, never count them as more models."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    configurations, seen, identities, sources = {}, set(), set(), []
    for folder in args.inputs:
        manifest = json.loads((folder / "manifest.json").read_text())
        summary = json.loads((folder / "summary.json").read_text())
        if summary["status"] != "complete":
            raise ValueError("Do not drop unfinished states from a sensitivity table")
        identities.add((tuple(map(tuple, manifest["bank"])), manifest["replicate_id"]))
        selected = {name: model for name, model in manifest["models"].items() if model["model"] == args.model}
        sources.append({"run": folder.name, "input_sha256": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                        for name in ("manifest.json", "summary.json", "traces.jsonl")}})
        for name, model in selected.items():
            settings = {"provider": model["provider"], "generation": model["generation"],
                        "output_style": model.get("output_style", "original")}
            identity = json.dumps(settings, sort_keys=True)
            if identity in seen or name in configurations:
                raise ValueError("A replay or alias does not add a new setting")
            seen.add(identity)
            groups = [g for g in summary["groups"] if g["model"] == name]
            if {tuple(g["setting"]) for g in groups} != set(map(tuple, manifest["bank"])):
                raise ValueError("Expected the complete paired bank")
            terminal = Counter()
            for line in (folder / "traces.jsonl").read_text().splitlines():
                row = json.loads(line)
                if row["model"] != name or row["policy"] != "B2":
                    continue
                for item in row["terminal_traces"]:
                    trace = item["trace"]
                    terminal["evaluations"] += 1
                    terminal["response_errors"] += bool(trace.get("error_type"))
                    terminal["no_delivery"] += trace["delivered_plan_id"] is None
            methods = {}
            for policy in ("B1", "B2", "B3", "A1", "P"):
                rows = [g["policies"][policy] for g in groups]
                if any(r["unpriced_requests"] for r in rows):
                    raise ValueError("Logical cost comparison requires priced receipts")
                methods[policy] = {"requests_summed_over_states": sum(r["unique_model_requests"] for r in rows),
                    "logical_usd": str(sum((Decimal(r["undiscounted_logical_usd"]) for r in rows), Decimal(0)))}
            configurations[name] = {"settings": settings, "states": len(groups), "methods": methods,
                "B2_terminals": dict(terminal), "audit_errors": {key: sum(g[key] for g in groups)
                    for key in ("action_disagreements", "bound_violations", "false_pruning")}}
    if len(identities) != 1 or not configurations:
        raise ValueError("Settings must share a case bank and replicate identity")
    result = {"base_model": args.model, "base_model_count": 1, "configurations": configurations,
              "sources": sources, "scope": "Paired development sensitivity; settings and cached replays are not independent cases or additional base models."}
    table = ["# Output setting sensitivity", "", result["scope"], "",
             "| Setting | Cap | B2 requests | P requests | B2 response errors | B2 no delivery | P/B2 logical cost |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, row in configurations.items():
        b, p = row["methods"]["B2"], row["methods"]["P"]
        ratio = Decimal(p["logical_usd"]) / Decimal(b["logical_usd"]) if Decimal(b["logical_usd"]) else None
        ratio_text = f"{ratio:.3f}" if ratio is not None else "undefined"
        cap = row["settings"]["generation"].get("max_tokens", row["settings"]["generation"].get("max_completion_tokens"))
        t = row["B2_terminals"]
        table.append(f"| {name} | {cap} | {b['requests_summed_over_states']} | {p['requests_summed_over_states']} | {t['response_errors']} / {t['evaluations']} | {t['no_delivery']} / {t['evaluations']} | {ratio_text} |")
    table += ["", "All settings keep all four states and five methods. A response failure may stop the pipeline early, so a lower request count alone is not better efficiency. P equals B3.", ""]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "table.md").write_text("\n".join(table))
    print(json.dumps({"base_models": 1, "settings": len(configurations)}))


if __name__ == "__main__":
    main()
