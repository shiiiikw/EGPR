"""E1 + fixed-state replay diagnostics, zero API calls; see OFFLINE_PROTOCOL.md."""
import argparse
from dataclasses import asdict, replace
from fractions import Fraction as F
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.fixtures import instance
from egpr.schema import canonical, digest
from egpr.solver import BoundIndex, Controller, Evaluator, revise


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def source_manifest():
    paths = sorted(list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").glob("*.py"))
                   + list((ROOT / "scripts").glob("*.py"))
                   + [ROOT / "configs/offline_v0.json", ROOT / "docs/OFFLINE_PROTOCOL.md", ROOT / "uv.lock"])
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--constant-rewards", action="store_true")
    ap.add_argument("--correlated", action="store_true")
    ap.add_argument("--memory", action="store_true")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((ROOT / "configs/offline_v0.json").read_text())
    grid = list(itertools.product(cfg["plans"], cfg["unknown_conditions"], cfg["anchor_reuse"], cfg["seeds"]))
    if args.smoke:
        grid = [(8, 4, 0, 13), (32, 8, .5, 37), (128, 12, .75, 73)]
    manifest = {"code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "file_sha256": source_manifest(), "config": cfg,
                "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
                "grid_size": len(grid), "api_calls": 0, "paid_usd": 0,
                "timing_scope": "algorithm including state/graph/bound/cache work; input generation and audit separate",
                "memory_instrumented": args.memory}
    write(args.output / "frozen_manifest.json", manifest)
    totals = {name: {"decisions": 0, "wall_seconds": 0., "cpu_seconds": 0.,
                     "branch_evaluations": 0, "constraint_checks": 0, "plan_evaluations": 0,
                     "bound_plan_visits": 0, "cache_hits": 0, "certificates": 0,
                     "peak_traced_bytes": None} for name in cfg["policies"]}
    audit = {"states": 0, "query_bounds": 0, "certificates": 0, "bound_violations": 0,
             "false_pruning": 0, "action_disagreements": 0, "incremental_divergences": 0,
             "max_action_regret": 0., "api_calls": 0}
    paired = []
    started = time.perf_counter()
    with gzip.open(args.output / "raw_decisions.jsonl.gz", "wt") as raw, gzip.open(args.output / "public_states.jsonl.gz", "wt") as bank:
        for index, (np, nc, shared, seed) in enumerate(grid):
            key = f"p{np}-c{nc}-r{shared}-s{seed}"
            construction_start = time.perf_counter()
            states, qs, meta = instance(np, nc, shared, seed, preferences=not args.constant_rewards, correlated=args.correlated)
            construction_seconds = time.perf_counter() - construction_start
            oracle_start = time.perf_counter()
            oracles = []
            for t, state in enumerate(states):
                bank.write(canonical({"instance": key, "step": t, "state": state, "queries": qs}) + "\n")
                e = Evaluator()
                base = e.terminal(state)[0]
                values = {"STOP": F(0)}
                ix = BoundIndex(state, Evaluator())
                for q in qs:
                    if state.status(q.condition_id) != "unknown":
                        continue
                    v = e.q_value(state, q, base)
                    bound = ix.bounds(q, base)
                    audit["query_bounds"] += 1
                    audit["bound_violations"] += not bound.lower <= v <= bound.upper
                    values[q.query_id] = v
                oracles.append((values, min(values, key=lambda q: (-values[q], q != "STOP", q))))
                audit["states"] += 1
            oracle_seconds = time.perf_counter() - oracle_start
            order = list(cfg["policies"])
            random.Random(key).shuffle(order)
            per_instance = {}
            for policy in order:
                if args.memory:
                    tracemalloc.start()
                start, cpu = time.perf_counter(), time.process_time()
                controller = Controller(policy)
                decisions, revisions = [], []
                previous = None
                for t, source in enumerate(states):
                    # New dataclass instances clear cached_property values, so
                    # timed policies do not inherit oracle-warmed belief caches.
                    state = replace(source, prior=replace(source.prior))
                    if previous is not None:
                        revisions.append(revise(previous, state, tuple(decisions[-1].certificates)))
                    decisions.append(controller.decide(state, qs))
                    previous = state
                elapsed, cpu_elapsed = time.perf_counter() - start, time.process_time() - cpu
                peak = tracemalloc.get_traced_memory()[1] if args.memory else None
                if args.memory:
                    tracemalloc.stop()
                total = totals[policy]
                total["wall_seconds"] += elapsed
                total["cpu_seconds"] += cpu_elapsed
                total["decisions"] += len(states)
                if peak is not None:
                    total["peak_traced_bytes"] = max(peak, total["peak_traced_bytes"] or 0)
                for name in ("branch_evaluations", "constraint_checks", "plan_evaluations", "bound_plan_visits", "cache_hits", "certificates"):
                    total[name] += getattr(controller.evaluator.work, name)
                per_instance[policy] = {"wall_seconds": elapsed, "cpu_seconds": cpu_elapsed,
                                        "work": asdict(controller.evaluator.work)}
                for t, d in enumerate(decisions):
                    state = states[t]
                    values, best = oracles[t]
                    regret = max(values.values()) - values[d.selected]
                    audit["action_disagreements"] += d.selected != best
                    audit["max_action_regret"] = max(audit["max_action_regret"], float(regret))
                    for cert in d.certificates:
                        audit["certificates"] += 1
                        audit["false_pruning"] += (not cert.valid(state, qs) or values[cert.query_id] >= values[cert.comparator])
                    raw.write(canonical({"instance": key, "step": t, "policy": policy,
                                         "decision": d, "oracle_values": values, "regret": regret}) + "\n")
                # Outside timing: incremental and fresh terminal computations.
                incremental = Evaluator(cache=True)
                for state in states:
                    audit["incremental_divergences"] += incremental.terminal(state) != Evaluator().terminal(state)
            paired.append({"instance": key, "plans": np, "conditions": nc, "seed": seed, **meta,
                           "construction_seconds": construction_seconds, "oracle_audit_seconds": oracle_seconds,
                           "methods": per_instance})
            if (index + 1) % 10 == 0 or index + 1 == len(grid):
                print(f"Completed {index + 1}/{len(grid)} instances", flush=True)
    audit["passed"] = not any(audit[k] for k in ("bound_violations", "false_pruning", "action_disagreements", "incremental_divergences", "max_action_regret"))
    comparisons = {}
    for baseline in ("B1", "B2", "B3", "A1"):
        comparisons["P/" + baseline] = {metric: totals["P"][metric] / totals[baseline][metric] if totals[baseline][metric] else None
                                      for metric in ("wall_seconds", "cpu_seconds", "branch_evaluations", "constraint_checks", "plan_evaluations")}
    summary = {"scope": "controlled finite-state E1 and same-state replay; not FoodPath MAS effectiveness",
               "instances": len(grid), "states": audit["states"], "totals": totals, "comparisons": comparisons,
               "B3_P": "algorithmically identical in v0; no independent-method advantage established",
               "elapsed_seconds_including_construction_audit_and_io": time.perf_counter() - started,
               "construction_seconds": sum(x["construction_seconds"] for x in paired),
               "oracle_audit_seconds": sum(x["oracle_audit_seconds"] for x in paired),
               "api_calls": 0, "paid_usd": 0, "audit": audit}
    write(args.output / "paired_instances.json", paired)
    write(args.output / "summary.json", summary)
    write(args.output / "verification.json", audit)
    if source_manifest() != manifest["file_sha256"]:
        raise RuntimeError("Source changed during run")
    print(json.dumps({"audit": audit, "comparisons": comparisons}, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
