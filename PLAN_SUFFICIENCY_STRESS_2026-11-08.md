# Plan (post hoc, written and pushed before computing): evidence-sufficiency stress test

Question (final cold review, M2): delta = 0.45 almost never binds on the archive, so is the sufficiency constraint
inert? It binds only when neighbour evidence is thin, and thin evidence is rare in the archive (3,062 of 263,303
episodes have at least two of the three neighbour sites MISSING). This plan tests the constraint where it is meant
to work: on the same episodes with neighbour evidence removed at controlled rates, and on the real thin subset.

Data: the 33 reviewed-bulletin networks (results/posthoc/_collect_reviewed.pkl, analysis/posthoc_collect.py;
263,303 episodes, 4,321 reviewed-associated). Frozen rule v2 otherwise (site weights 0.25/0.20/0.15, SNR weight 0.40,
theta_A 0.60, theta_D 0.16). Nothing in pipeline/ is used or changed. Descriptive and post hoc.

## A. Controlled evidence loss
Masking turns a neighbour-site state (YES or NO) into MISSING. The reference-station SNR is never masked.
- independent: each site state of each episode is masked with probability p;
- correlated: each (network, site, calendar day) is an outage with probability p; every episode of that site on
  that day becomes MISSING (whole-day outages, the realistic failure mode).
- p in {0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7}; masking seeds 7..56 (50 replicates per p and mode).

Rules on the masked states: P1 (classic coincidence), P3 (7.5 dB), P3-2t (8.0 / 13.5 dB, the training-chosen
two-threshold rule of review4), CG (c = 1), CG c = 0.5 and CG-D, each criteria-governed rule with delta in {0, 0.45, 0.55}
(delta = 0 means only den > 0 is required).

Outcomes per rule, p, mode and seed: reviewed-associated alarms dismissed (count and share of 4,321); unassociated
alerts; escalations; and the share of automatic decisions (alert or dismiss) resting on fewer than two evidence
sources, where the sources are the reference station (if its SNR is defined) and each neighbour site with YES or NO.

Uncertainty: for every seed, the pooled two-stage cluster bootstrap (networks, then days; 500 draws, seed 7) of the
statistic; the 50 x 500 values are pooled, and the 2.5 and 97.5 percentiles are reported (masking and sampling
variability together). The point value is the mean over seeds.

Hypotheses (one-sided, stated before computing):
- S1, missing is not negative: at independent p = 0.5, P1 dismisses a larger share of reviewed-associated alarms than
  CG c = 0.5 with delta = 0.45. Holds if the lower 2.5 percentile of P1 minus CG c = 0.5 is above 0. Reported for CG
  and CG-D too.
- S2, the sufficiency constraint matters when evidence is thin: at independent p = 0.5, CG c = 0.5 with delta = 0
  dismisses a larger share of reviewed-associated alarms than with delta = 0.45. Holds if the lower 2.5 percentile of
  (delta 0 minus delta 0.45) is above 0. The extra escalations of delta = 0.45 are reported as its cost.
- S3, graceful degradation against the matched comparator: from p = 0 to p = 0.5 (independent), the rise in the
  dismissed share of reviewed-associated alarms is smaller for CG c = 0.5 (delta 0.45) than for P3-2t. Holds if the
  upper 97.5 percentile of (rise CG c = 0.5 minus rise P3-2t) is below 0. Same comparison against P3 reported.
The same three statistics are reported for correlated masking (secondary) and for every p (curves).

## B. Real thin evidence
The episodes of the unmasked archive with at least two of the three neighbour sites MISSING (3,062). Per rule and
delta: dismissed reviewed-associated, unassociated alerts, escalations, automatic decisions on fewer than two sources;
cluster bootstrap (2000, seed 7) of P1 minus CG c = 0.5 and of CG c = 0.5 delta 0 minus delta 0.45. Descriptive.

Compute: VM p10-seismic (e2-standard-8), 8 worker processes; the VM is stopped after the run.
Outputs: results/sufficiency/stress.json, results/sufficiency/thin_subset.json, results/sufficiency/vm.log,
figures/fig7_sufficiency.png. Reported whatever the outcome.
