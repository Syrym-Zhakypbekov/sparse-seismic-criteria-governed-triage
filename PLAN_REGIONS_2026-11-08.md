# Plan: per-region stratification of the 38-network test (post hoc, method pre-specified here)

Written 2026-11-08 and pushed BEFORE any per-region number is computed. This is a post-hoc stratification of existing
results: it adds no hypothesis to the confirmatory family and changes no primary verdict. Purpose: show whether the pooled
results hold outside the USA, answering the reviewer question "mostly US networks".

## Strata (fixed, no reassignment)
- The `region` field of each network in `results/v2/network_check.json`, written by the selection rule
  (`SELECTION_RULE_V2_2026-11-08.md`) before any scoring. No network is moved between regions.
- Two aggregates:
  - (a) outside `USA-Mexico`;
  - (b) outside North America (`USA-Mexico` + `Alaska-Aleutians-Canada`).

## Label sets and network sets
1. **Catalogue labels:** the 38 networks of `results/v2/v2_eval_AB.json`, with the included set as scored there.
2. **Reviewed-bulletin labels:** the 33 networks included in `results/v2_reviewed/v2_eval_reviewed.json`. Labels are as in
   `analysis/v2_reviewed_bulletin.py`; the decisions are frozen.

## Quantities per stratum and label set
- For P1, P3, CG, CG-D and CG c = 0.5: the pooled share of associated episodes dismissed (%), the number of networks and
  the number of associated episodes.
- For CG, CG-D, CG c = 0.5 and P1, the difference from P3, using `v2_networks.cluster_boot` unchanged:
  - two-stage cluster bootstrap, 2000 draws, seed 7;
  - margin 3 pp, ratio criterion 1.5.
- A stratum with one network reduces to a day bootstrap within that network; such strata are flagged.
- All results are descriptive. No multiplicity correction is applied, and a stratum result is not a confirmatory test.

## Outputs
`analysis/posthoc_regions.py` → `results/posthoc/regions.json` and `figures/fig_regions.png` (600 dpi).
When the 12-month batch-B data (`runs_ext12B`) is scored, the analysis is rerun on it and reported as a separate block.
