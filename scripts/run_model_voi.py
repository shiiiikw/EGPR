"""Same-state model-valued VOI development pilot, with all exact controls.

Method cost is reconstructed for a standalone cold run from unique exact request
hashes. Cross-method cache order cannot be interpreted as an efficiency result.
"""
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
from egpr.providers import make_backend
from egpr.fixtures import instance
from egpr.ledger import AccessBlocked, BudgetExceeded, Ledger
from egpr.mas import ModelRoles
from egpr.model_voi import GuardedModelEvaluator, model_value_fingerprint
from egpr.schema import canonical, digest
from egpr.solver import Controller, POLICIES
from run_offline import source_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--models", nargs="+", default=["gpt-6-luna", "gpt-4.1-mini-2025-04-14"])
    ap.add_argument("--credentials", type=Path)
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--cases", type=int, choices=[1, 2, 4], default=2)
    ap.add_argument("--replicate-id", default="model-voi-development-0")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((ROOT / "configs/api_campaign.json").read_text())
    models = json.loads((ROOT / "configs/models.json").read_text())
    selected = {name: models[name] for name in args.models}
    ledger = Ledger(ROOT / cfg["ledger_path"], allow_paid_calls=args.allow_paid,
                    max_new_paid_usd=min(Decimal(cfg["authorized_total_usd"]),
                                         Decimal(cfg["initial_development_ceiling_usd"])))
    ledger_start = len(ledger.rows)
    credentials = load_credentials(args.credentials)
    bank = [(8, 4, .5, s) for s in (13, 37, 73, 101)[:args.cases]]
    manifest = {"source_hashes": source_manifest(), "models": selected, "bank": bank,
        "replicate_id": args.replicate_id, "campaign": cfg,
        "terminal_model": "fallible Planner/Reviewer/Coordinator plus guard; fixed nonnegative reward",
        "guarantee": "conditional on frozen exact-request responses and declared finite belief, one step only",
        "scope": "synthetic development same-state replay; not independent FoodPath effectiveness evidence",
        "bounds": "zero lower terminal utility; structural supported-plan maximum upper bound"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    groups, status = [], "complete"
    try:
        for name, model in selected.items():
            tariff = Tariff(**model["tariff"])
            backend = make_backend(model["provider"], credentials, tariff)
            value_id = model_value_fingerprint(model, args.replicate_id)
            for setting in bank:
                states, qs, _ = instance(*setting, preferences=False, correlated=True)
                state = states[0]
                order = list(POLICIES)
                random.Random(digest((name, setting))).shuffle(order)
                records, exact, oracle_selected = {}, None, None
                for policy in order:
                    ev = GuardedModelEvaluator(lambda: ModelRoles(ledger, model, backend, tariff,
                        replicate_id=args.replicate_id), cache=POLICIES[policy][1],
                        value_model_fingerprint=value_id)
                    decision = Controller(policy, evaluator=ev).decide(state, qs)
                    keys = {k for t in ev.traces for k in t["trace"]["request_hashes"]}
                    receipts = {r["request_hash"]: r for r in ledger.rows if r["status"] == "received"
                                and r["request_hash"] in keys and not r.get("access_blocked")}
                    cost = sum((Decimal(r["estimated_usd"]) for r in receipts.values()
                                if r.get("estimated_usd") is not None), Decimal(0))
                    logical = sum((Decimal(r["logical_uncached_usd"]) for r in receipts.values()
                                   if r.get("logical_uncached_usd") is not None), Decimal(0))
                    record = {"decision": asdict(decision), "terminal_traces": ev.traces,
                              "unique_model_requests": len(keys), "cold_usage_estimate_usd": str(cost),
                              "undiscounted_logical_usd": str(logical),
                              "unpriced_requests": len(keys) - sum(r.get("estimated_usd") is not None for r in receipts.values()),
                              "bound_model_fingerprint": value_id}
                    records[policy] = record
                    with (args.output / "traces.jsonl").open("a") as f:
                        f.write(canonical({"model": name, "setting": setting, "policy": policy, **record}) + "\n")
                    if policy == "B2":
                        exact = {q: iv.lower for q, iv in decision.intervals.items()}
                        exact["STOP"] = F(0)
                        oracle_selected = decision.selected
                    print(name, setting[-1], policy, "selected=" + decision.selected,
                          "unique_requests=" + str(len(keys)), "cold_estimate_usd=" + str(cost), flush=True)
                false_pruning = bound_violations = 0
                for record in records.values():
                    d = record["decision"]
                    for q, iv in d["intervals"].items():
                        bound_violations += not iv["lower"] <= exact[q] <= iv["upper"]
                    for cert in d["certificates"]:
                        false_pruning += not exact[cert["query_id"]] < exact[cert["comparator"]]
                groups.append({"model": name, "setting": setting,
                    "action_disagreements": sum(r["decision"]["selected"] != oracle_selected for r in records.values()),
                    "bound_violations": bound_violations, "false_pruning": false_pruning,
                    "policies": {p: {k: v for k, v in r.items() if k not in {"terminal_traces", "decision"}}
                                 | {"action": r["decision"]["selected"], "work": r["decision"]["work"]}
                                 for p, r in records.items()}})
    except (AccessBlocked, BudgetExceeded) as exc:
        status = type(exc).__name__
        print("Campaign stopped:", status, flush=True)
    except BaseException:
        status = "interrupted_or_transport_error"
        raise
    finally:
        rows = ledger.rows[ledger_start:]
        summary = {"status": status, "completed_model_states": len(groups), "groups": groups,
            "new_network_attempts": sum(r["status"] == "reserved" for r in rows),
            "local_cache_reuses": sum(r["status"] == "reused" for r in rows),
            "campaign_occupancy_usd": str(ledger.occupancy),
            "actual_billed_usd": None, "scope": manifest["scope"]}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps({k: v for k, v in summary.items() if k != "groups"}, indent=2))
    if status != "complete" or any(g[k] for g in groups for k in
            ("action_disagreements", "bound_violations", "false_pruning")):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
