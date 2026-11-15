# Deviations and pre-set handling — PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md (pushed f8a1762, 2026-11-09T02:51:22Z)

- 2026-11-09T03:24Z (section 9, pre-set handling, not a deviation): AK quarter 2023-07-01 .. 09-30 stopped twice on 2023-08-31 in the
  frozen pipeline (obspy merge: AK.E22K..BHZ traces with sampling rates 50.0 and 50.000003814697266 in one day). As pre-set, the
  quarter is "not completed (data)", not repaired and not replaced; AK is scored on the three completed quarters (273 calendar days).
- 2026-11-09T03:28Z (reporting only): after the first scoring (03:26:58Z) analysis/tdh2023_p1/score.py was extended to print the
  failed-quarter reason and a generated "Notes" section in RESULTS_tdh2023.md (reviewed share of catalogue rows, number of dismissals,
  T2 exercised or not). No estimate, interval, p value or verdict changed (family identical between the two runs).
- Section 5 machine: no VM was started; download (2,920 role-days, 0 failed), bucket copy and compute ran on the laptop.
