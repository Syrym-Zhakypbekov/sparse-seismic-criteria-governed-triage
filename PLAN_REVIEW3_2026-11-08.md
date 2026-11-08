# Plan: literature-anchored analyses (post hoc, method fixed before computing)

Date: 2026-11-08. Pushed before any of the three analyses below is computed. Script: `analysis/review3.py`.
Outputs: `results/review3/detprob_schorlemmer.json`, `results/review3/costopt_thresholds.json`,
`results/review3/draelos_screen.json`. Sources of the ideas: `LITERATURE_SCOUT_2026-11-08.md` (Ideas 1-3).
All three are post hoc and descriptive. Existing outputs only; no waveform download; `pipeline/` untouched.
Machine: the laptop (the work is light; no VM or Kaggle needed).

Common data. The 33 reviewed-label networks of the frozen reviewed-bulletin evaluation (cached collector
`analysis/posthoc_collect.py`, labels "reviewed"). Training set = the seven batch-A networks (AU AV C1 IV JP KR OH);
test set = the 26 batch-B networks (T1 of the context-dependent reliability analysis). Decision rules unchanged.

## 1. detprob_schorlemmer (Schorlemmer & Woessner 2008 style detection probability)

For every catalogue-associated episode and every neighbour site in state YES or NO, the outcome is y = 1 if the site
confirmed (YES). Covariates of the associated catalogue event: magnitude M and log10 of the event-to-site epicentral
distance (km; the nearest member of a merged site). Two estimators fitted on the training networks only:
(a) logistic regression y ~ M + log10 d + rank indicators; (b) the binned empirical table P(YES | M bin, distance bin)
(M bins <2, 2-3, 3-4, 4-5, >=5; distance bins <100, 100-300, 300-1000, 1000-3000, >=3000 km; cells with fewer than 20
training pairs fall back to the logistic estimate). Evaluated on the test networks (catalogue association, the same
episodes as T2) against: the context-dependent c_j(x) (refitted exactly as in analysis/context_c.py), the CG-D table and
c = 0.5. Reported: Brier score, ECE (10 bins), Pearson and Spearman correlation of each estimator with c_j(x), mean
absolute difference, and reliability bins. Note fixed in advance: M and d come from the catalogue, so this estimator is
a reference quantity, not a decision-time input.

## 2. costopt_thresholds (Chow / Fumera cost-optimal multi-threshold reject rule)

Neighbour-state pattern = counts (nYES, nNO, nMISSING) over the three sites (10 patterns). Within each pattern the rule
is: dismiss if SNR < t_D, alert if SNR >= t_A, escalate otherwise (t_D <= t_A, grid 0-30 dB in 0.5 dB steps, plus the
choice of a single action for episodes with undefined SNR). Cost per episode, in analyst minutes: escalation 2, alert
review 1, a dismissed reviewed-associated alarm k, with k in {30, 60, 120, 240}. Thresholds chosen on the training
networks to minimise total cost; evaluated on the test networks. Reported per k: test cost per network-day of the
cost-optimal rule, of CG c = 1, CG c = 0.5, CG-D, P3 and P1t; the per-pattern optimal thresholds; and, for each
pattern, the SNR at which the frozen CG rules dismiss and alert (derived by scanning SNR at fixed states), with the
distance in dB to the optimum. A cluster bootstrap (networks, then days; 1000 resamples, seed 7) of the cost
difference CG c = 0.5 minus cost-optimal.

## 3. draelos_screen (Draelos et al. 2012 style false-event screening)

Cells = neighbour-state pattern by site rank (3^3 = 27 states) x reference-SNR bin (<5, 5-10, 10-15, 15-20, >=20 dB,
undefined). From the training networks only, the reviewed-association rate of each cell. Rule: dismiss cells with rate
<= r_lo (and at least 30 training episodes), alert cells with rate >= r_hi that contain a YES, escalate the rest; cells
unseen in training are escalated. (r_lo, r_hi) chosen on the training networks from r_lo in {0.001, 0.002, 0.005, 0.01,
0.02, 0.05} and r_hi in {0.05, 0.1, 0.2, 0.3, 0.5}: among pairs whose training escalation count is within 10% of that of
CG c = 0.5, the pair with fewest dismissed reviewed-associated alarms. Evaluated on the test networks against CG c = 0.5,
CG-D, P3 and the two-threshold P3 (8.0/13.5 dB, results/posthoc/twothreshold.json): dismissed reviewed-associated
alarms, unassociated alerts and escalations; cluster bootstrap (2000, seed 7) of screen minus CG c = 0.5 and minus P3.

Results are reported whatever they are.
