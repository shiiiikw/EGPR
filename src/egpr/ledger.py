"""Provider-independent, append-only request bookkeeping.

Real calls require an injected backend and an explicit positive paid budget.
An unresolved reservation survives a process interruption and blocks spending
that amount again. It must be reconciled from a provider receipt, not guessed.
"""
from dataclasses import asdict, dataclass
from contextlib import contextmanager
from decimal import Decimal
import fcntl
import json
from pathlib import Path
import time
import uuid

from .schema import digest


class BudgetExceeded(RuntimeError):
    pass


class AccessBlocked(RuntimeError):
    pass


class PendingReservation(BudgetExceeded):
    pass


def money(value):
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise ValueError("Money must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class Request:
    provider: str
    model_snapshot: str
    messages: tuple[dict, ...]
    tools: tuple[dict, ...] = ()
    generation: tuple[tuple[str, object], ...] = ()
    response_format: str | dict = "json"
    endpoint: str = "offline"
    replicate_id: str = "replicate-0"

    @property
    def key(self):
        return digest(self)


@dataclass(frozen=True)
class Receipt:
    response: dict
    billed_usd: str | None = "0"
    logical_uncached_usd: str | None = "0"
    provider_request_id: str | None = None
    usage: dict | None = None
    estimated_usd: str | None = None
    cost_basis: str = "provider_receipt_or_offline"
    access_blocked: bool = False


class Ledger:
    """One global budget/cache per campaign, with an enforced single writer.

    API usage times a frozen tariff is an estimate, never a provider bill.
    Unknown costs keep the original reservation. Raw responses, even malformed
    completions and HTTP errors, are persisted before application validation.
    """
    def __init__(self, path: Path, *, allow_paid_calls=False, max_new_paid_usd="0"):
        self.path = Path(path)
        self.allow_paid_calls = allow_paid_calls
        self.limit = money(max_new_paid_usd)
        self.reload()

    def reload(self):
        self.rows = [json.loads(line) for line in self.path.read_text().splitlines()] if self.path.exists() else []

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("Another process owns this campaign ledger") from None
            try:
                self.reload()
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

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
                attempts[row["attempt_id"]] = money(row["reserved_usd"])
            elif row["status"] in {"success", "received", "reconciled"}:
                value = row.get("billed_usd")
                if value is None:
                    value = row.get("estimated_usd")
                if value is not None:
                    attempts[row["attempt_id"]] = money(value)
        return sum(attempts.values(), Decimal(0))

    @property
    def access_blocked(self):
        return any(r["status"] == "access_blocked" or r.get("access_blocked") for r in self.rows)

    def run(self, request: Request, invoke, *, paid=False, maximum_usd="0") -> dict:
        with self.locked():
            return self._run(request, invoke, paid=paid, maximum_usd=maximum_usd)

    def _run(self, request, invoke, *, paid, maximum_usd):
        cached = next((r for r in reversed(self.rows) if r["status"] in {"success", "received"} and r["request_hash"] == request.key), None)
        if cached:
            self.append({"status": "reused", "request_hash": request.key,
                         "original_attempt_id": cached["attempt_id"], "billed_usd": "0",
                         "estimated_usd": "0", "access_blocked": cached.get("access_blocked", False),
                         "logical_uncached_usd": cached["logical_uncached_usd"]})
            if cached.get("access_blocked"):
                raise AccessBlocked("Cached access failure; no new request sent")
            return cached["response"]
        if self.access_blocked:
            raise AccessBlocked("Access failure recorded; no automatic retry or provider switch")
        completed = {r["attempt_id"] for r in self.rows if r["status"] in {"success", "received", "reconciled"}}
        if any(r["status"] == "reserved" and r["request_hash"] == request.key
               and r["attempt_id"] not in completed for r in self.rows):
            raise PendingReservation("Reconcile the uncertain attempt before requesting it again")
        reserve = money(maximum_usd)
        if paid and (not self.allow_paid_calls or reserve <= 0):
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
            # Persist first: output parsing/cost validation must not lose a paid
            # response and cause a second charge on restart.
            self.append({"status": "received", "attempt_id": attempt,
                         "request_hash": request.key, **asdict(receipt)})
            amount = receipt.billed_usd if receipt.billed_usd is not None else receipt.estimated_usd
            accounted = reserve if amount is None else money(amount)
            if accounted > reserve:
                raise BudgetExceeded("Receipt violates the declared per-request bound")
            if receipt.access_blocked:
                raise AccessBlocked("Provider access/quota failure; raw response retained")
            return receipt.response
        except BaseException as exc:
            status = "access_blocked" if isinstance(exc, AccessBlocked) else "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
            self.append({"status": status, "attempt_id": attempt,
                         "request_hash": request.key, "error_type": type(exc).__name__})
            raise

    def reconcile(self, attempt_id: str, billed_usd: str, provider_receipt: str):
        with self.locked():
            self._reconcile(attempt_id, billed_usd, provider_receipt)

    def _reconcile(self, attempt_id, billed_usd, provider_receipt):
        if not provider_receipt:
            raise ValueError("A provider receipt is required to release a reservation")
        if not any(r.get("attempt_id") == attempt_id and r["status"] == "reserved" for r in self.rows):
            raise ValueError("Unknown attempt")
        value = money(billed_usd)
        self.append({"status": "reconciled", "attempt_id": attempt_id,
                     "billed_usd": str(value), "provider_receipt": provider_receipt})
