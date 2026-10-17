"""Descriptive stratified operation/timing analysis; no population p-values."""
import argparse
import json
from pathlib import Path


def compare(rows):
    result = {}
    for baseline in ("B1", "B2", "B3", "A1"):
        ratios = {}
        for metric in ("cpu_seconds", "wall_seconds", "branch_evaluations", "bound_plan_visits"):
            def total(policy):
                return sum(r["methods"][policy].get(metric, r["methods"][policy]["work"].get(metric, 0)) for r in rows)
            den = total(baseline)
            ratios[metric] = total("P") / den if den else None
        result["P/" + baseline] = ratios
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = json.loads((args.input / "paired_instances.json").read_text())
    by_scale = [{"plans": np, "conditions": nc,
                 "instances": len(subset := [r for r in rows if r["plans"] == np and r["conditions"] == nc]),
                 "comparisons": compare(subset)}
                for np in sorted({r["plans"] for r in rows}) for nc in sorted({r["conditions"] for r in rows})]
    seeds = [{"seed": s, "comparisons": compare([r for r in rows if r["seed"] == s])}
             for s in sorted({r["seed"] for r in rows})]
    result = {"input": str(args.input), "instances": len(rows), "overall": compare(rows),
              "by_scale": by_scale, "by_seed": seeds,
              "interpretation": "Fixed synthetic grid and five RNG seeds; descriptive ratios, not human-population confidence intervals."}
    (args.output / "stratified.json").write_text(json.dumps(result, indent=2))
    lines = ["# Stratified offline timing", "", result["interpretation"], "",
             "Ratios below 1 favor P. All methods are paired on the same instance.", "",
             "| Plans | Conditions | Instances | CPU P/B1 | CPU P/B2 | CPU P/B3 | CPU P/A1 |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for row in by_scale:
        values = " | ".join(f'{row["comparisons"]["P/" + b]["cpu_seconds"]:.3f}' for b in ("B1", "B2", "B3", "A1"))
        lines.append(f'| {row["plans"]} | {row["conditions"]} | {row["instances"]} | {values} |')
    lines += ["", "P and B3 execute the same algorithm in this stage. Their small timing",
              "differences are measurement/order effects, not a method advantage.", ""]
    (args.output / "table.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
