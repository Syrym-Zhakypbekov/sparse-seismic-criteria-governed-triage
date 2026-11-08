# Plan (post hoc, method fixed before computing): detection-probability likelihood baseline with a reject band

Date: 2026-11-08. Written and pushed before the baseline is fitted or scored.
Motivation: review panel on v32 (C:/review_p10/cold_v32_0811, reviewer F, item 5). The closest prior work, Cohen et al. [42],
separates inactive, detecting and non-detecting stations and weights a non-detection by the station's detection probability
inside a likelihood score. NET-VISA (Arora, Russell & Sudderth 2013, doi:10.1785/0120120107) uses station detection
probabilities in a Bayesian network-processing model. Neither had been compared head to head with the criteria-governed rules.
This is a post hoc comparison; it changes no pre-specified verdict.

## Baseline LLR (naive-Bayes posterior log-odds, three actions)
For an alarm episode with reference SNR s (valid flag ok) and up to three neighbour sites at rank r (merged as in rule v2;
state YES, NO or MISSING):

  L(x) = logit P0(event | s, ok) + Σ_{r: YES} log(Pd_r(x) / Pf_r(x)) + Σ_{r: NO} log((1 − Pd_r(x)) / (1 − Pf_r(x)));
  MISSING contributes 0.

- Pd_r(x) = P(site r says YES | catalogue-associated episode, x): logistic regression on (SNR feature, SNR-valid flag,
  log10 site distance), the same SNR and distance features as c_j(x) (analysis/context_c.py).
- Pf_r(x) = P(site r says YES | unassociated episode, x): the same logistic form fitted on unassociated episodes. This is the
  per-site false-trigger rate as a function of x. The tuning-week trigger counts are missing in most tune logs (context-c
  deviation D1), so they are not used.
- P0(event | s, ok): logistic regression of catalogue association on (SNR feature, SNR-valid flag).
- All three models are fitted on the training data of the context-c test only: IU.MAKZ development period + batch-A networks
  AU AV C1 IV KR OH, with catalogue association. No reviewed label and no test network enters any fit. Probabilities are
  clipped to [0.01, 0.99].
- Actions: dismiss if L ≤ t_D, alert if L ≥ t_A, escalate otherwise.

## Thresholds
- LLR-T (primary): (t_D, t_A) set on the TRAINING data so that the training dismiss share and alert share of the baseline
  equal those of CG with c = 0.5 on the same training data. The thresholds are frozen before any test episode is scored.
- LLR-M (secondary, descriptive): (t_D, t_A) set on each test set so that the pooled numbers of escalations and of automatic
  alerts equal those of CG c = 0.5 on that set. This is an equal-budget comparison and is labelled as using the test set.

## Test sets
- T1 (primary): the 26 batch-B networks included in the reviewed-bulletin evaluation (out of sample for every fitted model,
  as in the context-c test).
- ALL33 (secondary): the 33 networks of the reviewed-bulletin evaluation. Six of them are training networks; this is stated.
Labels: reviewed-bulletin association (analysis/v2_reviewed_bulletin.py relabelling, unchanged).

## Outcomes
- Dismissed reviewed-associated alarms: LLR − P3, LLR − CG c = 0.5, LLR − CG-D, LLR − CG-ctx. Pooled two-stage cluster
  bootstrap, 2000 resamples, seed 7, 3-point margin, ratio bound 1.5 (analysis/v2_networks.cluster_boot, unchanged).
- Per policy (P1t, P3, CG c = 1, CG c = 0.5, CG-D, CG-ctx, LLR-T, LLR-M): dismissed reviewed-associated alarms, unassociated
  automatic alerts, escalations, total analyst items (alerts + escalations), and queue precision (reviewed-associated
  escalations / escalations).
- Self-check: the CG c = 0.5, CG-D and CG-ctx actions computed here must equal those of results/context_c (T1) episode by
  episode.

## Reporting
Every result is reported whatever it is. If the likelihood baseline dismisses fewer reviewed-associated alarms at an equal or
smaller analyst budget, the paper says so and frames its own contribution as the empirical evaluation of reliability-weighted
discounting with a sufficiency constraint and a reject option, not as a better classifier.
Code: analysis/detprob_baseline.py. Output: results/detprob/detprob.json.
