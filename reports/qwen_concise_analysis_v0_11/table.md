# Model VOI development results

Each row aggregates the recorded synthetic development states for that model. These are not independent FoodPath outcomes.

| Model | States | B2 requests | P requests | P/B2 logical cost | B2 no delivery / terminal evaluations |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B-concise-v1 | 4 | 156 | 102 | 0.649 | 46 / 52 |

All five methods use the same roles and final evidence guard. P and B3 remain the same algorithm; this table does not establish a novelty advantage.

Request counts are summed per state, not new network calls or independent samples. Local cache reuse and provider prompt discounts do not determine the logical cost comparison.

The B2 terminal audit keeps every enumerated branch. No-delivery includes abstention and rejected recovery; the final guard blocks unsupported commitments. These branches are correlated counterfactual evaluations, not an online task-success denominator.
