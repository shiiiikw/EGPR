"""Provider-independent, append-only request bookkeeping. No network client.

Real calls require an injected backend and an explicit positive paid budget.
An unresolved reservation survives a process interruption and blocks spending
that amount again. It must be reconciled from a provider receipt, not guessed.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
import time
import uuid

from .schema import digest


class BudgetExceeded(RuntimeError):
    pass


class AccessBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class Request:
    provider: str
    model_snapshot: str
    messages: tuple[dict, ...]
    tools: tuple[dict, ...] = ()
    generation: tuple[tuple[str, object], ...] = ()
    response_format: str = "json"
    endpoint: str = "offline"

    @property
    def key(self):
        return digest(self)


@dataclass(frozen=True)
class Receipt:
    response: dict
    billed_usd: str = "0"
    logical_uncached_usd: str = "0"
    provider_request_id: str | None = None
    usage: dict | None = None


class Ledger:
    """Single-writer ledger; concurrent scheduling is deliberately unsupported."""
    def __init__(self, path: Path, *, allow_paid_calls=False, max_new_paid_usd="0"):
        self.path = Path(path)
        self.allow_paid_calls = allow_paid_calls
        self.limit = Decimal(max_new_paid_usd)
        if self.limit < 0:
            raise ValueError("Negative budget")
        self.rows = [json.loads(line) for line in self.path.read_text().splitlines()] if self.path.exists() else []

    def append(self, row):
        row = {"time_ns": time.time_ns(), **row}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
            f.flush()
            import os
            os.fsync(f.fileno())
        self.rows.append(row)

    @property
    def occupancy(self):
        attempts = {}
        for row in self.rows:
            if row["status"] == "reserved":
                attempts[row["attempt_id"]] = Decimal(row["reserved_usd"])
            elif row["status"] in {"success", "reconciled"}:
                attempts[row["attempt_id"]] = Decimal(row["billed_usd"])
        return sum(attempts.values(), Decimal(0))

    @property
    def access_blocked(self):
        return any(r["status"] == "access_blocked" for r in self.rows)

    def run(self, request: Request, invoke, *, paid=False, maximum_usd="0") -> dict:
        cached = next((r for r in reversed(self.rows) if r["status"] == "success" and r["request_hash"] == request.key), None)
        if cached:
            self.append({"status": "reused", "request_hash": request.key,
                         "original_attempt_id": cached["attempt_id"], "billed_usd": "0",
                         "logical_uncached_usd": cached["logical_uncached_usd"]})
            return cached["response"]
        if self.access_blocked:
            raise AccessBlocked("Access failure recorded; no automatic retry or provider switch")
        reserve = Decimal(maximum_usd)
        if reserve < 0 or (paid and (not self.allow_paid_calls or reserve <= 0)):
            raise BudgetExceeded("Paid calls disabled or missing a positive per-request reservation")
        if not paid and reserve:
            raise ValueError("Offline calls must reserve zero")
        if self.occupancy + reserve > self.limit:
            raise BudgetExceeded("Paid reservation would exceed the run's budget")
        attempt = uuid.uuid4().hex
        self.append({"status": "reserved", "attempt_id": attempt, "request_hash": request.key,
                     "reserved_usd": str(reserve), "request": asdict(request), "paid": paid})
        try:
            receipt = invoke(request)
            billed = Decimal(receipt.billed_usd)
            if billed < 0 or billed > reserve:
                # Persist an actual overrun before raising; never silently erase
                # billed usage. Providers still need their own hard request cap.
                self.append({"status": "reconciled", "attempt_id": attempt,
                             "billed_usd": str(max(billed, Decimal(0))), "overrun": True})
                raise BudgetExceeded("Receipt violates the declared per-request bound")
            self.append({"status": "success", "attempt_id": attempt, "request_hash": request.key,
                         **asdict(receipt)})
            return receipt.response
        except BaseException as exc:
            status = "access_blocked" if isinstance(exc, AccessBlocked) else "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
            self.append({"status": status, "attempt_id": attempt,
                         "request_hash": request.key, "error_type": type(exc).__name__})
            raise

    def reconcile(self, attempt_id: str, billed_usd: str, provider_receipt: str):
        if not provider_receipt:
            raise ValueError("A provider receipt is required to release a reservation")
        if not any(r.get("attempt_id") == attempt_id and r["status"] == "reserved" for r in self.rows):
            raise ValueError("Unknown attempt")
        value = Decimal(billed_usd)
        if value < 0:
            raise ValueError("Negative actual cost")
        self.append({"status": "reconciled", "attempt_id": attempt_id,
                     "billed_usd": str(value), "provider_receipt": provider_receipt})
