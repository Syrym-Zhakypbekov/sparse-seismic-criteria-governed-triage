# Plan: analyses answering the fair review panel on v31 (post hoc, method fixed before computing)

Written and pushed before any of the numbers below was computed. Post hoc: every verdict of Section 4 is already known;
these analyses do not change any pre-specified verdict. Frozen decision rules, frozen thresholds, margin 3 points,
ratio criterion 1.5, two-stage cluster bootstrap (networks, then days; 2000 resamples, seed 7) as in
analysis/v2_networks.py. Nothing is downloaded and no pipeline file changes.

Data: the 33 networks scored against analyst-reviewed bulletin events (results/v2_reviewed/v2_eval_reviewed.json), as
re-collected by analysis/posthoc_collect.py (results/posthoc/_collect_reviewed.pkl); per-network shifted-catalogue
chance counts from results/posthoc/chance_by_policy.json (set "reviewed"). Code: analysis/gap_reviewed.py. Output:
results/gap/gap_reviewed.json, figure figures/fig_gap_overlap_loo.png.

Policies: CG (c = 1), CG-D, CG with c = 0.5 (CG_c05), against P3 (7.5 dB).

## G1. Overlap of CG_c05 and P3 (panel A2: "the dismissal region of c = 0.5 nearly coincides with P3")
Descriptive. Over all episodes and over reviewed-associated episodes: 3 x 3 table of actions (alert, dismiss,
escalate) CG_c05 x P3; Jaccard index of the two dismissal sets; episodes dismissed by CG_c05 only and by P3 only, with
the neighbour states (all NO / NO with at least one MISSING) and the reference SNR (median, quartiles). Stated in
advance: if the Jaccard index over all episodes is at least 0.90, the paper says that CG_c05 and P3 dismiss nearly the
same episodes; if it is below 0.90, the paper reports the size and the composition of the difference.

## G2. Chance-corrected endpoint with an interval (panel A4: chance association biases contrasts against the policy that dismisses more)
Per network and policy: dismissed reviewed-associated minus mean chance-dismissed (100 shifts), denominator associated
minus mean chance-associated. Pooled chance-corrected difference policy - P3 in points, with a network bootstrap
(networks resampled; 2000, seed 7; the per-network chance means are fixed). Criterion stated now: upper 95% bound at
most 3 points.

## G3. Sensitivity of the verdicts to the margin and to zero-discordance networks (panel A1)
From the same cluster-bootstrap draws: verdict at margins 2, 3 and 4 points. Then the cluster bootstrap repeated
without the networks where the contrast has zero discordance (identical dismissal decisions on all associated
episodes), so that zero-width network intervals cannot carry the pooled verdict.

## G4. Heterogeneity across networks
Leave-one-network-out: the cluster bootstrap repeated 33 times with one network removed; reported: range of the pooled
difference and of the upper bound, and the number of removals that change a verdict. Also without JP (chance share
above 0.5 in the catalogue labels). Equal-weight mean of per-network differences (already computed by the cluster
bootstrap) reported beside the pooled one.

## G5. Multiplicity over the enlarged family (panel A3)
Family: the nine margin contrasts already adjusted (Appendix B, block 7), the three pooled reviewed-bulletin contrasts
(CG, CG-D, CG_c05 vs P3) and the 99 per-network reviewed contrasts (33 networks x 3). One-sided p for H0: difference
>= 3 points, p = (draws >= 3 + 1)/(draws + 1) (day bootstrap per network, cluster bootstrap pooled; 2000, seed 7).
Holm and Benjamini-Yekutieli adjustments at alpha 0.025. Reported: how many unadjusted "met" verdicts remain met.

## Reporting
Every number is read from results/gap/gap_reviewed.json. Results go to Appendix E of the manuscript, labelled post hoc.
