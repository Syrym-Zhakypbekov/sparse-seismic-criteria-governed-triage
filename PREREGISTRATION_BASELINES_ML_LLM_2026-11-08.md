# Pre-registration: learned baselines, an LLM triage baseline and a latency benchmark against the criteria-governed model

Committed and pushed before any learned model was trained and before any episode was sent to a language model.
Author: Syrym Zhakypbekov. Date: 2026-11-08. Scorer: analysis/baselines_ml_llm.py (pushed with this plan).
Outputs: results/baselines_ml_llm/.

**Why.** Two questions asked about every criteria-governed (CG) result: "why not a trained classifier or a large language
model instead of hand-set criteria?" and "the processing time was not benchmarked". This plan answers both with baselines
that see exactly the facts CG sees, are trained only on the development period, and are tested frozen on every test set
already used. CG may lose; the outcome is reported either way.

**State before this commit.** No learned model of this plan had been trained; no test-set prediction of any learned model
and no LLM answer on any episode existed. Before the commit one connectivity probe ("Reply with OK", no episode data) was
sent to gemini-3.8-flash and gemini-3.5-flash-lite on Vertex AI. The CG development numbers used below (392 escalations of
1077 episodes, 5-fold contiguous-block cross-validation) were read from the existing results/criteria_governed/dm_summary.json.
Published CG/P3 counts of the test sets are known (they are in the manuscript); they serve only as the scorer's self-check.

## 1. Features (identical for every learned model; nothing CG does not see)

Per episode, neighbours ordered by distance from the reference (rank 1 = nearest, as CG weights them):
for rank r = 1, 2, 3: state one-hot YES / NO (MISSING = both 0), window coverage `cov_r` (0..1);
reference SNR in dB clipped to [0, 60] (0 if undefined) and an indicator "SNR undefined". 11 features.
Not used: time, date, station names, peak STA/LTA, waveforms, catalogue fields.
Label for training: catalogue association of the development episode (`assoc_event >= 0`).

## 2. Learned models (hyperparameters fixed now, no tuning)

- **LR** logistic regression, standardised features, C = 1, max_iter 2000.
- **GB** gradient boosting (sklearn GradientBoostingClassifier), 200 trees, depth 3, learning rate 0.05, random_state 7.
- **MLP** standardised features, hidden layers (32, 16), ReLU, alpha 1e-3, max_iter 3000, random_state 7.

Training data: development episodes only (results/stage1_v3/episodes.csv, 2026-07-08..09-30, IU.MAKZ, 1077 episodes,
141 associated).

