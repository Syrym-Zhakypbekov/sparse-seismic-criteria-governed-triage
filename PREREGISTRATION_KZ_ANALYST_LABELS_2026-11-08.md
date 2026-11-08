# Pre-registration: Kazakhstan tests scored against analyst-reviewed bulletin events

Committed and pushed before any label of this test was downloaded. Author: Syrym Zhakypbekov. Date: 2026-11-08.

**Why.** The Kazakhstan tests (IU.MAKZ and II.KURK as references; KZ network) were scored only by catalogue association.
The Alaska test (PREREGISTRATION_GROUND_TRUTH_2026-11-08.md) and the 38-network test
(PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md, OSF https://osf.io/y8qxz) were also scored against analyst-reviewed
events. This plan applies the same reviewed-event rule to the Kazakhstan runs wherever a reviewed bulletin exists.

## 1. Feasibility (metadata and documentation only; decided before any label of the study periods was read)

| Source | Coverage and status | Decision |
|---|---|---|
| Reviewed ISC Bulletin (http://www.isc.ac.uk/iscbulletin/; FDSN event service http://www.isc.ac.uk/fdsnws/event/1/query) | The ISC states the Reviewed Bulletin "contains the most recent events (after 2024-11-01), which have yet to be reviewed" (page read 2026-11-08), i.e. reviewed up to 2024-11-01. ISC-relocated origins carry evaluationStatus "reviewed". Probe outside the study periods (2023-12-01..2023-12-08, 15° around IU.MAKZ, M ≥ 2): 263 events, 15 with an ISC-reviewed preferred origin; preferred-origin agencies MOS 146, NNC 81, ISC 15, KRNET 11, IDC 6. | **Primary label source.** |
| NNC RK / KNDC national bulletin, as contributed to the ISC (agency code NNC) | Present in the ISC database for the region (81 of 263 preferred origins in the probe week). | **Secondary label** (events with an NNC origin in the ISC record). |
| KNDC web bulletins (https://kndc.kz/index.php/en/seismic-bulletins; interactive bulletin https://kndc.kz/index.php/sejsmicheskie-byulleteni/interactive-bulletin) | Web pages; no documented bulk download or licence statement found. The same agency's solutions reach the ISC as NNC. | Not used directly (covered through the ISC as NNC). |
| EMSC | Not an analyst review of the Kazakhstan region beyond contributed solutions; not needed given the ISC. | Not used. |

Consequence: only periods before 2024-11-01 can be scored. The extended test (January 2025 – June 2026) and the KZ
network after 2024-10-31 are outside the reviewed range and are not part of this test.

## 2. Runs and periods (existing frozen outputs; no new waveform processing)

- **K-MAKZ:** results/y2024/out24_MAKZ_* (reference IU.MAKZ), episodes with t_on in [2024-01-01, 2024-11-01).
- **K-KURK:** results/y2024/out24_KURK_* (reference II.KURK), same window.
- **K-KZ:** results/kz/outKZ_2024-* (KZ network, reference KZ.MAKZ), episodes with t_on in [2024-01-08, 2024-11-01).

Calendar days and outage days are restricted to the same windows.

## 3. Labels

- Downloads: ISC FDSN event service (QuakeML), one query per calendar month from 2023-12-31 to 2024-11-01, centre
  (48.8, 80.3), maxradius 20°, minmagnitude 2 (covers the pipelines' 15° query circles of both references), plus USGS
  ComCat global M ≥ 5.5 (GeoJSON, status) for teleseismic rows, the same months. URLs, row counts and sha256 are recorded in
  results/kz_analyst/labels/SHA256.txt.
- Matching: each pipeline catalogue row is matched to the bulletin by source (ISC rows to ISC events, USGS rows to ComCat),
  |dt| ≤ 2 s and ≤ 0.5° (the same function as analysis/v2_reviewed_bulletin.py).
- **L1 (primary):** REVIEWED = matched ISC event whose preferred origin has evaluationStatus "reviewed"; ComCat tele rows
  with status "reviewed".
- **L2 (secondary):** NATIONAL = matched ISC event whose record contains an origin by agency NNC.
- An episode is reviewed-associated (L1) or national-associated (L2) when a labelled row's predicted P lies in
  [t_on − 15 s, t_off] (the pipeline's association rule, applied to the labelled rows only).
- Self-check: re-association of ALL catalogue rows must reproduce the stored association for ≥ 99.5 % of episodes of each
  run; otherwise scoring stops.

## 4. Policies (frozen; no re-tuning)

P1, P1t 8.0 dB, P3 7.5 dB, P2 10.5 dB, CG (c = 1), CG-D (MAKZ development detection table, as in the original tests),
and CG with c = 0.5, all exactly as in analysis/cgd_2024.py and analysis/kz_network.py (thresholds, weights, δ = 0.45,
θ_A = 0.60, θ_D = 0.16). CG with c = 0.5 uses the CG code path with the factor of a recorded non-confirmation set to 0.5.

## 5. Hypotheses (per run; margin 3 percentage points; paired day bootstrap 2000, seed 7, as in the original tests)

- **KR1 (primary):** CG − P3 dismissed share of L1-associated episodes, upper 95 % bound ≤ 3 pp.
- **KR2:** CG-D − P3, same criterion.
- **KR3:** CG with c = 0.5 − P3, same criterion.
- **KR4:** on outage days of the nearest neighbour (MK31 valid share < 0.10), CG dismisses fewer L1-associated episodes
  than P1 (exercised with ≥ 10 L1-associated episodes on such days).
- Exercise rule: KR1–KR3 are not exercised for a run with fewer than 20 L1-associated episodes.
- The same hypotheses on L2 are secondary.
- Reported without hypothesis: chance control (L1 rows shifted by uniform 1–7 days with random sign, 100 shifts, seed 7,
  wrapped in the run's calendar span), unassociated alerts, escalations per day.
- The three runs share sites and periods and are not independent; they are reported separately, not pooled.

## 6. Code and outputs

analysis/kz_reviewed_labels.py (download | score) → results/kz_analyst/labels/, results/kz_analyst/kz_reviewed_eval.json,
results/kz_analyst/kz_reviewed_table.md. Results are reported whatever the outcome; deviations are logged in
results/kz_analyst/DEVIATIONS.md with date and reason.
