# DRAFT — Prospective test of criteria-governed seismic alarm triage (to be registered on OSF before any listed data exists)

Status: DRAFT, not registered. Becomes binding only when frozen on OSF (timestamped by OSF, not by this repository);
the OSF registration date must precede the first day of the evaluation period below.

## 1. Why
All earlier tests of this study were pre-specified as timestamped git commits by the author and run on archival data.
Reviewers rightly note that this proves file ordering, not independent registration. This test is registered with a
third party and evaluated only on waveforms recorded after the registration date.

## 2. Decision rules (exact, frozen at commit <SHA filled at registration>)
- CG: rule v2 (sites merged within 50 km; site weights 0.25 / 0.20 / 0.15 by rank; SNR 0.40; theta_A 0.60, delta 0.45,
  theta_D 0.16), c = 1.
- CG_c05: the same rule with c = 0.5.
- CG-D: the IU.MAKZ development table mapped by site rank.
- Comparators: P1 (classic coincidence), P3 at 7.5 dB (abstaining rule).
- Every threshold is tuned with ONE procedure for all rules (5-fold median on the tuning week). This removes the
  inconsistency reviewers found in P1t/P2.

## 3. Networks and periods
- Networks: the 31 batch-B networks of PREREGISTRATION_V2_BATCHB plus the 7 included batch-A networks, same roles and
  sites (results/v2/networks*.json). JP is kept but reported separately (see §5).
- Tuning: first 7 days after registration. Evaluation: the following 90 days.
- Pipeline: pipeline/extended_stalta_criteria.py at the frozen commit. A trace with mixed sampling rates is resampled to
  the nominal rate before merging. This rule is set now; it fixes the CZ failure of 08.11.

## 4. Outcome
- Primary label: association with the reviewed catalogue (ISC reviewed, or the national reviewed bulletin where it
  exists), available 6–24 months after the evaluation period. Unreviewed solutions are not used.
- Secondary label: blinded labels by two analysts on a stratified sample of 400 episodes (100 per stratum:
  associated / unassociated × CG dismiss / P3 forward), with Cohen's kappa reported.

## 5. Hypotheses (one-sided, alpha 0.025, Holm across H1–H3)
- H1: CG_c05 is non-inferior to P3 in dismissed associated alarms, with margin M = 3 pp, pooled 2-stage cluster bootstrap.
- H2: CG-D is non-inferior to P3 under the same rule.
- H3: on outage days of the nearest site, CG dismisses fewer associated alarms than P1. Exercised only with at least
  10 episodes from at least 2 networks.
- H4 (full weight, reported, expected to fail): CG is non-inferior to P3.
- Pre-specified exclusion: a network whose chance-association share is above 0.5 (shifted-catalogue control, seed 7,
  100 shifts, computed on the tuning week only) is excluded from the pooled analysis and reported separately.
- Margin justification and cost: the margin is converted to analyst minutes per day, using the escalation count and a
  stated 2 min per reviewed alarm. A cost-matched comparison at equal escalation budget is reported.

## 6. Refutation
The discount condition is refuted if H1 and H2 both fail after Holm. The outage claim is refuted if H3 is exercised and fails.

## 7. Reported whatever the outcome
All networks, including excluded and failed ones; per-network table; every deviation with date and reason.
