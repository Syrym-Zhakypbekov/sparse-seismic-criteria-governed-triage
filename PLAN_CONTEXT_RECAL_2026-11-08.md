# Plan (post hoc, method fixed before computing): recalibration of the context-dependent reliability c_j(x)

Written 2026-11-08 before any result below was computed. Answers the v33 cold panel (Fable MAJOR 3, Codex Astra minors 1-2):
the T1 reliability bins show the context model under-predicting confirmation, so "lower Brier score" may be resolution, not calibration.
Nothing in analysis/context_c.py, the frozen model or the features changes; no test data enter any fit.

## Recalibration (training set only)
- Training set and model exactly as analysis/context_c.py (IU development + the six batch-A training networks, logistic regression on FEATS).
- Out-of-fold predictions on the training set: leave-one-training-set-out (7 folds), same model class and standardisation refit in each fold.
- Two calibrators fitted on the out-of-fold predictions only:
  - Platt: logistic regression of y on logit(p) (C = 1e6, i.e. unpenalised);
  - isotonic regression (increasing, clipped to [0, 1]).
- Each calibrator is applied to the frozen model's predictions on the test sets, then clipped to [0.05, 1.0] as in the frozen rule.

## Metrics on T1 (26 batch-B networks, reviewed-associated episodes with a valid site), for: frozen c_j(x), Platt, isotonic, CG-D table, c = 0.5
- Brier score; calibration intercept and slope (logistic regression of y on logit(p)); ECE over 10 equal-width bins (weighted |mean pred - observed|);
  Murphy decomposition of the Brier score (reliability, resolution, uncertainty) over the same 10 bins.
- Intervals for Brier differences: two-stage cluster bootstrap (networks, then days; 2000; seed 7), as in context_c.brier_boot.

## Decisions on T1 with the recalibrated variants
- H1 (each recalibrated CG-ctx vs P3) and H2 (vs CG c = 0.5) with v2.cluster_boot (margin 3 points, ratio 1.5), plus dismissed associated,
  escalations and unassociated alerts.

## Reading rule fixed now
- "Calibrated" is used in the manuscript only for a variant whose T1 calibration slope 95% interval contains 1 and intercept interval contains 0
  (bootstrap as above). Otherwise the frozen model is described as having a lower Brier score through resolution.
- Reported whatever the result.

Outputs: results/context_c/recal.json; script analysis/context_c_recal.py.
