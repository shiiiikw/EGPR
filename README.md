# EGPR — Evidence-Grounded Plan Revision

EGPR investigates whether conservative information-value screening and incremental
plan revision reduce computation while preserving evidence-supported complete
plans. This repository now contains an executable **finite-state first stage**.
It does not yet establish a novel method advantage or a full FoodPath MAS result.

The user requested that code live in `shiiiikw/EGPR` and start with a simplified
implementation. This supersedes the destination and full-version-first wording
in the [preserved original plan](docs/PLAN_2026_10_16.md). The current executable
scope and comparison rules are in [the offline protocol](docs/OFFLINE_PROTOCOL.md).

## Run

Python 3.12+ and uv:

```sh
uv sync --frozen
uv run pytest -q
uv run python scripts/run_offline.py --smoke --output results/my-smoke
uv run python scripts/run_offline.py --output results/my-full-grid
```

Every output directory must be new. These commands use no model service, API key,
or third-party dataset. Runtime code uses the Python standard library.

## Implemented first stage

- Scoped source evidence, unknown/false/conflict separation, complete-plan checks.
- Exact joint finite beliefs; evidence obligations remain distinct from truth.
- B1 full one-step VOI, B2 dependency caching, A1 screening only, P screening plus
  caching, and B3 generic branch-and-bound. **P and B3 are identical in v0.**
- Rational interval witnesses, strict-dominance certificates and safe fallback.
- Cache invalidation and revision reports, including indirect belief changes.
- Small multi-step reference for complementarity tests.
- Full-request hashing, append-only accounting, interrupted reservations and
  disabled-by-default paid calls. The ledger has no network backend.

The implementation is limited to fixed candidate pools, Boolean conditions and
one-field Ask/Verify. Dynamic pool replacement invalidates cached certificates;
search itself, live model roles and real user outcomes are not implemented by
this finite solver. Conditional/unresolved outputs do not count as supported
completion. All fixture utilities and observation models are declared assumptions.

## Evidence and next steps

E0 correctness tests and the development smoke are runnable now. Versioned run
artifacts and reports will record actual results; historical FoodPath results are
not EGPR results. Full-system extraction, candidate construction, search/recovery,
B0/B4, two-model evaluation and cross-domain tests remain separate later gates.

No paid calls are enabled. The public repository does not contain the private
FoodPath project, raw service data, old prompts, API responses or credentials.
