from dataclasses import replace
from decimal import Decimal

import pytest

from egpr.ledger import AccessBlocked, BudgetExceeded, Ledger, Receipt, Request


def request():
    return Request("mock", "frozen-model-v1", ({"role": "user", "content": "hello"},),
                   tools=({"name": "search", "schema": {"type": "object"}},), generation=(("temperature", 0),))


def test_exact_full_request_reuse_and_accounting(tmp_path):
    ledger = Ledger(tmp_path / "calls.jsonl", allow_paid_calls=True, max_new_paid_usd="1")
    calls = []
    def backend(req):
        calls.append(req)
        return Receipt({"ok": True}, "0.10", "0.10", "test-id")
    q = request()
    ledger.run(q, backend, paid=True, maximum_usd="0.2")
    ledger.run(q, backend, paid=True, maximum_usd="0.2")
    assert len(calls) == 1 and ledger.occupancy == Decimal("0.10")
    for changed in [replace(q, model_snapshot="v2"), replace(q, tools=()),
                    replace(q, generation=(("temperature", 1),)), replace(q, response_format="text"),
                    replace(q, endpoint="new")]:
        assert changed.key != q.key
    assert ledger.rows[-1]["logical_uncached_usd"] == "0.10"
    assert ledger.rows[-1]["billed_usd"] == "0"


def test_no_paid_calls_by_default_and_no_retry_after_quota(tmp_path):
    ledger = Ledger(tmp_path / "calls.jsonl")
    with pytest.raises(BudgetExceeded):
        ledger.run(request(), lambda _: None, paid=True, maximum_usd="0.1")
    assert not ledger.rows
    ledger = Ledger(tmp_path / "paid.jsonl", allow_paid_calls=True, max_new_paid_usd="1")
    def blocked(_):
        raise AccessBlocked("quota")
    with pytest.raises(AccessBlocked):
        ledger.run(request(), blocked, paid=True, maximum_usd="0.3")
    reloaded = Ledger(ledger.path, allow_paid_calls=True, max_new_paid_usd="1")
    assert reloaded.occupancy == Decimal("0.3")
    with pytest.raises(AccessBlocked):
        reloaded.run(request(), lambda _: pytest.fail("must not call"), paid=True, maximum_usd="0.3")


def test_interruption_reservation_survives_restart(tmp_path):
    ledger = Ledger(tmp_path / "calls.jsonl", allow_paid_calls=True, max_new_paid_usd="0.4")
    def interrupt(_):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        ledger.run(request(), interrupt, paid=True, maximum_usd="0.3")
    ledger = Ledger(ledger.path, allow_paid_calls=True, max_new_paid_usd="0.4")
    with pytest.raises(BudgetExceeded):
        ledger.run(request(), lambda _: None, paid=True, maximum_usd="0.3")
    ledger.reconcile(ledger.rows[0]["attempt_id"], "0.05", "mock-provider-receipt")
    assert ledger.occupancy == Decimal("0.05")
