# Pre-registration: second reference station II.KURK, 2025-01-01 to 2026-06-30

Committed before any waveform of this run was processed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

- Reference II.KURK; neighbours IU.MAKZ, IM.MK31, G.WUS. Pipeline pipeline/extended_stalta_criteria.py with P10_REF=KURK.
- Detector thresholds frozen at the values tuned on 2026-07-01..07 (results/extended/ref_KURK/outB_ref_KURK/summary.json; KURK 6.796058, MAKZ 7.010977, MK31 7.384668, WUS 3.490711).
- Decision parameters frozen as in analysis/ref_kurk.py: weights by distance rank 0.25/0.20/0.15 + SNR 0.40, δ 0.45, θ_A 0.60, θ_D 0.16, SNR full score 30 dB; τ: P1t 8.0, P2 10.5, P3 7.5 dB.
- Catalogue requests retried with back-off; any chunk with a catalogue failure is reprocessed before scoring.

Hypotheses (same as PREREGISTRATION_EXTENDED.md, stated for II.KURK):
- K1. On days with IM.MK31 unavailable, CG dismisses fewer catalogue-associated alarms than P1.
- K2. CG forwards fewer unassociated alerts than P3 and than P1t.
- K3. Non-inferiority: upper bound of the 95% paired day-bootstrap interval of (dismissed-associated share CG − P3) ≤ 3 percentage points.
- K4. Every episode with all neighbours MISSING is escalated by CG.

Reported regardless of outcome.
