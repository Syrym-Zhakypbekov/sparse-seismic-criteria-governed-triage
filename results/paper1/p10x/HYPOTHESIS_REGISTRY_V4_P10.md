# Hypothesis registry v4-P10 — cold-panel rows on the P10 seismic alarm-triage data

**Status of every row: post hoc after cold review 09.11, exploratory-confirmatory: registered before computation.**
Registered 09.11.2026 (Almaty), before any script of this registry was written or run. Motivation: cold review
`C:/review_p10/cold_overnight_0911/TRIAGE.md` (M1, M2, M3, M5 and the G.WUS bullet) of the frozen manuscript v37
(`frozen/P10_manuscript_v37_2026-11-08.md`).

**Data (read-only, P10 repository `C:/dev/p10-seismic-alarm-triage`, HEAD `a97d376`).** No raw waveform is downloaded, no
detector is re-run, no GCP machine is used. Inputs:
- `results/posthoc/_collect_reviewed.pkl` (local cache of `analysis/posthoc_collect.py collect("reviewed")`, sha256 prefix
  `325cb484706603a6`): per network the frozen site states (3 nearest sites), SNR, SNR validity, reviewed-bulletin association,
  day of each episode and the frozen actions; 33 networks included (pre-specified inclusion of the reviewed test).
- Batch membership: `results/v2/networks.json` (batch A) and `results/v2/networks_batchB.json` (batch B). Of the 33 included
  networks, 7 are batch A (AU, AV, C1, IV, JP, KR, OH) and 26 are batch B. This is the split already used in Section 4.16.
- `results/posthoc/chance_by_policy.json` (shifted-catalogue chance control, prefix `62af702694085ad7`) and
  `results/posthoc/chance_per_episode_33net.json` (per-episode Poisson estimator, prefix `35f84d0d675649dd`).
- Single-network episode ledgers: development `results/stage1_v3/episodes.csv`, extended IU.MAKZ / II.KURK
  (`results/extended/vm_2025*`, `kaggle_2026h1`, `results/kurk_ext/outK_*`), 2024 (`results/y2024/out24_*`), with the frozen
  feature code of `analysis/oos_operating_points.py` (copied, not modified).

**What was already seen (disclosure).** While inspecting the data to define the rows, the following existing outputs were
read and are already published in v37: Table B2 (whole-development procedure: P3 8.0 dB, E3 1.96 [1.28, 2.63], met);
`same_procedure_baselines.json` (fold-median procedure leaves P3 at 7.5 dB, so CG − P3 contrasts are unchanged);
`gap/gap_reviewed.json` G2 (chance-corrected CG − P3 2.171 [1.041, 3.21], c = 0.5 0.32 [−0.126, 0.756], CG-D 0.479 [0.014, 0.899]);
`chance_per_episode_33net.json` pooled CG − P3 (2.245 [0.994, 3.425]); `sufficiency/cost.json` (δ removed no reviewed-associated
dismissal of c = 0.5 and CG-D on the 3062-episode real thin subset; 843 escalations per avoided dismissal under masking);
`gap2/wus_removed.json` (E3 3.71, K3 11.44 with G.WUS missing); Section 4.16 (P3-2t chosen on 7 networks matched c = 0.5 on 26).
Rows P10X-03, P10X-05 and parts of P10X-04/P10X-06 therefore re-compute or extend results whose headline values are known;
they are labelled so below and cannot count as independent confirmation. Rows P10X-01 and P10X-02 (equal-budget held-out
frontier with CG re-tuned) have never been computed.

**Common statistics.** Two-stage paired cluster bootstrap (networks resampled with replacement, then days with episodes
within each drawn network; both policies evaluated on the same draw), 2000 resamples, seed 7, percentile 95% interval —
the scheme of `analysis/v2_networks.cluster_boot`. Single-network rows use the published day bootstrap (`v2_networks.day_boot`,
2000, seed 7). One-sided p for a non-inferiority bound = (number of resamples at or beyond the margin + 1) / (B + 1).
For a joint claim (all components must hold) p = max of the component p values (intersection–union).

