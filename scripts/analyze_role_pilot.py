"""Report the complete guarded fixture matrix, retaining failed role outputs."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text())
    summary = json.loads((args.input / "summary.json").read_text())
    if summary["status"] != "complete":
        raise ValueError("An incomplete provider queue is not a completed case matrix")
    cases, seen = [], set()
    for line in (args.input / "traces.jsonl").read_text().splitlines():
        row = json.loads(line)
        identity = (row["model"], row["case"])
        if identity in seen:
            raise ValueError("A cached replay is not another fixture")
        seen.add(identity)
        trace = row.get("trace") or {}
        cases.append({"model": row["model"], "case": row["case"], "guarded_correct": row["correct"],
            "response_error": bool(row.get("error_type")),
            "initial_guard_rejected": bool(trace.get("initial_guard") and not trace["initial_guard"]["allowed"]),
            "final_guard_rejected": bool(trace.get("final_guard") and not trace["final_guard"]["allowed"]),
            "role_requests": len(trace.get("request_hashes", row.get("request_hashes", [])))})
    expected = {(model, case) for model in manifest["models"] for case in manifest["cases"]}
    if seen != expected or sum(r["guarded_correct"] for r in cases) != summary["correct_cases"]:
        raise ValueError("Fixture matrix does not match the declared roster and summary")
    models = {}
    for model in manifest["models"]:
        rows = [r for r in cases if r["model"] == model]
        models[model] = {"cases": len(rows)} | {key: sum(r[key] for r in rows) for key in
            ("guarded_correct", "response_error", "initial_guard_rejected", "final_guard_rejected", "role_requests")}
    result = {"scope": "Fixed synthetic evidence fixtures after the common guard and bounded recovery; not raw model accuracy or operational effectiveness",
              "models": models, "cases": cases, "source_run": args.input.name,
              "replicate_id": manifest["replicate_id"],
              "input_sha256": {name: hashlib.sha256((args.input / name).read_bytes()).hexdigest()
                               for name in ("manifest.json", "summary.json", "traces.jsonl")},
              "failure_note": "A guarded correct abstention can follow a rejected unsupported proposal; guard rejection counts are retained."}
    table = ["# Guarded evidence fixture matrix", "", result["scope"], "",
             "| Model | Correct / cases | Response errors | Initial guard rejections | Final guard rejections |",
             "|---|---:|---:|---:|---:|"]
    for model, row in models.items():
        table.append(f"| {model} | {row['guarded_correct']} / {row['cases']} | {row['response_error']} | {row['initial_guard_rejected']} | {row['final_guard_rejected']} |")
    table += ["", result["failure_note"], "", "The same declared cases are shared across all models. Previously cached cases are reused, not counted as additional independent observations.", ""]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "table.md").write_text("\n".join(table))
    print(json.dumps({"models": len(models), "model_case_pairs": len(cases),
                      "guarded_correct": sum(r["guarded_correct"] for r in cases)}))


if __name__ == "__main__":
    main()