**Thresholds, chosen the same way as CG.** Five contiguous day blocks of the development period (as for CG's θ_D);
out-of-fold probabilities p from models trained on the other four blocks. DISMISS if p ≤ θ_D, ALERT if p ≥ θ_A, otherwise
ESCALATE. θ_D = largest value on the grid 0.000, 0.001, ..., 1.000 keeping ≥ 95 % of associated development episodes
out of DISMISS (CG's rule). CG's θ_A = 0.60 was set a priori on the D(x) scale, which has no counterpart on a probability
scale, so the escalation band is matched by cost: θ_A = smallest grid value > θ_D for which the out-of-fold development
escalation share is ≤ CG's development escalation share (392/1077 = 36.4 %). The final model is refitted on all
development episodes and applied with these frozen thresholds; no test-set information enters.

## 3. Test sets (all frozen, all already processed; the learned models and the LLM are new)

| Set | Episodes source | Days |
|---|---|---|
| EXT-MAKZ | chunks of results/extended/extended_eval.json (IU.MAKZ, 2025-01..2026-06) | 546 |
| EXT-KURK | results/kurk_ext/outK_* (II.KURK reference) | 546 |
| KZ | results/kz/outKZ_20* (KZ.MAKZ reference) | 632 |
| AK | results/ak/outAK_20* (AK.CUT reference) | 540 |
| AK-GT | AK episodes with the analyst labels of results/ground_truth/episodes_labelled.csv.gz (CONFIRMED / REJECTED) | 540 |

Comparators, frozen: **CG** (rank weights 0.25/0.20/0.15 + SNR 0.40, δ 0.45, θ_A 0.60, θ_D 0.16), **P3** (7.5 dB),
**CG-D** where the detectability table applies by neighbour name (EXT-MAKZ, KZ, AK). Self-check before scoring: the
scorer must reproduce the published P3 and CG counts of dismissed associated and unassociated alerts of every set
(and AK-GT's stored CG actions); it stops otherwise.

## 4. Hypotheses, learned baselines (per set S ∈ {EXT-MAKZ, EXT-KURK, KZ, AK}, per model m ∈ {LR, GB, MLP})

Uncertainty: paired day bootstrap over episode dates, 2000 resamples, seed 7 (as every earlier test). Margin 3 pp.
- **M1** m is non-inferior to P3: upper 95 % bound of (m − P3) dismissed share among associated ≤ 3 pp.
- **M2** (primary) CG is non-inferior to m: **M2a** upper 95 % bound of (CG − m) dismissed share among associated ≤ 3 pp;
  **M2r** relative criterion, upper 95 % bound of (CG dismissed + 0.5)/(m dismissed + 0.5) ≤ 1.5. Reported separately.
- **M3** CG forwards fewer unassociated alerts than m: upper 95 % bound of (CG − m) unassociated-alert count < 0.
- **M4** escalations per calendar day of CG and m, with the bootstrap interval of the difference (descriptive).
- **M5** (AK-GT) analyst labels: **M5a** upper 95 % bound of (CG − m) dismissed share among CONFIRMED ≤ 3 pp;
  **M5b** ALERT share among REJECTED lower for CG: upper 95 % bound of (CG − m) < 0.
- **M6** episodes with every neighbour MISSING: CG escalates all (Statement 4); for each m the number of such episodes it
  decides automatically (ALERT or DISMISS) is reported. Not exercised in a set without such episodes.

Twelve set × model cells per hypothesis; each cell is a separate decision, no family-level claim; the number of cells in
which each hypothesis holds is reported, with Holm-adjusted one-sided bootstrap p-values beside the raw bounds
(p = (draws beyond the margin + 1)/(draws + 1)).

**Interpretability (descriptive outcome, fixed now).**
I1 exact decomposition: whether every decision is an exact sum of named per-criterion contributions with weights fixed
before data (CG: Statement 2.2, checked numerically; LR: additive only in the logit with learned coefficients; GB, MLP: no).
I2 monotonicity violations on all test episodes: for every neighbour rank, changing NO → YES, and MISSING → YES (coverage
set to 1), and raising the SNR by 5 dB, each with all else fixed; count of episodes where the model's score decreases.
CG cannot decrease under these changes by construction; the counts are computed for CG as a check.

## 5. LLM triage baseline (Google Gemini only, Vertex AI)

Model **gemini-3.8-flash**, Vertex AI, project the authors' Google Cloud project, location global, temperature 0, thinking level low,
response MIME type JSON (no response schema, so format errors can occur and are counted). Price used for the cost
figure: $0.75 per million input tokens, $3.75 per million output tokens (output includes thinking tokens), as listed for
this model; every usage record is saved.

**Prompt (one call per episode).** The model is told: it triages automatic seismic triggers at a reference station; the
three neighbour stations with distance in km, nearest first; for this trigger: reference SNR in dB (or "undefined"), and for
each neighbour whether it triggered in its expected arrival window (YES), recorded without a trigger (NO) or had no data
(MISSING), with its data coverage. Actions: ALERT (forward automatically as a real seismic event), DISMISS (discard
automatically), ESCALATE (human review). Instruction: dismissing a real earthquake is the costliest error, at most about
5 % of real events may be dismissed; escalate when evidence is missing or conflicting. Answer only JSON
{"action": "ALERT"|"DISMISS"|"ESCALATE", "reason": "<= 30 words", "criteria_used": [...]}. No time, date, station code of
the reference, catalogue information or policy output is given. The exact prompt text is in the scorer and every prompt
and raw response is saved (results/baselines_ml_llm/llm/calls.jsonl).

**Samples (fixed seed 7).** AK-GT: all REJECTED episodes (114) + 486 random CONFIRMED = 600. EXT-MAKZ: 300 random
associated + 300 random unassociated = 600. Repeatability: the first 100 episodes of the shuffled combined list are asked
a second time after the first pass. Total 1300 calls.
**Spend cap $10**: the scorer stops when the running cost reaches $10; unfinished calls are reported as not run.

Hypotheses (within-class shares, bootstrap over episodes, 2000 resamples, seed 7):
- **L1** format: a valid action is parsed from ≥ 99 % of answers (invalid or refused answers counted, treated as ESCALATE
  in L2–L4).
- **L2** CG is non-inferior to the LLM on real events: upper 95 % bound of (CG − LLM) dismissed share among positives ≤ 3 pp,
  separately for AK-GT CONFIRMED and EXT-MAKZ associated.
- **L3** CG alerts less on negatives: upper 95 % bound of (CG − LLM) ALERT share < 0, separately for AK-GT REJECTED and
  EXT-MAKZ unassociated.
- **L4** repeatability: the LLM gives the same action on the repeat for ≥ 95 % of the 100 repeated episodes.
- **L5** agreement with CG: exact-action agreement and Cohen's kappa (descriptive).
Also reported: cost per call and per 10,000 episodes, latency (median, p95), tokens, the confusion table LLM × CG.

## 6. Latency benchmark (laptop CPU, author's Windows 11 laptop, single thread)

Per-episode decision time on the EXT-MAKZ episodes: CG as a scalar Python function (one episode at a time, 1000 random
episodes, 5 repeats, median and p95) and vectorised over the whole set (episodes per second); LR, GB, MLP `predict_proba`
on one row (same 1000 episodes) and on the whole set; LLM wall-clock per call from section 5 (calls run 6 in parallel;
per-call latency is measured per request).
- **T1** CG single-episode median < 1 ms.
- **T2** LLM median latency ≥ 1000 × CG single-episode median.
- **T3** learned models: medians reported (descriptive).

## 7. Interpretation fixed in advance

If CG fails M2 for a model and set, the learned model dismissed fewer associated alarms there; this is reported as a CG
loss, together with the escalation and unassociated-alert costs. Catalogue association is not ground truth (Sections 3–4 of
the manuscript); AK-GT is the only analyst-labelled set. The learned models are trained on 141 associated episodes of one
station and one quarter; a failure of a learned model to transfer is a property of this training budget, not of learned
models in general. The LLM is one model with one prompt; its result is not a statement about language models in general.
