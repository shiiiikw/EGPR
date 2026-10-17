# Frozen-response model VOI development pilot

This extends the finite solver's terminal evaluator to the actual guarded
Planner–Reviewer–Coordinator API pipeline. Every counterfactual terminal
evaluation can incur three model calls and at most one guard-recovery call.
The current bank is synthetic, has fixed candidates, and uses a declared joint
Boolean belief. This is an E2 integration pilot, not a FoodPath effectiveness test.

## Correctness boundary

The original finite solver returns the best admissible plan deterministically.
An LLM may instead choose a lower-reward plan, fail JSON validation, or refuse.
Its lower terminal bound must therefore be **zero**, including states where a
valuable plan is publicly supported. The upper bound remains the maximum fixed
nonnegative reward achievable among plans supported in that observation branch.
This follows from the mandatory final evidence checker, not model confidence.
Preference bonuses are excluded from this initial model-evaluator contract.

The shared cache freezes each full request's response for a replicate. The VOI
objective then integrates over the declared finite observation outcomes, with
that response mapping fixed. Certificates are exact only for this modeled
one-step objective, conditional on the frozen responses. They do not prove
optimality for fresh stochastic API draws, unmodeled observation probabilities,
incorrect extraction, expanded candidate pools, or a multi-step objective.

Certificates carry a value-model fingerprint covering model configuration,
replicate ID and role/parser implementation. A certificate for one model cannot
validate against another evaluator merely because the public state is unchanged.

The 27-state adversarial test deliberately returns suboptimal or missing model
plans. All bounds must still cover the resulting terminal values and all five
policies must agree. JSON failures count as zero terminal reward without buying a
replacement response. Access/quota/transport failures stop the run; they are not
scored as a completed ineffective policy.

## Comparisons and accounting

All B1/B2/B3/A1/P methods receive identical roles, full public state, schema,
failure handling, generation limits, checker and recovery. B2 enumerates the
one-step oracle for the same frozen model mapping. Every available interval and
certificate is audited against it. P and B3 are still algorithmically identical.

Methods share exact model-response caching. Their execution order is shuffled
per model and state. **Later methods' cache-hit bills and replay wall time are
not evidence of an efficiency advantage.** Report these separately:

- Actual new campaign API attempts, cache hits and usage-based cost estimates.
- Each method's unique request set and the estimated cost of executing that set
  once from an empty local response cache, using the recorded responses' usage.
- Structural bound visits, branch evaluations, cache work, certificates and all
  failed outputs. Logical requests are not independent experimental samples.

Provider prompt-cache discounts observed in a receipt may depend on the shared
run order. The recorded estimate is therefore not a randomized cold-provider
cost measurement; undiscounted logical token cost should accompany formal claims.
No end-to-end latency comparison is inferred from this replay pilot.

```sh
uv run python scripts/run_model_voi.py --allow-paid --cases 2 \
  --output results/model-voi-dev
# Same bank, models and replicate; requires no credentials or new payment.
uv run python scripts/run_model_voi.py --cases 2 \
  --output results/model-voi-dev-replay
```

Use `--models` to select documented configurations. Additional independent
replicates require a different `--replicate-id`, an explicit experiment purpose,
and available campaign budget. They do not enlarge the independent case count.

## Development output-cap diagnostic

The four-state Qwen3.5-9B run at 768 output tokens produced 15 response errors
and 29 no-delivery outcomes among 52 B2 terminal evaluations. Inspection found
visible-output truncation with reported reasoning-token usage zero. Before
running a cap variant, the extension was fixed to **all four original states**
and all five methods, with a 1,536-token cap and otherwise unchanged parameters.
Both configurations remain reported, including every failure. The higher cap
is not an automatic retry, a new foundation model, or an independent replicate.
It changes the complete request key, so it cannot reuse a response from the
768-token request. The configured name is `Qwen/Qwen3.5-9B-cap1536`.

Completion counts must accompany request reductions: a truncated Planner can
terminate a pipeline early and make it appear cheaper. The output audit records
unique B2 requests, finish reasons, parse failures, output caps and reported
reasoning tokens. Missing usage fields are not silently interpreted as zero.

The completed cap comparison found 14 response errors and 31 no-delivery
outcomes at 1,536 tokens, versus 15 and 29 at 768. Both used 52 B2 terminal
evaluations. See the [paired table](../reports/qwen_caps_comparison_v0_10/table.md).
The resulting [concise-output diagnostic](OUTPUT_STYLE_DIAGNOSTIC.md) is a
separate prompt setting with unchanged role schemas and full public context.
