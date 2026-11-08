# Rescue of the multi-network networks excluded for technical reasons (post hoc extension), 08.11.2026

Written and pushed before any new waveform, availability record or bulletin label of these networks is requested.
It is a POST HOC extension: the networks below are known to have been excluded, and the primary results of
PREREGISTRATION_V2_NETWORKS_2026-11-08.md, PREREGISTRATION_V2_BATCHB_2026-11-08.md and
PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md (38 networks; 33 in the reviewed-bulletin pool) are unchanged and remain
the primary results. The rescue set is reported separately, and the 38 + rescued set only as a post hoc sensitivity.

## 1. Networks
- Tuning failed in batch A or B (a role without usable data in the tuning week 2024-01-01..2024-01-08): AB, AF, AW, C, CU, EI,
  FR, KO, O2, PQ, S1, US.
- CZ: not completed; CZ.PRU switches sampling rate (100 / 99.99998 Hz) within a day and obspy refuses to merge the traces.
- SC: not completed (disk-full chunk and data-centre throttling on the night of 7-8 November).
- LD and WU are NOT rescued: they ran to completion and are excluded by the pre-specified rule (< 30 associated episodes).

## 2. What changes (run list only; nothing in the decision rules)
1. Tuning window (AB, AF, AW, C, CU, EI, FR, KO, O2, PQ, S1, US, CZ): the first 7-day window [t, t + 7 d), t = 2024-01-01,
   2024-01-02, ..., 2024-03-25 (so the window ends by 2024-03-31), in which every role has data on at least 5 of the 7 days.
   A role has data on a day when the FDSN availability extents of its stream cover at least 12 h of that day; if the data centre
   has no availability service, when a 5-minute dataselect request at 00:00 or at 12:00 UTC returns samples. If the frozen
   pipeline still gives a non-finite threshold for the chosen window, the next qualifying window is used, at most three windows.
   No qualifying window, or three non-finite attempts: the network stays excluded and is reported with the reason.
2. Evaluation period: [max(2024-01-08, t + 7 d), 2024-07-08), i.e. unchanged when t = 2024-01-01; otherwise it starts the day the
   tuning window ends, so no evaluated day lies in or before the tuning window. Quarterly chunks from that start, as in the runner.
3. CZ only: traces whose sampling rate differs from the nominal rate of the channel (the most common rate) by less than 0.01 % are
   resampled to the nominal rate (linear interpolation) before the pipeline's merge; every such trace is logged
   (pipeline/p10_v2_rescue_wrapper.py, active only with P10_RATE_FIX=1). The frozen pipeline file is unchanged (sha256 checked).
4. SC: rerun unchanged (tuning 2024-01-01..2024-01-08, evaluation 2024-01-08..2024-07-08).
5. Outputs in results/v2/runs_rescue/<NET>/ (never over results/v2/runs/). Runner: analysis/v2_fleet/run_rescue.py.

## 3. Unchanged
Frozen pipeline (sha256 4c8c9a71...), rule v2 (sites merged within 50 km, weights 0.25 / 0.20 / 0.15, SNR 0.40), theta_A 0.60,
delta 0.45, theta_D 0.16, c = 1 / CG-D / c = 0.5, baselines P1, P1t 8.0 dB, P2 10.5 dB, P3 7.5 and 8.0 dB, inclusion >= 30
associated episodes and no catalogue failure, margin 3 points and ratio 1.5, two-stage cluster bootstrap 2000 resamples seed 7,
Holm, chance-shift control, outage hypothesis rule (>= 10 episodes from >= 2 networks). Scorer analysis/v2_networks.py.

## 4. Scoring and reporting (analysis/v2_rescue_score.py)
- Catalogue association (as batch A/B) and analyst-reviewed bulletin labels (as PREREGISTRATION_REVIEWED_BULLETIN_38NET: ISC
  reviewed origins and ComCat status 'reviewed', |dt| <= 2 s, <= 0.5 deg), labels in results/v2_rescue/labels/.
- Sets: RESCUE (rescued networks passing inclusion) and ALL (38 primary + RESCUE). For each: CG, CG-D, c = 0.5 minus P3 with
  intervals and ratio, rule v2 vs v1, per-network Holm, outage comparison CG vs P1.
- Reported whatever the outcome, with every network's state (rescued, no window, non-finite thresholds, not completed),
  platform and wall time; deviations in results/v2/FLEET_DEVIATIONS.md. Labelled post hoc in the manuscript.

## 5. Compute
Kaggle CPU kernels (analysis/v2_fleet/make_kaggle.py <NET> --rescue --suffix rescue) and, if useful, GCP VMs of project
the authors' Google Cloud project (stopped after use). The first run of each network to complete is the scored run; others are replicates.
