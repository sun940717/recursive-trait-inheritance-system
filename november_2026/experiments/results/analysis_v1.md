# RTIS experiment plan v1: results (X1, X2)

Analysis `analyze_v1.0` · data code_hash `bb54458008ff10be` · Python 3.10.12 · 7650 + 9180 rows, errors: 0

## Confirmatory: PCE vs same-K random, passing

- Delta = **+7.5 pp** (95% CI +5.6 pp to +9.4 pp), sign-flip p < 0.0001
- pairs better / worse / same: 9 / 1 / 5; observations that differ: 185 of 765
- K (non-root pairs matched by PCE), share K = 0: 38.7%, K <= 1: 46.7%; counts {0: 592, 1: 122, 2: 454, 3: 209, 4: 122, 5: 31}
- G5 parts kept, same method (secondary): Delta -0.5 pp (95% CI -0.8 pp to -0.1 pp), p 0.0092
- interpretation rule: **PCE written as better (higher pass rate, parts kept not lower by more than 5 pp)**

| pair | PCE pass | random pass | difference |
|---|---|---|---|
| quadruped x biped | 93.1% | 78.4% | +14.7 pp |
| quadruped x spider | 100.0% | 89.2% | +10.8 pp |
| quadruped x serpent | 96.1% | 85.3% | +10.8 pp |
| quadruped x jellyfish | 68.6% | 68.6% | +0.0 pp |
| quadruped x crab | 100.0% | 99.0% | +1.0 pp |
| biped x spider | 83.3% | 70.6% | +12.7 pp |
| biped x serpent | 100.0% | 70.6% | +29.4 pp |
| biped x jellyfish | 54.9% | 54.9% | +0.0 pp |
| biped x crab | 85.3% | 69.6% | +15.7 pp |
| spider x serpent | 75.5% | 82.4% | -6.9 pp |
| spider x jellyfish | 36.3% | 36.3% | +0.0 pp |
| spider x crab | 97.1% | 77.5% | +19.6 pp |
| serpent x jellyfish | 36.3% | 36.3% | +0.0 pp |
| serpent x crab | 90.2% | 85.3% | +4.9 pp |
| jellyfish x crab | 59.8% | 59.8% | +0.0 pp |

## X2: rules turned off one at a time (vs the full rule set), Holm family of six

| condition | measure | full | condition | Delta | 95% CI | p | Holm p |
|---|---|---|---|---|---|---|---|
| relative_off | bend | 1.601 | 159.458 | +157.857 | +153.804 to +161.899 | < 0.0001 | 0.0003 |
| linkage_off | humps | 0.263 | 1.123 | +0.860 | +0.818 to +0.903 | < 0.0001 | 0.0003 |
| graft_off | kept | 79.6% | 79.2% | -0.4 pp | -0.5 pp to -0.3 pp | < 0.0001 | 0.0003 |
| site_off | buried | 0.107 | 0.389 | +0.282 | +0.259 to +0.305 | < 0.0001 | 0.0003 |
| strict | pass | 78.4% | 78.4% | -0.1 pp | -0.6 pp to +0.5 pp | 1.0000 | 1.0000 |
| attr | hidden | 0.384 | 0.148 | -0.235 | -0.267 to -0.203 | < 0.0001 | 0.0003 |
| site_off | kept (outside family) | 79.6% | 81.9% | +2.3 pp | +2.1 pp to +2.5 pp | < 0.0001 | – |
| strict | kept (outside family) | 79.6% | 79.0% | -0.6 pp | -0.8 pp to -0.4 pp | < 0.0001 | – |

## Every condition, every measure (mean over 15 pairs, equal weight)

| condition | pass | kept | minority | both10 | g1 | buried | hidden | bubbles | bend | humps | parts | m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| random_k | 70.9% | 80.1% | 35.6% | 97.3% | 99.9% | 0.221 | 0.441 | 0.0% | 1.138 | 0.314 | 6.139 | 0.036 |
| pce | 78.4% | 79.6% | 35.6% | 97.1% | 99.9% | 0.107 | 0.384 | 0.0% | 1.601 | 0.263 | 6.104 | 0.013 |
| order | 64.2% | 92.1% | 37.1% | 99.8% | 100.0% | 0.465 | 0.682 | 0.1% | 2.538 | 0.558 | 5.615 | 0.101 |
| root_only | 80.1% | 70.8% | 33.7% | 97.1% | 99.9% | 0.059 | 0.385 | 0.0% | 0.044 | 0.130 | 6.552 | 0.000 |
| shuffled_tags | 71.7% | 79.9% | 35.4% | 97.3% | 99.9% | 0.203 | 0.427 | 0.1% | 0.904 | 0.296 | 6.128 | 0.035 |
| linkage_off | 75.2% | 80.2% | 37.5% | 99.0% | 100.0% | 0.111 | 0.481 | 0.0% | 2.704 | 1.123 | 6.161 | 0.006 |
| relative_off | 75.4% | 80.2% | 38.0% | 99.0% | 100.0% | 0.059 | 0.475 | 0.0% | 159.458 | 1.402 | 6.161 | 0.020 |
| graft_off | 80.5% | 79.2% | 35.4% | 97.1% | 99.9% | 0.107 | 0.331 | 0.0% | 1.601 | 0.263 | 6.063 | 0.013 |
| site_off | 65.2% | 81.9% | 36.7% | 98.4% | 99.9% | 0.389 | 0.550 | 0.0% | 1.601 | 0.264 | 6.320 | 0.235 |
| strict | 78.4% | 79.0% | 35.4% | 97.2% | 99.9% | 0.099 | 0.389 | 0.0% | 1.220 | 0.249 | 6.137 | 0.012 |
| attr | 91.6% | 78.5% | 35.9% | 97.6% | 99.9% | 0.035 | 0.148 | 0.8% | 0.105 | 0.208 | 6.052 | 0.011 |

## Jellyfish split (pre-specified description) / 水母分開描述

| condition | pass, 5 jellyfish pairs | pass, other 10 | kept, jellyfish | kept, other |
|---|---|---|---|---|
| random_k | 51.2% | 80.8% | 72.2% | 84.0% |
| pce | 51.2% | 92.1% | 72.2% | 83.3% |
| order | 53.1% | 69.8% | 87.1% | 94.6% |
| root_only | 51.2% | 94.5% | 72.2% | 70.1% |
| shuffled_tags | 51.2% | 82.0% | 72.2% | 83.8% |
| linkage_off | 44.3% | 90.7% | 72.3% | 84.1% |
| relative_off | 50.0% | 88.1% | 73.3% | 83.6% |
| graft_off | 53.5% | 93.9% | 71.8% | 82.9% |
| site_off | 38.2% | 78.7% | 76.4% | 84.7% |
| strict | 51.2% | 92.0% | 72.2% | 82.4% |
| attr | 82.4% | 96.2% | 74.1% | 80.7% |

minority = share of genes from the parent that gave fewer (50% = even); both10 = children where each parent gave at least 10% of the genes; m3 = old measure, recorded only.
