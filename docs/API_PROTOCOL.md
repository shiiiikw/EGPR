# API campaign: breadth within US$200

The user explicitly authorized **US$200 total new API spending** in chat after
uploading the reference paper. This supersedes the earlier disabled-paid default
for authorized campaign commands. The first development phase stays below US$10.
Configuration is in `configs/api_campaign.json`; all stages share one ledger.
Unused allocation can be reassigned after reporting results, without exceeding
the campaign ceiling. US$200 is a ceiling, not a target to exhaust.

## Reference-paper design

The uploaded [The Average Patient: Do Simulated Psychiatric Patients Answer Like
Real People?](../4760_The_Average_Patient_Do_Si.pdf) is an anonymous ACL submission.
Section 4.2 (p. 4), Appendix C (pp. 13–15), and Table 3 (p. 22) support these
design choices:

- Its main questionnaires cover 17 models, 9 conditions, and 50 trials per
  condition, with item order shuffled. That is 450 trials per questionnaire per
  model, not 50 total. Other experiments use smaller model subsets: 7 for some
  interventions/interviews, 5 for grounded-profile interviews, 2 for robustness.
- It uses short structured answers with validation and typically disables or
  minimizes reasoning, with model-specific exceptions. The providers include
  OpenAI, Azure AI Foundry and Google AI Studio.
- It matches comparisons, separates repeated profiles in folds, reports missing
  outputs, and uses uncertainty estimates. These controls matter as much as the
  number of model names.
- The approximately US$200 figure was supplied by the user. It was not located
  in the PDF; we do not present it as a documented reproduction cost.

We adopt the tiered design, not the psychiatric task or its numeric sample-size
thresholds. A short one-shot questionnaire is cheaper than multi-turn MAS with
counterfactual branches. Pilot token counts will determine the affordable roster.

## Proposed evaluation tiers

1. **Development gate:** eight fixed synthetic evidence cases, two accessible
   OpenAI models, one replicate. Exercise Planner, Reviewer, Coordinator, strict
   guard and one bounded recovery. This is an integration check, not effectiveness
   evidence. It does not measure screening's API savings.
2. **Primary experiment:** two representative model families, full B0/B1/B2/B3/
   B4/A1/P controls where implemented. The shared FoodPath cohort has 43
   provenance groups, not 59 independent cases. Reserve groups and freeze prompts,
   budgets, extraction rules and stopping rules before effectiveness runs. Current
   qualification does not establish an untouched operational holdout.
3. **Breadth:** aim for 6–8 model configurations across distinct families and
   sizes; all receive the same paired cases and at least B2, B3 and P. Additional
   models do not compensate for an inadequate number of independent cases.
4. **Robustness:** selected representative models for extraction corruption,
   unknown/conflicting observations, query complementarity, candidate changes,
   reasoning effort and budget sensitivity. Keep failed or null effects.

No fixed small sample is promised to satisfy reviewers. Report source-group
paired intervals and discordant outcomes. A small cohort may identify large
failures while remaining inconclusive about small quality losses. Repeated seeds
or cached responses do not increase the number of independent source groups.
Current P equals generic B3; model breadth does not establish algorithm novelty.

After the seven-model VOI and two-family sequential gates, extend the original
eight diagnostic role cases to all seven original model configurations using
the existing `development-0` mapping. Reuse completed cases, keep all failures,
and report the full case matrix after the common guard. Do not count the two
Qwen sensitivity settings as additional base models. These eight fixed cases
test scoped evidence, conflict, explicit negative requirements, source correction
and cross-service obligations; they are not a statistical effectiveness sample.

This extension completed 55/56 model/case pairs successfully. MiniMax abstained
on the complete cross-service case after adding an undeclared eligibility
requirement. All other configurations passed the eight fixtures; no case was
replaced or resampled. The full cached replay reused 168 responses with zero
new attempts and identical case traces. See the [complete matrix](../reports/role_pilot_analysis_v0_11/table.md).

