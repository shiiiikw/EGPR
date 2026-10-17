# EGPR v0 execution amendment and frozen offline protocol

The user requested implementation in `shiiiikw/EGPR`, starting with a simplified
version and reporting each stage before continuing. These instructions supersede
the original plan's destination and its prohibition on starting small. The full
plan is preserved unchanged in [PLAN_2026_10_16.md](PLAN_2026_10_16.md), copied from
repository commit `d561304`. Referenced directive/configuration files did not
exist at that commit. This amendment does not authorize new paid model calls.

## First executable scope

Implement M1–M4 on finite Boolean state, fixed complete candidate plans, scoped
source evidence, exact joint beliefs, Ask/Verify with truthful or unresolved
observations, and a common final checker. Required positive **and negative** facts
need public evidence. Conflict prevents commitment. The scalar policy utility is
a declared fixture assumption: maximum expected supported-plan reward, with an
outside option of zero. Conditional and unresolved outputs receive zero in this
initial objective. We do not equate this utility with human burden or food access.

Public state carries no hidden target resource or future answer. The simulator
alone chooses a world. Probabilities and comparisons use rational arithmetic.
The bound uses plans already supported or missing exactly the queried fact;
optional preference contributions use their conservative range. Strict dominance
is the only hard-pruning condition. Unsupported observation models expose an
adaptive-policy fallback; untrusted/incomplete dependency structure uses full VOI.
Certificates expire on any state/query change (conservative invalidation).
Plan caches use scoped evidence and exact marginal fingerprints. Unchanged
conditional marginals may be reused; correlated changes must invalidate them.

## Comparisons and controls

- B1: enumerate one-step outcomes and fully recompute plan values.
- B2: same enumeration with dependency-aware structural/value caches.
- A1: structural interval screening without the cache.
- P: structural interval screening with the cache.
- B3: the **same** generic branch-and-bound implementation as P. Equality is an
  expected negative novelty control, not an independent published reproduction.
- Exact horizon reference: <=8 conditions/queries, horizon <=3; used on small
  complementarity tests, never claimed to be dominated by one-step screening.

The bound's supported-plan set, exact observation probabilities and all cache
lookups, bound visits and certification work are part of measured execution.
Elapsed/CPU timing includes these operations. Structured input generation and
oracle audits are recorded separately. There are no LLM calls to count as saved.
No E3/MAS, published SAGE, second-model or cross-domain result is implied.

## E0 and staged E1

First run correctness checks for evidence, conflicts, scope, guard recovery,
joint dependence, complementarity, bounds, strict ties, version invalidation,
cache/full recomputation, request reuse, interruptions and budget enforcement.
Then run a small development smoke, followed by the fixed 180-instance cross
product in `configs/offline_v0.json`. Three public states per instance use a fixed
collection policy, revealing the first two fields from the simulator's world.
State construction never uses the candidate policy's actions or outcomes.
Each policy has a separate fresh state and its own cache across those states.
Per-instance policy order is shuffled with a fixed seed; no parallel timing.

One necessary specification correction: 128 plans over only four unknown fields
cannot have zero incidental sharing when every plan uses those fields. The
original ratio is operationalized as an **anchor-reuse generator parameter**;
the realized pairwise constraint overlap is reported. Zero means no extra forced
anchor reuse, not a promise of zero overlap. This prevents a fictitious sharing
claim and leaves the prescribed 180-cell grid intact.

Primary diagnostics: exact action equality and regret, all initial-bound
coverage, every pruning certificate, full/cached terminal equality, branch
evaluations, constraint checks, full plan evaluations, bound work, elapsed/CPU
time. P/B2 and P/B3 are both reported. Timing is local algorithm cost, not dollar
cost or full-system latency. A separate optional tracemalloc run measures Python
allocation peaks; its timings are not pooled with primary timing.

No quality/cost success threshold is inferred from a favorable pruning ratio.
If screening saves evaluations but costs more CPU, report the overhead and
continue with a measured implementation optimization, preserving the previous
artifacts. If P equals B3, report that v0 does not demonstrate an independent
method advantage. No main FoodPath test set is used to tune the solver.

Every run gets a new directory, immutable source/config hashes, environment
metadata, raw decisions and witnesses, a verification summary and a completion
status. The runner refuses to overwrite results. Real data qualification is a
separate read-only operation; raw private project artifacts are not copied into
this public repository.