**Verdict rule (all testable rows).** HELD: every component's upper 95% bound is within its margin. «not held»: the point
estimate of at least one component lies beyond its margin. «inconclusive»: otherwise (interval contains a margin, point
inside). Descriptive rows end as «inconclusive» (label status:inconclusive) with the estimates. Blocked: data not on disk.

**Holm family F-P10X** (one-sided, α = 0.025): P10X-01, P10X-02, P10X-03a, P10X-03b, P10X-05a, P10X-05b, P10X-05c, P10X-06a
(06a has an exact count, p := 0 if the count is zero, 1 otherwise; it enters Holm only formally). Holm-adjusted p values are
reported; a row is HELD only if it holds by the verdict rule AND its Holm-adjusted p ≤ 0.025 (06a: exact).

---

## P10X-01 — chain A (novelty): CG vs two-threshold P3 at equal tuning budget, held out (batch A → batch B)
- **Policies and grids (360 settings each).** P3-2t: dismiss if no site YES, SNR valid and SNR < t_D; alert if any site YES,
  SNR valid and SNR ≥ t_A; else escalate; t_D ∈ {5.0, 5.5, …, 12.0}, t_A ∈ {t_D, …, 20.0} step 0.5 (360, as Section 4.16).
  CG (rule v2 frozen except the tuned values): c ∈ {0.25, 0.5, 0.75, 1.0}, θ_D ∈ {0.08, 0.10, …, 0.24} (9), θ_A ∈ {0.45, 0.50, …,
  0.90} (10) → 360; weights 0.25/0.20/0.15 + SNR 0.40, SNR full score 30 dB, δ = 0.45 frozen.
- **Selection (same rule for both, development = 7 batch-A networks only).** Minimise unassociated alerts per episode subject to
  dismissed share of reviewed-associated episodes ≤ 3% and escalated share of episodes ≤ 40% (the middle constraint of
  Appendix H); ties → fewer escalations, then fewer dismissed associated. If no setting is feasible, the escalation cap is raised
  by 10 points until one is (logged as a deviation).
- **Held-out evaluation:** the 26 batch-B networks, each selected setting frozen.
- **Metrics (CG − P3-2t, pooled):** (i) dismissed share of reviewed-associated episodes, pp; (ii) unassociated alerts per
  network-day; (iii) escalations per network-day, plus the escalation ratio CG / P3-2t.
- **Claim:** CG is non-inferior on dismissals (upper bound of (i) ≤ 3 pp) AND not worse on escalations (upper bound of the
  escalation ratio ≤ 1.10). (ii) is reported, not tested. **Registered expectation: no material difference** (the paper's own
  conclusion, Section 4.16 and Appendix H).
- Secondary (descriptive): the other five Appendix-H constraints (3%/30%, 3%/50%, 5%/30%, 5%/40%, 5%/50%) and the cost rule
  r_m = 50, r_e = 0.25; a temporal split (first half of each of the 33 networks → second half) with the primary constraint.

## P10X-02 — chain A: CG vs availability-aware two-threshold rule, equal budget, held out
- **Baseline P3-2t-av:** P3-2t, except that an episode with any of the three sites MISSING is never dismissed (it is escalated
  if it is not alerted), i.e. «escalate if any neighbour is MISSING and the alert condition fails». Same 360-setting grid, same
  selection rule, same development and held-out sets. CG: the setting selected in P10X-01 (identical grid and rule).
- **Metrics and claim:** as P10X-01 with P3-2t-av in place of P3-2t. Registered expectation: no material difference.

## P10X-03 — chain C (thresholds/design): one threshold procedure for every policy
- **Procedure registered:** rule (4) applied on the WHOLE development set (IU.MAKZ, `results/stage1_v3/episodes.csv`) for every
  policy: SNR grid 0–30 dB step 0.5 for P1t, P2, P3; θ_D grid 0.00–1.00 step 0.01 for CG (largest value keeping ≥ 95% of
  associated development episodes undismissed). The CG θ_D is recomputed here, not taken from the text.
- **P10X-03a (re-computation; outcome known: Table B2):** E3 = CG − P3 dismissed share on extended IU.MAKZ (2025–26), margin
  3 pp, day bootstrap; frozen-procedure self-check must reproduce 2.44 [1.74, 3.18] (main text) or [1.75, 3.14] (Table B2).
  Claim: non-inferiority holds under the one procedure. Report whether the verdict differs from the frozen E3 («not established»).
