# Pre-registration: context-dependent reliability of a non-confirming neighbour, c_j(x)

Written and pushed on 2026-11-08 BEFORE the model below was fitted or any decision with it was scored.
Uses only pipeline outputs that already exist in this repository; no waveform, catalogue or label is downloaded.
The decision rule, its weights and thresholds stay frozen; only the weight of a valid NO changes.

## 1. Question

In the frozen rule (rule v2), a valid non-confirming site (NO) enters the evidence weight with reliability c.
CG uses c = 1, CG_c05 uses c = 0.5, CG-D uses the IU.MAKZ development table (site rank x SNR bin).
Here c becomes a function of the context known at decision time:

    c_j(x) = P(site j confirms | the reference episode is a catalogued event, x),
    x = (SNR_ref, d_j, N_j, H_j)

A NO then counts strongly when site j would very probably have seen the event, and weakly when it might have missed it.

## 2. Features (all available at decision time; the catalogue is used only as the training label)

Per (reference episode, neighbour site j), sites merged by rule v2 (members within 50 km; YES if any member YES,
NO if no member YES and at least one NO, MISSING otherwise); at most three sites, nearest first.

- `snr`: reference SNR in dB clipped to [0, 40] and divided by 40; 0 when SNR is undefined, with flag `snr_ok`.
- `logd`: log10 of the site distance to the reference in km (site distance = nearest member, from the configuration).
- `thr`: noise proxy 1, mean over members of the STA/LTA 99.9th-percentile threshold of the member, computed by the frozen
  pipeline on the tuning week before the evaluation period (v2 networks: tune run summary; IU.MAKZ development: summary).
- `lrate`: noise proxy 2, mean over members of log((own triggers + 1) / (reference triggers + 1)) on the same tuning week.
- `hist`: H_j, causal history of the site: (YES + 1) / (valid + 2) over all EARLIER reference episodes of the same
  network in which the site was valid (no catalogue information), entered as its logit.

## 3. Model

Logistic regression (scikit-learn LogisticRegression, L2, C = 1.0, lbfgs, features standardised on the training set),
target 1 = site YES, 0 = site NO, fitted on training pairs: reference episodes associated with the pipeline catalogue
(assoc_event >= 0) and site valid. c_j(x) = predicted probability, clipped to [0.05, 1.0].
CG-ctx = rule v2 with q = c_j(x) for a valid NO; YES q = 1, MISSING q = 0; weights 0.25 / 0.20 / 0.15 by site rank,
SNR 0.40; theta_A 0.60, delta 0.45, theta_D 0.16 (identical code path to CG-D, only the NO weight differs).
Self-check before scoring: the same code with q = 0.5 must reproduce CG_c05 and with the development table must reproduce
CG-D of analysis/v2_networks.py on every network, episode by episode.

## 4. Training and test sets

- Training: IU.MAKZ development period (results/stage1_v3, roles MK31 / KURK / WUS) and the batch-A networks with outputs
  (AU, AV, C1, IV, KR, OH). JP is excluded from training because its catalogue associations are mostly chance
  (shifted-catalogue control). AB, AF, AW have no outputs.
- Test T1 (primary): batch-B networks scored on reviewed-bulletin labels (analysis/v2_reviewed_bulletin.py labels,
  plan dffacba), networks included in that analysis.
- Test T2 (secondary): batch-B networks on catalogue labels, networks included in results/v2/v2_eval_batchB.json.
- Test T3 (secondary, Kazakhstan): KZ network (KNDC, results/kz, 2024-01-08 .. 2025-09-30) on catalogue labels; noise
  proxies from its own tuning week (results/kz/outKZ_tune), distances from results/metadata/station_comparison.json.
No test network or period contributes to the fit.

## 5. Hypotheses (same margin, bootstrap and seed as the earlier plans)

Statistics: two-stage cluster bootstrap of analysis/v2_networks.cluster_boot (networks, then days; 2000 resamples,
seed 7); margin 3 pp; ratio criterion: upper 95 % bound of the dismissed-count ratio <= 1.5.

- H1 (primary, T1): CG-ctx is non-inferior to P3 (7.5 dB) on dismissed reviewed-associated episodes: upper 95 % bound of the
  pooled difference <= 3 pp AND ratio criterion holds. Also reported on T2 and T3.
- H2 (T1): CG-ctx versus CG_c05: non-inferior when the upper 95 % bound of (CG-ctx - CG_c05) <= 3 pp; "no more dismissals"
  when the point difference <= 0. Also reported on T2 and T3.
- H3 (calibration, T1 and T2 pairs: associated episode, valid site): Brier score of c_j(x) against constant 0.5, the CG-D
  table and c = 1; reliability curve in 10 equal-width bins; holds when the upper 95 % bound of
  Brier(ctx) - Brier(0.5) < 0 and Brier(ctx) - Brier(CG-D) < 0 (cluster bootstrap of pairs by network, then day).
- H4 (descriptive): share of alerts, dismissals and escalations, escalations per day and unassociated alerts for CG, CG_c05,
  CG-D, CG-ctx and P3 on every test set.

## 6. Reporting

Every hypothesis is reported whatever the outcome, with the fitted coefficients, the training size and all three test
sets. A null or negative result is a finding: it marks where a richer reliability model stops paying. Any deviation is
recorded with date and reason in results/context_c/DEVIATIONS.md.

Outputs: results/context_c/context_c.json, results/context_c/calibration_*.png. Code: analysis/context_c.py.
