# Plan (post hoc, method fixed before computing): sensitivity of the reviewed-bulletin verdicts to the hand-set weights and thresholds, and ablation of the sufficiency constraint and the reject band

Written and pushed before any of the analyses below was computed. It answers the reviewer objection that the weights
(SNR 0.40; site weights 0.25 / 0.20 / 0.15 by rank) and thresholds (delta 0.45, theta_A 0.60, theta_D 0.16) were set by hand.
The frozen rules, data and verdicts are not changed. Everything here is post hoc and is reported as such, whatever the outcome.

## Data
The 33 networks scored against analyst-reviewed bulletin events (results/v2_reviewed/v2_eval_reviewed.json), using the
per-network site states, reference SNR, validity flags, days and reviewed-association labels re-collected from the frozen
evaluation by analysis/posthoc_collect.py (cache results/posthoc/_collect_reviewed.pkl). P3 (7.5 dB) actions are the frozen ones.
No waveform is downloaded and no file in pipeline/ is touched.

## Check before the sweep
The re-implemented scorer (analysis/sens_weights.py) must reproduce the frozen actions of CG, CG_c05 and CG-D episode by
episode on all 33 networks at the frozen parameters, and the original cluster bootstrap (2000 replicates, seed 7) must
reproduce the published pooled results (CG 3.89 [2.31, 5.73]; c = 0.5 0.74 [0.25, 1.32]; CG-D 0.97 [0.44, 1.57]).
If either check fails, the sweep is not run and the failure is reported.

## Grid (full factorial, 675 points per policy)
- SNR weight w in {0.30, 0.35, 0.40, 0.45, 0.50}. Site weights are rescaled so that all weights sum to 1, as in the frozen
  rule (0.40 + 0.60). Scaling the three site weights by a common factor (x0.8, x1.2) and renormalising is equivalent to
  changing w, so the site-to-SNR balance is covered by w.
- Site rank gradient g in {0, 1, 2}: unnormalised site weights 0.20 + g x (0.05, 0, -0.05), i.e. flat (0.20, 0.20, 0.20),
  frozen (0.25, 0.20, 0.15) and steep (0.30, 0.20, 0.10), each then rescaled to sum to 1 - w.
- delta in {0.35, 0.40, 0.45, 0.50, 0.55}; theta_A in {0.55, 0.60, 0.65}; theta_D in {0.11, 0.16, 0.21}.
- Policies: CG (c = 1), CG_c05 (c = 0.5), CG-D (development table, unchanged), each against the frozen P3.

## Statistics
Same pooled two-stage cluster bootstrap design (networks with replacement, then days within each drawn network), margin
3 percentage points, ratio criterion (dismissed counts + 0.5) at most 1.5, seed 7. For the grid a vectorised implementation
with 500 replicates is used (lighter, stated); the frozen point is re-run with the original 2000-replicate function.
A grid point "meets" when the upper 95% bound of the pooled difference is at most 3 pp; the ratio criterion is reported separately.

## Outcomes
1. Per policy: share of grid points whose difference verdict equals the frozen verdict (CG not met; CG_c05 met; CG-D met),
   and the same for the ratio criterion.
2. Per policy: worst-case (largest) upper bound of the difference and of the ratio across the grid, with its parameters.
3. One-at-a-time curves (each parameter varied, the others frozen) and a heatmap (w x delta, other parameters frozen).
4. Pooled dismissals, alerts and escalations of reviewed-associated alarms and of all alarms at each grid point (summary).

## Ablations (each against the frozen rule and against P3)
- A1, no sufficiency constraint: delta = 0 (an automatic decision is taken whenever any evidence is present).
- A2, no reject band: a single threshold, alert if D >= theta else dismiss; theta = 0.38 (midpoint of theta_D and
  theta_A), and theta = theta_D and theta = theta_A reported as bounds.
- A3, both removed.
Reported: dismissed / alerted / escalated counts (reviewed-associated and all), the pooled difference to P3 with interval,
and, where relevant, the link to Statement 2 (lowering c cannot create a new automatic dismissal).

## Files
analysis/sens_weights.py; results/sensitivity/sens_weights.json; results/sensitivity/ablations.json;
figures/fig_sens_weights.png. Manuscript: Appendix F of v32 and one or two sentences in the Discussion / Limitations.