- **P10X-03b (new):** the reviewed 33-network primary contrast CG − P3 (pooled, cluster bootstrap, margin 3 pp, ratio ≤ 1.5)
  with P3 at the one-procedure threshold; also c = 0.5 and CG-D (descriptive). Claim: CG non-inferior to P3 (difference and ratio).
  Expectation: not held (frozen verdict 3.89 [2.31, 5.73] at 7.5 dB).

## P10X-04 — chain B (evidence): chance confirmation per neighbour, G.WUS
- **Registered method (time-shifted trigger lists):** shift each neighbour's trigger times by many large offsets, recompute YES.
  **Expected to be blocked:** the ledgers store only the per-episode state, not neighbour trigger times (v37 Appendix H says so).
- **Substitute (registered now, labelled deviation-from-request):** Poisson chance-YES per neighbour and reference
  p = 1 − exp(−λ · 2w), λ = neighbour triggers per valid second (trigger counts in `summary.json` «episodes», valid seconds from
  `availability.csv`), w = d/5.5 + 5 s (the pipeline's YES window). Per quarter of 2024 (4 runs, both IU.MAKZ and II.KURK as
  reference) and development 2026; 95% interval from the exact Poisson interval on the trigger count. Empirical companion: share of
  YES among unassociated reference episodes with the neighbour valid (an upper proxy; real local events are included).
- **Sensitivity:** G.WUS set to MISSING in every episode (CG and P3 frozen) on extended IU.MAKZ and II.KURK and 2024: CG − P3
  differences in dismissed share (pp), unassociated alerts and escalations per day, day bootstrap. Dismissal values are known
  (Appendix H); alerts/escalations with intervals are new. Descriptive.

## P10X-05 — chain B: chance-corrected non-inferiority at margins 1, 2, 3, 5 pp
- **Data:** 33 reviewed networks; estimator A (shifted catalogue, `chance_by_policy.json`) primary, estimator B (per-episode
  Poisson, `chance_per_episode_33net.json`) secondary. Corrected difference = Σ[(D_k − C_k) − (D_P3 − C_P3)] / Σ(assoc − chance_assoc)
  × 100; corrected ratio = Σ(D_k − C_k) / Σ(D_P3 − C_P3); network bootstrap 2000, seed 7 (as G2); undefined ratio resamples counted.
- **Rows:** P10X-05a CG, 05b c = 0.5, 05c CG-D. Holm member = margin 3 pp (difference) for each; margins 1, 2, 5 reported as
  verdicts per margin (descriptive). Ratio criterion (upper ≤ 1.5) after correction reported (known: fails for c = 0.5, CG-D).
  Claim per row: chance-corrected difference upper bound ≤ 3 pp. Known for estimator A (G2): CG fails, c = 0.5 and CG-D meet.

## P10X-06 — chain C: δ as a constraint, measured cost
- **Data:** 33 reviewed networks (frozen thresholds); δ = 0.45 (on) vs δ = 0 (off) for CG, c = 0.5, CG-D.
- **P10X-06a (testable, exact):** δ changes no reviewed-associated dismissal: for each of CG, c = 0.5, CG-D the set of
  reviewed-associated episodes dismissed is identical with δ on and off (count of changed episodes = 0). HELD iff 0 for all three.
  Known for c = 0.5 and CG-D on the thin subset (0); CG not computed before.
- **P10X-06b (descriptive cost):** added escalations, removed automatic alerts and dismissals (total and per network-day), with
  cluster-bootstrap intervals, on the archive; and under random masking of site states to MISSING (p = 0.5 independent per
  site-episode, 50 seeds, seed base 7): per policy avoided reviewed-associated dismissals, added escalations, escalations per
  avoided dismissal (network bootstrap of the seed-averaged per-network values; undefined resamples counted).

Results: `results/registry/P10X-NN.json`; scripts `src/p10x/`; outputs `results/p10x/`. Deviations: `plan/DEVIATIONS.md`
(D-P10X-n). Blockers: `plan/BLOCKERS_P10X.md`.
