"""Controlled sequential model integration; not operational FoodPath evidence."""
import argparse
from dataclasses import asdict
from decimal import Decimal
from fractions import Fraction as F
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.api import Tariff, load_credentials
from egpr.episodes import ControlledEnvironment, EpisodeBudget, run_episode
from egpr.fixtures import instance
from egpr.ledger import AccessBlocked, BudgetExceeded, Ledger
from egpr.mas import ModelRoles
from egpr.model_voi import GuardedModelEvaluator, model_value_fingerprint
from egpr.providers import make_backend
from egpr.schema import canonical, digest
from egpr.solver import POLICIES
from run_offline import source_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--models", nargs="+", default=["gpt-6-luna", "deepseek-ai/DeepSeek-V4-Pro-0813"])
    ap.add_argument("--credentials", type=Path)
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--cases", type=int, choices=[1, 2, 4], default=2)
    ap.add_argument("--replicate-id", default="model-voi-development-0")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "configs/api_campaign.json").read_text())
    models = json.loads((ROOT / "configs/models.json").read_text())
    selected = {name: models[name] for name in args.models}
    args.output.mkdir(parents=True, exist_ok=False)
    budget = EpisodeBudget()
    bank = [(8, 4, .5, seed) for seed in (13, 37, 73, 101)[:args.cases]]
    manifest = {"source_hashes": source_manifest(), "models": selected, "bank": bank,
                "replicate_id": args.replicate_id, "campaign": cfg, "budget": asdict(budget),
                "scope": "controlled sequential integration with a supported fixture fallback; not FoodPath effectiveness",
                "environment": "fixed joint-prior world and per-query resolution draw, paired across methods and models",
                "environment_seed_rule": "model-episode-v1:<instance seed>",
                "budget_note": "information_actions counts Ask and Verify together; model outputs have configured token caps, no episode token-budget claim",
                "guarantee": "each local one-step choice only, conditional on the same frozen response mapping"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    ledger = Ledger(ROOT / cfg["ledger_path"], allow_paid_calls=args.allow_paid,
                    max_new_paid_usd=min(Decimal(cfg["authorized_total_usd"]), Decimal(cfg["initial_development_ceiling_usd"])))
    start = len(ledger.rows)
    credentials = load_credentials(args.credentials)
    groups, status = [], "complete"
    try:
        for name, model in selected.items():
            tariff = Tariff(**model["tariff"])
            backend = make_backend(model["provider"], credentials, tariff)
            for setting in bank:
                states, queries, _ = instance(*setting, preferences=False, correlated=True)
                state = states[0]
                rng = random.Random(f"model-episode-v1:{setting[-1]}")
                world = rng.choices(state.prior.worlds, weights=state.prior.weights, k=1)[0]
                truth = {cid: bool(world & (1 << i)) for i, cid in enumerate(state.prior.condition_ids)}
                unresolved = {q.query_id for q in queries if rng.random() >= float(q.resolution_probability)}
                order = list(POLICIES)
                random.Random(digest(("model-episode-order-v1", name, setting))).shuffle(order)
                records = {}
                for policy in order:
                    ev = GuardedModelEvaluator(lambda: ModelRoles(ledger, model, backend, tariff, replicate_id=args.replicate_id),
                        cache=POLICIES[policy][1], value_model_fingerprint=model_value_fingerprint(model, args.replicate_id))
                    episode = run_episode(state, queries, ControlledEnvironment(truth, unresolved=unresolved),
                                          policy=policy, budget=budget, evaluator=ev)
                    keys = {k for t in ev.traces for k in t["trace"]["request_hashes"]}
                    receipts = {r["request_hash"]: r for r in ledger.rows if r["status"] == "received"
                                and r["request_hash"] in keys and not r.get("access_blocked")}
                    logical = sum((Decimal(r["logical_uncached_usd"]) for r in receipts.values()
                                   if r.get("logical_uncached_usd") is not None), Decimal(0))
                    delivered = episode["delivered_plan_id"]
                    reward = next((p.reward for p in episode["final_state"].plans if p.plan_id == delivered), F(0))
                    public_actions = [{k: a[k] for k in ("kind", "query_id", "observation", "proposal", "reason") if k in a}
                                      for a in episode["actions"] if a["kind"] != "DECIDE"]
                    record = {"delivered_plan_id": delivered, "supported_completion": episode["score"]["supported_completion"],
                        "truth_correct": episode["score"]["truth_correct"], "final_reward": str(reward),
                        "termination": episode["termination"], "information_actions": episode["information_actions"],
                        "ask_user_actions": sum(a["kind"] == "ASK_USER" for a in episode["actions"]),
                        "verify_source_actions": sum(a["kind"] == "VERIFY_SOURCE" for a in episode["actions"]),
                        "search_actions": episode["search_actions"], "counterfactual_branches": episode["counterfactual_branches"],
                        "unique_model_requests": len(keys), "undiscounted_logical_usd": str(logical),
                        "unpriced_requests": len(keys) - sum(r.get("logical_uncached_usd") is not None for r in receipts.values()),
                        "terminal_evaluations": len(ev.traces), "parse_failures": sum(bool(t["trace"].get("error_type")) for t in ev.traces),
                        "public_actions": public_actions, "work": asdict(ev.work),
                        "finalization_work": episode["finalization_work"]}
                    records[policy] = record
                    with (args.output / "traces.jsonl").open("a") as f:
                        f.write(canonical({"model": name, "setting": setting, "policy": policy,
                                           "record": record, "episode": episode, "terminal_traces": ev.traces}) + "\n")
                    print(name, setting[-1], policy, "delivered=" + str(delivered),
                          "information_actions=" + str(episode["information_actions"]), "requests=" + str(len(keys)), flush=True)
                baseline = records["B2"]
                groups.append({"model": name, "setting": setting, "policies": records,
                    "P_B2_trajectory_equal": records["P"]["public_actions"] == baseline["public_actions"],
                    "P_B3_trajectory_equal": records["P"]["public_actions"] == records["B3"]["public_actions"],
                    "unsupported_delivery": sum(r["delivered_plan_id"] is not None and not r["supported_completion"] for r in records.values())})
    except (AccessBlocked, BudgetExceeded) as exc:
        status = type(exc).__name__
        print("Campaign stopped:", status, flush=True)
    except BaseException:
        status = "interrupted_or_transport_error"
        raise
    finally:
        rows = ledger.rows[start:]
        summary = {"status": status, "completed_model_cases": len(groups), "groups": groups,
                   "new_network_attempts": sum(r["status"] == "reserved" for r in rows),
                   "local_cache_reuses": sum(r["status"] == "reused" for r in rows),
                   "campaign_occupancy_usd": str(ledger.occupancy), "actual_billed_usd": None,
                   "scope": manifest["scope"]}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps({k: v for k, v in summary.items() if k != "groups"}, indent=2), flush=True)
    if status != "complete" or any(g["unsupported_delivery"] for g in groups):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
