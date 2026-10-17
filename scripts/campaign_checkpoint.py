"""Publish aggregate accounting only; never raw requests, responses or secrets."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egpr.ledger import Ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    config = json.loads((ROOT / "configs/api_campaign.json").read_text())
    ledger = Ledger(ROOT / config["ledger_path"])
    # Reject concurrent network work rather than snapshot half of an attempt.
    with ledger.locked():
        attempts = {}
        for row in ledger.rows:
            if row["status"] == "reserved":
                attempts[row["attempt_id"]] = {"reserved": Decimal(row["reserved_usd"]),
                                               "billed": None, "estimate": None}
            elif row["status"] in {"received", "success", "reconciled"}:
                attempt = attempts[row["attempt_id"]]
                if row.get("billed_usd") is not None:
                    attempt["billed"] = Decimal(row["billed_usd"])
                if row.get("estimated_usd") is not None:
                    attempt["estimate"] = Decimal(row["estimated_usd"])
        known_billed = sum((a["billed"] for a in attempts.values() if a["billed"] is not None), Decimal(0))
        estimates = sum((a["estimate"] for a in attempts.values()
                         if a["billed"] is None and a["estimate"] is not None), Decimal(0))
        unknown = [a for a in attempts.values() if a["billed"] is None and a["estimate"] is None]
        reserved = sum((a["reserved"] for a in unknown), Decimal(0))
        if known_billed + estimates + reserved != ledger.occupancy:
            raise ValueError("Checkpoint does not reproduce ledger occupancy")
        report = {
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "authorized_total_usd": config["authorized_total_usd"],
            "development_ceiling_usd": config["initial_development_ceiling_usd"],
            "network_attempts": len(attempts),
            "successful_inference_responses": sum(r["status"] in {"received", "success"}
                and r.get("response", {}).get("http_status") == 200 for r in ledger.rows),
            "usage_based_estimate_usd": str(estimates),
            "known_billed_component_usd": str(known_billed),
            "unreconciled_reservations_usd": str(reserved),
            "unreconciled_reservations": len(unknown),
            "budget_occupancy_usd": str(ledger.occupancy),
            "actual_billed_usd": str(known_billed) if all(a["billed"] is not None for a in attempts.values()) else None,
            "access_blocked": ledger.access_blocked,
            "ledger_sha256": hashlib.sha256(ledger.path.read_bytes()).hexdigest(),
            "privacy": "Only aggregates published; raw requests, responses, credentials and private disclosures remain local.",
            "billing_note": "Estimates and unresolved reservations are not a provider invoice. Successful HTTP responses may still contain failed model outputs.",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as f:
        f.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("network_attempts", "usage_based_estimate_usd",
                     "unreconciled_reservations_usd", "budget_occupancy_usd", "actual_billed_usd", "access_blocked")}))


if __name__ == "__main__":
    main()
