# Output setting sensitivity

Paired development sensitivity; settings and cached replays are not independent cases or additional base models.

| Setting | Cap | B2 requests | P requests | B2 response errors | B2 no delivery | P/B2 logical cost |
|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-9B | 768 | 128 | 73 | 15 / 52 | 29 / 52 | 0.553 |
| Qwen/Qwen3.5-9B-cap1536 | 1536 | 130 | 76 | 14 / 52 | 31 / 52 | 0.524 |

All settings keep all four states and five methods. A response failure may stop the pipeline early, so a lower request count alone is not better efficiency. P equals B3.
