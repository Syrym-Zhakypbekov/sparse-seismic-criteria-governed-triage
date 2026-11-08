# PLAN learned_rejectband (post hoc; v33 review panels; written and pushed before any computation)

Question: do learned classifiers given a reject band (two thresholds) beat the criteria-governed rule at a matched analyst budget?

- Models: LR, GB, MLP with the hyperparameters of analysis/baselines_ml_llm.py make_models() (unchanged).
- Features per episode (only information available at decision time): for site ranks 1-3, YES and NO indicators (MISSING = both 0);
  reference SNR clipped to 0-40 dB and divided by 40 (0 when undefined); SNR-defined flag. The coverage fractions of the original
  learned baselines are not carried in the multi-network ledgers in the same form, so they are omitted (deviation from 4.14, stated).
- Target: catalogue association of the episode (as in 4.14).
- Training set = the training set of the context-dependent reliability (Section 4.15): IU.MAKZ development period + batch-A
  networks AU AV C1 IV KR OH, catalogue labels. Test set = T1: the 26 batch-B networks with reviewed labels (included in pooled).
- Thresholds: on leave-one-training-network-out predictions, tD is set so that the share of training associated episodes
  dismissed equals that of CG c = 0.5 on the training set, and tA so that the training escalation share equals that of CG c = 0.5.
  Both are frozen before the test set is scored. Final models are refitted on the whole training set.
- Outcomes on T1: dismissed reviewed-associated alarms, unassociated alerts, escalations (counts and per network-day) for LR, GB,
  MLP, CG c = 0.5, CG-D, CG-ctx and P3; pooled two-stage cluster bootstrap (2000, seed 7) of each model minus P3 and minus CG c = 0.5,
  margin 3 points and ratio 1.5 reported as for the other rules.
- Reported whatever the result. Output: results/review2/learned_rejectband.json.
