# Sequential model integration

Supported fixture fallback; completion is an integration result, not operational FoodPath success. Cases are paired across models.

| Model | Method | Cases | Supported | Reward sum | Information actions | Requests | Logical USD |
|---|---|---:|---:|---:|---:|---:|---:|
| deepseek-ai/DeepSeek-V4-Pro-0813 | B1 | 2 | 2 | 19/5 | 3 | 150 | 0.241353 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | B2 | 2 | 2 | 19/5 | 3 | 150 | 0.241353 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | B3 | 2 | 2 | 19/5 | 3 | 33 | 0.049874 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | A1 | 2 | 2 | 19/5 | 3 | 33 | 0.049874 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | P | 2 | 2 | 19/5 | 3 | 33 | 0.049874 |
| gpt-6-luna | B1 | 2 | 2 | 19/5 | 3 | 152 | 0.020151 |
| gpt-6-luna | B2 | 2 | 2 | 19/5 | 3 | 152 | 0.020151 |
| gpt-6-luna | B3 | 2 | 2 | 19/5 | 3 | 33 | 0.004045 |
| gpt-6-luna | A1 | 2 | 2 | 19/5 | 3 | 33 | 0.004045 |
| gpt-6-luna | P | 2 | 2 | 19/5 | 3 | 33 | 0.004045 |

Per-case complete unique request sets; undiscounted usage price, not a bill or cache-order saving.

P remains the same algorithm as B3. Report failures and budget limits alongside request savings; this does not prove multi-step optimality.
