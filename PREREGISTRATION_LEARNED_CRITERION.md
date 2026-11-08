# Pre-registration: a learned criterion inside the governed model (CG-L), extended test episodes

Committed before the EQTransformer output for the extended episodes (Colab run, 18,637 episodes) was read. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Question.** Can a trained neural network enter the criteria-governed model as one criterion, with its own quality
factor, while the aggregation, the evidence threshold and the decision record stay unchanged?

**Model CG-L.** Criteria: c1–c3 neighbour confirmation with the detectability-weighted quality factor of CG-D (MAKZ table,
results/prereg/detectability_tables_dev.json); c4 SNR (s = min(1, SNR/30 dB)); c5 EQTransformer ("original" weights v3):
s = maximum detection probability in the episode window, q = 1 if the model ran without error, else 0.
Weights 0.20/0.15/0.10/0.25/0.30; δ 0.45; θ_A 0.60; θ_D 0.11, chosen on the development episodes (in-sample, 95 % rule)
before this commit (results/prereg/cgl_params.json: development 5 dismissed associated, 190 unassociated alerts, 6.42 escalations/day).

**Data.** The 18,637 episodes of the extended test (2025-01 .. 2026-06, IU.MAKZ). These episodes were analysed before
for the other policies; the EQTransformer scores for them are new. The test is therefore a pre-registered secondary test,
not a test on unseen waveforms.

**Hypotheses.** L1 non-inferiority CG-L vs P3 (upper 95 % paired day-bootstrap bound ≤ 3 pp). L2 CG-L forwards fewer
unassociated alerts than P3. L3 CG-L escalates fewer alarms per day than CG-D. L4 episodes where EQTransformer failed
(q5 = 0) receive a decision from the remaining criteria or are escalated; none is dropped. Reported regardless of outcome.
