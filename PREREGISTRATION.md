# Held-out evaluation, pre-registered 07.11.2026 (before the held-out data were processed)

Everything below is fixed before the held-out run. The run is executed once; its numbers are reported as they come out.

- **Held-out period:** 2026-10-01 00:00 UTC – 2026-11-07 00:00 UTC (37 days).
  Not used in any earlier analysis; no file from this period existed when this note was committed.
- **Detector thresholds:** 99.9th percentile of the STA/LTA characteristic function on the tuning week 2026-07-01..07 (same as development).
- **Policy thresholds, frozen from the development period (results/stage1_v3/policies.json):**
  - P2 availability-aware: τ = 10.5 dB.
  - P1t tuned coincidence: τ = 8.0 dB.
  - P1 classic coincidence: no threshold.
- **Pipeline:** `pipeline/stage1_pipeline.py` with `P10_T1=2026-11-07`, `P10_EVAL_START=2026-10-01`. All other parameters are identical to `results/stage1_v3/summary.json`.
- **Primary outcomes:**
  - unsafe dismissals among catalogue-associated episodes, with a day-bootstrap 95 % CI;
  - unassociated automatic ALERTs;
  - escalations per day.
- **Pre-registered hypotheses:**
  - H2: P2 has no more unsafe dismissals than P1t and fewer unassociated automatic ALERTs.
  - H4: P2's unsafe rate stays within the development 95 % CI (2.2–11.4 %).
- **Known limitation, stated in advance:** the ISC bulletin for recent months is preliminary and less complete than the reviewed bulletin, so catalogue association in the held-out period is conservative.
