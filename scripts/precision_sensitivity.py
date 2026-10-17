"""Illustrative independent-Bernoulli zero-loss bound, not cohort power analysis."""
import argparse
import json
import math
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    confidence, margin = .95, .03
    alpha = 1 - confidence
    required = math.ceil(math.log(alpha) / math.log1p(-margin))
    rows = [{"independent_binary_units": n,
             "zero_observed_losses_one_sided_upper_bound": -math.expm1(math.log(alpha) / n)}
            for n in (1, 9, 34, 43, 59, required, 150)]
    report = {"scope": "illustrative sample-precision sensitivity; not achieved power or FoodPath noninferiority evidence",
              "assumption": "independent Bernoulli loss events with zero observed events and a fixed sample size",
              "confidence_one_sided": confidence, "illustrative_loss_margin": margin,
              "minimum_n_for_zero_event_upper_bound_at_most_margin": required,
              "rows": rows,
              "limitations": ["Source groups with multiple cases and unequal dependence are not independent Bernoulli trials by default",
                              "Actual paired quality differences include both gains and losses; this is not their full confidence interval",
                              "Development states, model variants, counterfactual branches and cached replays do not multiply independent source groups",
                              "The stricter initial-candidate provenance audit forms one connected group, so unseen-provider generalization is not established"]}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "sensitivity.json").write_text(json.dumps(report, indent=2) + "\n")
    table = ["# Sample precision sensitivity", "",
        "This is an illustrative calculation for zero losses in a fixed sample of independent binary units. It is not the confidence interval for our clustered paired results, a power guarantee, or a reviewer-acceptance threshold.", "",
        "| Independent binary units | One-sided 95% upper bound with zero losses |",
        "|---:|---:|"]
    table += [f"| {r['independent_binary_units']} | {100*r['zero_observed_losses_one_sided_upper_bound']:.2f}% |" for r in rows]
    table += ["", f"Under these illustrative assumptions, at least {required} independent units with zero losses are needed to put the upper bound at 3% or below. Thirty-four or 43 groups cannot establish that precision merely by adding model runs or reusing responses.", "",
              "The actual FoodPath grouping and endpoint qualification remain separate requirements. Report clustered paired uncertainty for eligible frozen evaluation data, and retain an inconclusive result when the interval is too wide.", ""]
    (args.output / "table.md").write_text("\n".join(table))
    print(json.dumps({"required_independent_binary_units_under_assumption": required}))


if __name__ == "__main__":
    main()
