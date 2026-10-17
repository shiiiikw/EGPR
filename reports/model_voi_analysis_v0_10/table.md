# Model VOI development results

Each row aggregates the recorded synthetic development states for that model. These are not independent FoodPath outcomes.

| Model | States | B2 requests | P requests | P/B2 logical cost | B2 no delivery / terminal evaluations |
|---|---:|---:|---:|---:|---:|
| MiniMaxAI/MiniMax-M3 | 4 | 154 | 46 | 0.309 | 26 / 52 |
| Qwen/Qwen3.5-9B | 4 | 128 | 73 | 0.553 | 29 / 52 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | 4 | 156 | 48 | 0.296 | 9 / 52 |
| gpt-4.1-mini-2025-04-14 | 4 | 171 | 51 | 0.281 | 23 / 52 |
| gpt-6-luna | 4 | 157 | 57 | 0.355 | 2 / 52 |
| gpt-6.1-sol | 4 | 156 | 48 | 0.302 | 0 / 52 |
| openai/gpt-oss-120b | 4 | 156 | 48 | 0.299 | 2 / 52 |

All five methods use the same roles and final evidence guard. P and B3 remain the same algorithm; this table does not establish a novelty advantage.

Request counts are summed per state, not new network calls or independent samples. Local cache reuse and provider prompt discounts do not determine the logical cost comparison.

The B2 terminal audit keeps every enumerated branch. No-delivery includes abstention and rejected recovery; the final guard blocks unsupported commitments. These branches are correlated counterfactual evaluations, not an online task-success denominator.
