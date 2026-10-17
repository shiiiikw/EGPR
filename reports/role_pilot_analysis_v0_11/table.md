# Guarded evidence fixture matrix

Fixed synthetic evidence fixtures after the common guard and bounded recovery; not raw model accuracy or operational effectiveness

| Model | Correct / cases | Response errors | Initial guard rejections | Final guard rejections |
|---|---:|---:|---:|---:|
| gpt-6-luna | 8 / 8 | 0 | 0 | 0 |
| gpt-4.1-mini-2025-04-14 | 8 / 8 | 0 | 0 | 0 |
| gpt-6.1-sol | 8 / 8 | 0 | 0 | 0 |
| Qwen/Qwen3.5-9B | 8 / 8 | 0 | 0 | 0 |
| MiniMaxAI/MiniMax-M3 | 7 / 8 | 0 | 0 | 0 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | 8 / 8 | 0 | 0 | 0 |
| openai/gpt-oss-120b | 8 / 8 | 0 | 0 | 0 |

A guarded correct abstention can follow a rejected unsupported proposal; guard rejection counts are retained.

The same declared cases are shared across all models. Previously cached cases are reused, not counted as additional independent observations.
