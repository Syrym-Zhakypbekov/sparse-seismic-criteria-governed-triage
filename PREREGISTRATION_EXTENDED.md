# Pre-registration: extended out-of-sample test (2025-01-01 to 2026-06-30)

Committed before any waveform of this period was processed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

## Data
- Stations, channels, filters, STA/LTA parameters, episode merging, masks, SNR and neighbour windows: identical to the development run (`pipeline/`, results/stage1_v3/summary.json).
- **Detector thresholds frozen** at the development values (no tuning on the new period):
  MAKZ 7.010977, MK31 7.384668, KURK 6.796058, WUS 3.490711.
- Catalogue: ISC + USGS, the same association rule. ISC solutions for 2025–2026 are unreviewed.
- Period: 2025-01-01 to 2026-06-30, processed in two-month chunks on a Google Cloud VM.

## Frozen decision parameters
| Policy | Parameter |
|---|---|
| P1 classic coincidence | none |
| P1t tuned coincidence | τ = 8.0 dB |
| P2 crisp availability-aware | τ = 10.5 dB |
| P3 abstaining, availability-blind | τ = 7.5 dB |
| CG criteria-governed model | w = (MK31 0.25, KURK 0.20, WUS 0.15, SNR 0.40), δ = 0.45, θ_A = 0.60, θ_D = 0.16, SNR full score 30 dB |

## Hypotheses (decided before the data)
- **E1.** On outage days (MK31 valid on less than 10% of the day), CG dismisses fewer catalogue-associated alarms than P1.
- **E2.** Over the whole period, CG forwards fewer automatic alerts without a catalogue event than P3 and than P1t.
- **E3 (non-inferiority).** The share of catalogue-associated alarms dismissed by CG exceeds that of P3 by no more than 3 percentage points (upper bound of the 95% paired day-bootstrap interval).
- **E4.** Every episode with all neighbours MISSING is escalated by CG (Statement 4).

Reported regardless of outcome. If the period contains no MK31 outage, E1 is reported as not testable.
