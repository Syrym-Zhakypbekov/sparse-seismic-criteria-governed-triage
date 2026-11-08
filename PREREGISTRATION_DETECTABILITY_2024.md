# Pre-registration: detectability-weighted quality factor (CG-D), test on 2024, two reference stations

Committed before any 2024 waveform was processed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Motivation (stated before the test).** In the pre-registered II.KURK test (PREREGISTRATION_KURK_EXTENDED.md) K3 failed:
CG dismissed 10.2 pp more associated alarms than P3. In CG a valid NO enters with q = 1 regardless of whether the
neighbour could have detected the event. CG-D replaces q for a NO by the neighbour's detection probability.

**Model CG-D.** Same as CG (weights by distance rank 0.25/0.20/0.15 + SNR 0.40, δ 0.45, θ_A 0.60, θ_D 0.16, SNR full 30 dB),
except for neighbour i: YES → s = 1, q = 1; NO → s = 0, q = p_i(b); MISSING → q = 0. p_i(b) is the Laplace-smoothed share
of YES among valid records of neighbour i for catalogue-associated development episodes in reference-SNR bin b
(<5, 5–10, 10–15, 15–20, ≥20 dB). Tables frozen in results/prereg/detectability_tables_dev.json
(MAKZ: development 85 days; KURK: exploratory 85-day run). Nothing is re-estimated on 2024.

**Data.** 2024-01-01 .. 2025-01-01, four quarterly chunks per reference, pipeline/extended_stalta_criteria.py with
P10_FIXED_THR = {"MAKZ": 7.010977, "MK31": 7.384668, "KURK": 6.796058, "WUS": 3.490711} for both references; Google Cloud VM.
Chunks with catalogue failures are reprocessed before scoring.

**Hypotheses (each reference separately; P1, P1t 8.0, P2 10.5, P3 7.5 dB, CG frozen):**
- D1. Non-inferiority: upper bound of the 95 % paired day-bootstrap interval of (dismissed-associated share CG-D − P3) ≤ 3 pp.
- D2. CG-D forwards fewer unassociated alerts than P3.
- D3. On days with IM.MK31 valid < 10 %, CG-D dismisses fewer associated alarms than P1 (if such days exist).
- D4. CG-D dismisses fewer associated alarms than CG.
Reported regardless of outcome.
