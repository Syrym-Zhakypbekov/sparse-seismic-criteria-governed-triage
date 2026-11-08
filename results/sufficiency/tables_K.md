Table K1. Evidence-sufficiency stress test on the 33 reviewed-label networks (263,303 episodes, 4,321 reviewed-associated): share of reviewed-associated alarms dismissed without masking and with half of the neighbour-site states set to MISSING (independently per episode and site, or as whole-day site outages), and, for independent masking at p = 0.5, automatic alerts without a reviewed event, escalations and the share of automatic decisions resting on fewer than two evidence sources. Columns 3 and 5–7: independent masking at p = 0.5; column 4: whole-day site outages at p = 0.5. Masked values are means over 50 masking seeds. Post hoc (results/sufficiency/stress.json).

| Rule | Dismissed (%), p = 0 | Dismissed (%), p = 0.5 | Dismissed (%), outages p = 0.5 | Alerts without a reviewed event | Escalations | On < 2 sources (%) |
|---|---|---|---|---|---|---|
| P1 (classic coincidence) | 10.37 | 31.50 | 31.31 | 21,676 | 0 | 14.4 |
| P3 (7.5 dB) | 3.49 | 5.85 | 5.84 | 14,466 | 116,689 | 13.0 |
| P3-2t (8.0 / 13.5 dB) | 4.05 | 6.92 | 6.88 | 6594 | 115,797 | 13.9 |
| CG, c = 1, δ = 0.45 | 7.38 | 5.68 | 5.67 | 8799 | 126,791 | 0.0 |
| CG, c = 0.5, δ = 0 | 4.24 | 3.69 | 3.69 | 15,992 | 138,172 | 10.6 |
| CG, c = 0.5, δ = 0.45 | 4.24 | 3.33 | 3.31 | 12,745 | 151,543 | 0.0 |
| CG, c = 0.5, δ = 0.55 | 4.24 | 1.96 | 1.96 | 9375 | 192,473 | 0.0 |
| CG-D, δ = 0 | 4.47 | 3.80 | 3.81 | 13,570 | 139,305 | 10.7 |
| CG-D, δ = 0.45 | 4.47 | 3.44 | 3.43 | 10,322 | 152,676 | 0.0 |

Table K2. Pre-stated contrasts of the stress test (percentage points; mean over 50 masking seeds, 95% interval from the 50 × 500 pooled two-stage cluster-bootstrap values). S1: P1 minus the criteria-governed rule (δ = 0.45). S2: c = 0.5 with δ = 0 minus δ = 0.45. S3: rise in the dismissed share from p = 0 to p = 0.5, c = 0.5 (δ = 0.45) minus the comparator.

| Contrast | Independent, p = 0.5 | Whole-day outages, p = 0.5 |
|---|---|---|
| S1: P1 − CG c = 0.5 | 28.17 [24.13, 32.46] | 28.00 [23.39, 32.86] |
| S1: P1 − CG c = 1 | 25.83 [22.20, 29.62] | 25.64 [21.38, 30.08] |
| S1: P1 − CG-D | 28.07 [24.08, 32.30] | 27.89 [23.30, 32.69] |
| S2: δ = 0 − δ = 0.45 (c = 0.5) | 0.37 [0.08, 0.88] | 0.38 [0.07, 0.90] |
| δ = 0.55 − δ = 0.45 (c = 0.5) | −1.37 [−2.60, −0.55] | −1.36 [−2.61, −0.55] |
| S3: rise, c = 0.5 − P3-2t | −3.78 [−5.47, −2.32] | −3.75 [−5.56, −2.26] |
| S3: rise, c = 0.5 − P3 | −3.26 [−4.82, −1.94] | −3.27 [−4.92, −1.91] |

Table K3. The real thin subset: episodes of the unmasked archive with at least two of the three neighbour sites missing (3062 episodes on 16 networks). Post hoc (results/sufficiency/thin_subset.json).

| Rule | Dismissed reviewed-associated | Automatic alerts without a reviewed event | Escalations | Automatic decisions on < 2 sources |
|---|---|---|---|---|
| P1 (classic coincidence) | 9 of 35 | 335 | 0 | 128 |
| P3 (7.5 dB) | 1 of 35 | 168 | 1792 | 6 |
| P3-2t (8.0 / 13.5 dB) | 1 of 35 | 87 | 1844 | 6 |
| CG, c = 1, δ = 0.45 | 0 of 35 | 140 | 1895 | 0 |
| CG, c = 0.5, δ = 0 | 0 of 35 | 262 | 1854 | 62 |
| CG, c = 0.5, δ = 0.45 | 0 of 35 | 230 | 1916 | 0 |
| CG, c = 0.5, δ = 0.55 | 0 of 35 | 96 | 2946 | 0 |
| CG-D, δ = 0 | 0 of 35 | 219 | 1914 | 62 |
| CG-D, δ = 0.45 | 0 of 35 | 187 | 1976 | 0 |
