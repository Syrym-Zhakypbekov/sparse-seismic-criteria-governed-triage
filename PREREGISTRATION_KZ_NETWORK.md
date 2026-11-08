# Pre-registration: replication on the KZ network (KNDC operator), 2024-01-01 .. 2025-09-30

Committed before any waveform of this run was processed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Why.** All previous tests used IU/IM/II/G channels. The KZ network is operated by the Kazakhstan National Data Centre
(different operator, instruments and data path) and has the same geometry around Makanchi. EarthScope holds KZ data
to about 2025-09.

**Stations (roles keep the names used in the code).** reference MAKZ = KZ.MAKZ (--, BHZ, 40 Hz, same site as IU.MAKZ);
MK31 = KZ.MKAR (24 km); KURK = KZ.KURK (500 km); WUS = KZ.PDGK (434 km). pipeline/extended_stalta_criteria.py with
P10_STATIONS; regime by KZ.MKAR availability (valid < 10 % = outage).

**Detector.** Same STA/LTA settings; thresholds = 99.9th percentile per station on the tuning week 2024-01-01..07
(the instruments differ, so the IU thresholds are not reused); evaluation 2024-01-08 .. 2025-09-30. Catalogue and
association rules unchanged; chunks with catalogue failures are reprocessed before scoring.

**Policies frozen:** P1, P1t 8.0, P2 10.5, P3 7.5 dB; CG (weights by distance rank 0.25/0.20/0.15 + SNR 0.40, δ 0.45,
θ_A 0.60, θ_D 0.16); CG-D with the MAKZ detectability table of results/prereg/detectability_tables_dev.json
(roles mapped as above).

**Hypotheses.** N1 outage days: CG dismisses fewer associated alarms than P1. N2 CG forwards fewer unassociated alerts
than P3 and P1t. N3 non-inferiority CG vs P3 (upper 95 % day-bootstrap bound ≤ 3 pp). N4 all-missing episodes escalated.
N5 the same N3 for CG-D. Reported regardless of outcome.
