"""A bounded API development gate, not the main multi-model experiment."""
import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.api import ChatBackend, ModelResponseError, Tariff, load_credentials
from egpr.ledger import AccessBlocked, BudgetExceeded, Ledger
from egpr.mas import ModelRoles, diagnostic_cases
from egpr.schema import canonical
from egpr.solver import Evaluator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gpt-6-luna", "gpt-4.1-mini-2025-04-14"])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--credentials", type=Path)
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--cases", type=int, default=8)
    ap.add_argument("--replicate-id", default="development-0")
    args = ap.parse_args()
    if not 1 <= args.cases <= 8:
        ap.error("Development pilot has 1–8 fixed cases")
    models = json.loads((ROOT / "configs/models.json").read_text())
    campaign = json.loads((ROOT / "configs/api_campaign.json").read_text())
    selected = {name: models[name] for name in args.models}
    args.output.mkdir(parents=True, exist_ok=False)
    paths = sorted(list((ROOT / "src").rglob("*.py")) + list((ROOT / "configs").glob("*.json"))
                   + [Path(__file__)])
    manifest = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                "models": selected, "campaign": campaign, "replicate_id": args.replicate_id,
                "cases": [name for name, _ in diagnostic_cases()[:args.cases]],
                "scope": "eight deterministic synthetic development fixtures; no population inference"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    ledger = Ledger(ROOT / campaign["ledger_path"], allow_paid_calls=args.allow_paid,
                    max_new_paid_usd=min(Decimal(campaign["authorized_total_usd"]),
                                         Decimal(campaign["initial_development_ceiling_usd"])))
    start = len(ledger.rows)
    credentials = load_credentials(args.credentials)
    results, status = [], "complete"
    try:
        for name, model in selected.items():
            tariff = Tariff(**model["tariff"])
            backend = ChatBackend(credentials, tariff)
            for case_name, state in diagnostic_cases()[:args.cases]:
                roles = ModelRoles(ledger, model, backend, tariff, replicate_id=args.replicate_id)
                expected = Evaluator().terminal(state)[1]
                try:
                    trace = roles.recommend(state)
                    result = {"model": name, "case": case_name, "expected_plan_id": expected,
                              "correct": trace["delivered_plan_id"] == expected, "trace": trace}
                except ModelResponseError as exc:
                    result = {"model": name, "case": case_name, "correct": False,
                              "error_type": type(exc).__name__, "error": str(exc),
                              "request_hashes": roles.requests}
                results.append(result)
                with (args.output / "traces.jsonl").open("a") as f:
                    f.write(canonical(result) + "\n")
                print(name, case_name, "correct=" + str(result["correct"]),
                      "campaign_occupancy_usd=" + str(ledger.occupancy), flush=True)
    except (AccessBlocked, BudgetExceeded) as exc:
        status = type(exc).__name__
        print("Campaign stopped:", status, str(exc), flush=True)
    except BaseException:
        status = "interrupted_or_transport_error"
        raise
    finally:
        rows = ledger.rows[start:]
        summary = {"status": status, "completed_cases": len(results),
            "correct_cases": sum(r["correct"] for r in results),
            "new_network_attempts": sum(r["status"] == "reserved" for r in rows),
            "local_cache_reuses": sum(r["status"] == "reused" for r in rows),
            "campaign_occupancy_usd": str(ledger.occupancy),
            "actual_billed_usd": None, "billing_note": "Usage estimate plus unresolved reservations; no invoice received",
            "per_model": {name: {"completed": sum(r["model"] == name for r in results),
                "correct": sum(r["model"] == name and r["correct"] for r in results)} for name in selected}}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2), flush=True)
    if status != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
