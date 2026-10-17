"""Sequential controlled integration audit. No LLM or service-network calls."""
import argparse
from dataclasses import asdict
from fractions import Fraction as F
import gzip
import itertools
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.episodes import ControlledEnvironment, EpisodeBudget, run_episode
from egpr.fixtures import instance
from egpr.schema import canonical
from run_offline import source_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    policies = ("B1", "B2", "B3", "A1", "P")
    grid = list(itertools.product((8, 32), (4, 8), (0, .75), (13, 37, 73, 101, 137)))
    budget = EpisodeBudget()
    manifest = {"source_hashes": source_manifest(), "grid": grid, "budget": asdict(budget),
                "variants": ["truthful", "one_unresolved", "search_recovery"],
                "scope": "controlled sequential integration audit, not FoodPath or live MAS quality",
                "api_calls": 0, "paid_usd": 0}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    totals = {p: {"episodes": 0, "supported_completion": 0, "truth_correct": 0,
                  "information_actions": 0, "search_actions": 0, "counterfactual_branches": 0,
                  "unsupported_commits": 0} for p in policies}
    disagreements = 0
    with gzip.open(args.output / "episodes.jsonl.gz", "wt") as f:
        for np, nc, share, seed in grid:
            for variant in manifest["variants"]:
                signatures = []
                for policy in policies:
                    states, queries, _ = instance(np, nc, share, seed, preferences=False, correlated=True)
                    state = states[0]
                    rng = random.Random(f"episode:{np}:{nc}:{share}:{seed}")
                    world = rng.choices(state.prior.worlds, weights=state.prior.weights, k=1)[0]
                    truth = {c.condition_id: bool(world & (1 << i)) for i, c in enumerate(state.conditions)}
                    unresolved = {queries[0].query_id} if variant == "one_unresolved" else set()
                    batches = (state.plans,) if variant == "search_recovery" else ()
                    if batches:
                        state = state.replace_candidates(())
                    env = ControlledEnvironment(truth, unresolved=unresolved, search_batches=batches)
                    result = run_episode(state, queries, env, policy=policy, budget=budget)
                    score = result["score"]
                    t = totals[policy]
                    t["episodes"] += 1
                    for k in ("information_actions", "search_actions", "counterfactual_branches"):
                        t[k] += result[k]
                    for k in ("supported_completion", "truth_correct"):
                        t[k] += score[k]
                    t["unsupported_commits"] += result["delivered_plan_id"] is not None and not score["supported_completion"]
                    signatures.append((result["delivered_plan_id"], result["information_actions"],
                                       result["search_actions"], result["termination"]))
                    f.write(canonical({"setting": (np, nc, share, seed), "variant": variant,
                                       "budget": budget, "result": result}) + "\n")
                disagreements += len(set(signatures)) != 1
    summary = {"case_variants": len(grid) * len(manifest["variants"]), "totals": totals,
               "policy_outcome_disagreements": disagreements,
               "branch_ratio_P_B2": totals["P"]["counterfactual_branches"] / totals["B2"]["counterfactual_branches"],
               "scope": manifest["scope"], "api_calls": 0, "paid_usd": 0,
               "quality_note": "Generator includes a publicly supported fallback; completion rate is not an effectiveness claim."}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if disagreements or any(t["unsupported_commits"] for t in totals.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
