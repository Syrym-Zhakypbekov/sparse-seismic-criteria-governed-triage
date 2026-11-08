# Plan: analyst workload and cost-matched comparison (post hoc, method pre-specified here)

Written 2026-11-08 and pushed BEFORE the numbers below are computed. `results/posthoc/workload_33net.json` already gives
the raw action counts of the 33 reviewed-included networks; this plan adds rates, analyst minutes and the cost-matched
comparison. It is post hoc and changes no primary verdict.

## Workload at the frozen operating points
Network sets: the 33 reviewed-included networks, and also the 38 catalogue-included networks.

Per network and pooled, for P1, P3, CG, CG-D and CG c = 0.5:
- escalations per day;
- analyst minutes per day at 2 min per escalation (the value stated in `PREREGISTRATION_PROSPECTIVE_OSF_DRAFT.md`);
- automatic alerts per day and their reviewed-associated share (alert precision);
- dismissed reviewed-associated episodes.

Pooled values are totals over networks divided by total network-days.

## Cost-matched comparison (operating-point sweep; the decision rules are otherwise frozen)
- **CG family:** the weight c of a valid non-confirmation in {0, 0.1, ..., 1.0}. c = 1 is CG; c = 0.5 is CG c = 0.5.
- **P3 family:** the SNR threshold t in {5.0, 5.5, ..., 12.0} dB. t = 7.5 is P3.
- For every point, pooled over the 33 networks: escalations per network-day, dismissed reviewed-associated share,
  automatic alerts per network-day, and alert precision.
- **Matched pairs:** for CG c = 0.5 and for CG-D, take the P3 threshold whose pooled escalations per network-day is closest
  to theirs. For each pair, compute the difference in dismissed reviewed-associated share with `v2_networks.cluster_boot`
  (2000 draws, seed 7).
- All results are descriptive. The sweep describes an operating curve; it is not a new confirmatory test.

## Outputs
`analysis/posthoc_workload.py` → `results/posthoc/workload.json` and `figures/fig_workload.png` (600 dpi).
The analysis is rerun on `runs_ext12B` when that data is scored.
