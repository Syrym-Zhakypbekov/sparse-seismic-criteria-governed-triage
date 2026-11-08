# Pre-registration: blast / earthquake / escalate with the criteria-governed model (exploratory application)

Committed before any waveform feature of this analysis was computed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Population.** Extended-test episodes at IU.MAKZ associated with an NNC (KNDC) event via results/nnc/episodes_nnc.csv
(1007 NNC "earthquake", 308 NNC "mining explosion"; NNC labels are agency judgements, not ground truth).
Development: events before 2025-07-01. Test: 2025-07-01 .. 2026-02-28. The test labels are not used for any choice.

**Features at IU.MAKZ (BHZ, demean, taper, causal 4th-order Butterworth):**
- f1 spectral ratio log10(RMS 6–12 Hz / RMS 1–4 Hz) in [p, p+6 s] (p = predicted P from the NNC origin, TauP iasp91);
- f2 P/S ratio log10(RMS 2–8 Hz in [p, p+5 s] / RMS 2–8 Hz in [s, s+8 s]) (s = predicted S);
- f3 local hour (UTC+5) in 08–18 — reported separately because the agency label may itself depend on time of day.
- Quality q_i = 1 if the window is complete (no gap) and the SNR of the window over pre-P noise is >= 3 dB, else 0.

**Model.** Partial scores s_i = empirical CDF of the feature among development explosions vs earthquakes
(direction fixed on development); weights 0.5/0.5 for f1,f2 (model W) or 0.35/0.35/0.30 with f3 (model WT);
δ = 0.45; D(x) as in the paper; θ_B, θ_E chosen on development so that each automatic class has precision >= 0.90;
otherwise ESCALATE.

**Hypotheses (test period).**
- B1. Among automatic decisions of model W, accuracy against NNC labels exceeds that of the single best development feature with the same automation share.
- B2. Episodes with q = 0 on both waveform features are escalated, never decided automatically.
- B3 (descriptive). Escalation share and accuracy of W and WT; time of day alone as a baseline.

Reported regardless of outcome; a failed B1 is reported as failed.