Seven configurations have completed the four-state development comparison:
GPT-6 Luna, dated GPT-4.1 Mini, GPT-6.1 Sol, Qwen3.5-9B, MiniMax M3,
DeepSeek V4 Pro 0813 and GPT-OSS 120B. GPT-4.1 Mini is deprecated in current
documentation and remains a development comparison. Luna and DeepSeek were
selected for the next sequential integration before inspecting DeepSeek's VOI
results; the formal primary roster is not yet frozen. Generation settings and
output caps differ by model and are recorded, so this is not a controlled study
of architecture alone. The Qwen 1,536-token variant is a sensitivity setting,
not an eighth foundation model. See the [paired results](../reports/model_voi_analysis_v0_10/table.md).

Together metadata retrieval initially returned HTTP 403 with the standard
library transport. Its official SDK 2.41.0 successfully listed models, so the
transport uses that SDK with automatic retries disabled. Earlier HTTP 402
`credit_limit` failures remain recorded. The replacement credential supplied by
the user then passed two diagnostic cases on each of the four Together models.
No credential is stored in this repository.

The first model-VOI queue completed Qwen and stopped on a MiniMax HTTP 429
`rate_limit`. This was a transient request-rate error. After a recorded cooldown,
the operator explicitly resumed with two-second request-start spacing. Failed
receipts and unresolved cost reservations were retained; successful exact
requests were reused. Ordinary model-output failures are never resampled.
The new queue uses the original model roster, states and replicate identity.
Rate-limit response headers are recorded with an allowlist; authorization and
cookie headers are excluded. No larger experiment budget or provider switch
was needed.

## Cache and accounting

- Hash provider, exact endpoint/model selector, full messages, tools, schema,
  generation parameters and replicate identity. Reuse only exact requests, across
  methods and runs. Persist returned model ID and provider request ID.
- Intentionally independent replicates have distinct IDs. Identical cached
  responses are shared computation, never extra independent observations.
- Persist the raw response before validating JSON/schema. Truncation, refusal,
  malformed output and HTTP errors survive restart. No automatic resampling of
  failures and no automatic network retries. This avoids hidden survivor bias.
- Use one locked append-only campaign ledger. Persist each reservation before
  sending; unknown outcomes retain it. Concurrent writers are rejected. A provider
  receipt is required to reconcile unknown spending.
- API token usage times a frozen price is a **cost estimate**, not a bill.
  `billed_usd` stays null until a real receipt is available. Budget occupancy uses
  conservative estimates plus unresolved reservations. Record uncached logical
  cost separately from actual new network calls and provider prompt-cache usage.
- Reserve the full documented context at the maximum applicable tariff, with a
  hard output cap. Current standard-price configurations exclude paid hosted
  tools. Backend latency and zero-call cache replay latency must not be pooled.

Primary API sources checked 2026-10-17:
[OpenAI chat API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[GPT-4.1 Mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Together model catalog](https://docs.together.ai/docs/serverless/models),
[Together structured output](https://docs.together.ai/docs/inference/chat/structured-outputs),
[Together API key identity](https://docs.together.ai/reference/whoami),
[Together billing usage](https://docs.together.ai/reference/billing-usage).
The billing-usage API is organization-enabled beta and is not a remaining-credit
balance endpoint. An unavailable response cannot be interpreted as zero balance.

## Run the development gate

```sh
uv run python scripts/run_role_pilot.py --output results/role-pilot-dry
# Uses the explicitly authorized campaign budget; credentials are read from env.
uv run python scripts/run_role_pilot.py --allow-paid --output results/role-pilot-1
```

The default rejects cache misses requiring payment. Optional `--credentials`
accepts a local assignment file, parsed without shell execution. Never commit it.
Every run needs a new output directory; the shared ledger enables exact replay.
Raw model responses and private source data remain under ignored `results/`.
