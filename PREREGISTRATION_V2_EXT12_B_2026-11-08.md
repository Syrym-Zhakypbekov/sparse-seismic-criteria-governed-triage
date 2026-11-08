# Pre-registration: extension ext12B of the batch-B networks of the rule-v2 test (12 months in total)

Author: Syrym Zhakypbekov. Written 08.11.2026 about 12:00 Almaty (07:00 UTC).
Addendum to PREREGISTRATION_V2_NETWORKS_2026-11-08.md (batch A, 4464e34), PREREGISTRATION_V2_BATCHB_2026-11-08.md (batch B) and
PREREGISTRATION_V2_EXT12_2026-11-08.md (ext12 of batch A, b23608a), which it mirrors. Everything not stated here is as in those plans.

## 1. Timing and what was known at the commit
- Written AFTER the batch-B results were scored and reported (results/v2/v2_eval_batchB.json, v2_eval_AB.json, the reviewed-bulletin
  test results/v2_reviewed/v2_eval_reviewed.json). No waveform, episode, catalogue or label of the ext12B period
  2024-07-08 .. 2025-01-08 has been requested or seen for any batch-B network. The extension is a test of the same frozen rules on
  six new months of the same networks.
- The network list uses the batch-B inclusion flags (>= 30 associated episodes in the batch-B period, reported earlier); this is
  stated as a known, outcome-adjacent input. No network is added or dropped after this commit.

## 2. Networks
The 31 batch-B networks included in the batch-B pooled analysis, in batch-B rule order:
NM NS HC RV QZ CN ND C0 NY SI BW PL IW OK EE UU HE TX FN UW HL PE N4 ET AE WW MB AG CO NE UO.
Run ids <NET>_EXT12B. The list is written by analysis/v2_ext12B_networks.py to results/v2/networks_ext12B.json (stations, roles
and sites copied unchanged from networks_batchB.json).

## 3. Period, thresholds, rule, code
- Evaluation period 2024-07-08 .. 2025-01-08 (exclusive; 184 days), the six months following the batch-B period. Batch B + ext12B =
  2024-01-08 .. 2025-01-08 (366 days).
- No re-tuning: frozen per-role thresholds of each network's batch-B run (results/v2/runs/<NET>/status.json "thresholds"; for CN the
  scored Kaggle copy), passed as P10_FIXED_THR. The runner change is identifier/directory only (analysis/v2_fleet/run_network.py:
  ids ending _EXT12B use the ext path with output tree results/v2/runs_ext12B/<NET>/).
- Rule v2, every frozen parameter, the frozen pipeline and wrapper, quarterly chunks (2024-07-08 .. 2024-10-08, 2024-10-08 ..
  2025-01-08), catalogue re-run rule: unchanged. A trace whose sampling rate differs from the nominal is handled as the frozen
  pipeline does (no new handling in this addendum).
- Exclusion (ext alone): unrecovered catalogue failure, fewer than 30 associated episodes in the ext period, or no reference data.
  Reported, not replaced.
- Scorer: analysis/v2_networks.py run-list modes EXTB (runs_ext12B -> v2_eval_ext12B.json) and BEXTB (runs + runs_ext12B by date
  -> v2_eval_B_ext12B.json; combined set = networks included in both v2_eval_batchB.json and v2_eval_ext12B.json). Run-list only,
  committed with this plan before any ext12B output exists; the merge unit tests pass.

## 4. Hypotheses (identical to batch B / ext12)
Primary of this addendum (ext period alone, pooled): V1 (CG − P3 7.5 dB, margin 3 pp, upper 95% bound) and co-primary V1r
(ratio upper bound <= 1.5); two-stage cluster bootstrap, 2000 resamples, seed 7. Secondary V2-V8 unchanged (V2 CG-D, V3 c = 0.5,
V4 P3 8.0 dB, V5 v2 vs v1, V6 unassociated alerts, V7 outage days, V8 all-missing escalated). Per network: day bootstrap, Holm at
one-sided 0.025. Combined batch-B + ext12B (secondary): same hypotheses over networks included in both. Neither replaces the batch-B
primary.

## 5. Chance-association control
As section 6 of the batch-A plan, unchanged, over the ext calendar span and over the combined 366-day span.

## 6. Reviewed-bulletin scoring (secondary, as PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md)
Labels: ISC Reviewed Bulletin (evaluationStatus reviewed) and USGS ComCat (status reviewed), same matching rule (source,
|dt| <= 2 s, <= 0.5 deg), same R1/R1r/R2/R3/R7 hypotheses. Completeness rule fixed now: the ISC Reviewed Bulletin is stated by ISC to
be complete to 2024-11-01; episodes from 2024-11-01 onward are UNUSABLE for reviewed scoring in every network (so the reviewed ext
analysis covers 2024-07-08 .. 2024-11-01); a sensitivity analysis over the full ext period is reported for the networks labelled
from ComCat only, and labelled as such. Code: a wrapper around analysis/v2_reviewed_bulletin.py functions with the ext run tree and
months; no decision rule changes.

## 7. Compute and stopping
GCP VMs of project the authors' Google Cloud project (europe-west zones first; US VMs were throttled by EarthScope on 07-08.11), Colab, and Kaggle
kernels not used by the parallel rescue run. Platform per network is logged in FLEET_DEVIATIONS.md / EXPERIMENT_LEDGER.md and does
not change code or parameters. A network not finished by 08.11.2026 23:00 Almaty is reported "not completed (compute)", never
replaced. Analysis is run once per mode after every network has finished or been declared not completed; scorer bugs found later are
fixed in a separate logged commit with before/after output kept.

## 8. Reported whatever the outcome
Every hypothesis of sections 4 and 6, including failures, networks not completed and non-exercised hypotheses.
