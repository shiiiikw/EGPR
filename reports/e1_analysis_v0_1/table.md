# Stratified offline timing

Fixed synthetic grid and five RNG seeds; descriptive ratios, not human-population confidence intervals.

Ratios below 1 favor P. All methods are paired on the same instance.

| Plans | Conditions | Instances | CPU P/B1 | CPU P/B2 | CPU P/B3 | CPU P/A1 |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 4 | 20 | 1.223 | 0.878 | 0.995 | 1.209 |
| 8 | 8 | 20 | 0.973 | 0.774 | 0.997 | 1.132 |
| 8 | 12 | 20 | 0.809 | 0.772 | 0.994 | 1.022 |
| 32 | 4 | 20 | 1.638 | 0.905 | 0.994 | 1.427 |
| 32 | 8 | 20 | 1.183 | 0.754 | 0.996 | 1.355 |
| 32 | 12 | 20 | 0.852 | 0.761 | 0.996 | 1.085 |
| 128 | 4 | 20 | 2.280 | 1.042 | 1.009 | 1.689 |
| 128 | 8 | 20 | 1.687 | 0.872 | 0.993 | 1.640 |
| 128 | 12 | 20 | 0.960 | 0.754 | 1.000 | 1.266 |

P and B3 execute the same algorithm in this stage. Their small timing
differences are measurement/order effects, not a method advantage.
