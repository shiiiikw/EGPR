# EGPR — Evidence-Grounded Plan Revision

EGPR investigates whether conservative information-value screening and incremental
plan revision reduce computation while preserving evidence-supported complete
plans. This repository now contains an executable **finite-state first stage**.
It also contains a guarded API role pipeline and a frozen-response model VOI
pilot. It does not yet establish a novel method advantage or a full FoodPath result.

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
or third-party dataset. The finite core uses the Python standard library;
Together inference additionally uses its pinned official SDK (`uv sync --extra together`).

## Implemented first stage

- Scoped source evidence, unknown/false/conflict separation, complete-plan checks.
- Exact joint finite beliefs; evidence obligations remain distinct from truth.
- B1 full one-step VOI, B2 dependency caching, A1 screening only, P screening plus
  caching, and B3 generic branch-and-bound. **P and B3 are identical in v0.**
- Rational interval witnesses, strict-dominance certificates and safe fallback.
- Cache invalidation and revision reports, including indirect belief changes.
- Small multi-step reference for complementarity tests.
- Bounded sequential Ask/Verify, public candidate replacement, revision and final
  guard; a separate controlled environment holds simulator truth.
- Full-request caching, append-only accounting, interrupted reservations, process
  locking, and explicit recovery after externally resolved API access failures.
- OpenAI and official Together SDK transports; actual Planner, Reviewer and
  Coordinator calls with bounded guard recovery. All four Together models passed
  the initial access gate; the model VOI queue now uses explicit request pacing.
- A fallible model terminal evaluator with zero lower bounds, structural upper
  bounds and model-specific certificates. Its guarantee is conditional on a
  frozen exact-request response mapping.
- A field-limited native user adapter: scoped answers, unresolved missing fields,
  repeated-item accounting and atomic budgets. Initial preferred profiles cannot
  disclose later alternatives. See [the native adapter contract](docs/NATIVE_ADAPTER.md).

The implementation is limited to fixed candidate pools, Boolean conditions and
one-field Ask/Verify. Dynamic pool replacement invalidates cached certificates;
live service search and real user outcomes are not implemented by this finite
solver. Controlled search reveals a predeclared public candidate batch.
Conditional/unresolved outputs do not count as supported completion. All fixture
utilities and observation models are declared assumptions.

## Evidence and next steps

See [the current research report](docs/PROGRESS_2026_10_17.md),
[API budget and breadth protocol](docs/API_PROTOCOL.md), and
[model VOI correctness/accounting](docs/MODEL_VOI_PROTOCOL.md).
The full 180-instance grid and correlated robustness variant have passed their
audits. Seven model configurations have completed four model VOI development
states each, including all five controls and failure accounting;
[the table](reports/model_voi_analysis_v0_10/table.md) includes model abstentions
and rejected recovery. A complete seven-model replay reused 3,269 responses with
zero new network attempts. The [output audit](reports/model_output_audit_v0_10/output_audit.json)
separates truncation from valid abstention. Full-system extraction, real-source
candidate construction, B0/B4, cross-family effectiveness and cross-domain tests
remain later gates. See the [baseline mapping](docs/BASELINE_SOURCE_AUDIT.md) and
[cross-domain input qualification](docs/CROSS_DOMAIN_QUALIFICATION.md).

The user authorized a US$200 campaign with a US$10 initial development ceiling.
Paid execution still requires `--allow-paid`; default runs reuse cache only.
The public repository does not contain the private FoodPath project, raw service
data, old prompts, API responses or credentials.

```sh
uv run python scripts/run_episodes.py --output results/my-episodes
uv run python scripts/run_role_pilot.py --allow-paid --output results/my-role-pilot
uv run python scripts/run_model_voi.py --allow-paid --cases 2 --output results/my-model-voi
```

Credentials come from `OPENAI_API_KEY` / `TOGETHER_API_KEY` or an explicitly supplied
local assignment file. All API stages share the campaign ledger in `results/`.
