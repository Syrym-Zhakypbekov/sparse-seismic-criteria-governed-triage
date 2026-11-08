# Pre-registration: second-region replication on the AK network (Alaska), 2024-01-08 .. 2025-07-01

Committed and pushed before any waveform of this run was processed. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Why.** Every earlier test (IU/II/IM/G and KZ streams) is in one region around Makanchi, Kazakhstan. This test repeats the
same frozen pipeline and policies in a different region (south-central and northern Alaska, about 8 000 km away) on a
network run by a different operator (AK, Alaska Geophysical Network, Alaska Earthquake Center, University of Alaska
Fairbanks), with a different regional catalogue contributor (AK solutions in USGS ComCat, plus ISC) through the same ISC
and USGS FDSN event services.

**How the stations were chosen (before any waveform was processed; evidence in results/ak/selection/).**
EarthScope FDSN station service, network AK, channel BHZ, epochs covering 2024-01-01 .. 2025-07-01: 187 stations
(AK_st.json, pairs.py). Reference candidates = stations whose nearest neighbour is 20–60 km and none closer than 15 km.
The FDSN availability service is retired at EarthScope (HTTP 404 "This service has been retired"), so availability was
checked with cheap dataselect probes: one minute at 12:00 UTC on every day of the period for ten candidate stations
(probe.py, probe_AK_12.json, probe_daily_1200_summary.txt) and one minute at 06:00 UTC every third day for seven far
candidates (probe3.py, probe_AK_6.json). AK.CUT was the most reliable reference (6 empty probes in 547 days) whose 20–60 km
neighbour has real multi-day outages: AK.L22K (29 km) was empty on 40 probe days, including runs of 7, 5 and 4 days in
April–May 2024, so the outage hypothesis can be exercised. The two far roles were chosen to repeat the development
geometry (MAKZ: 24, ~500, ~670 km) among reliable stations: AK.COLD (536 km, 2 empty of 183 probes) and AK.E22K (641 km,
5 empty of 183). A probe is one minute, not a day; the regime of every day is decided by the pipeline from the processed
data as before. Probes on 2024-05-11 and 2024-05-18 were empty at nearly every station (an archive-wide gap at that
minute); this is noted, not used.

**Stations (roles keep the names used in the code; all AK, location "", BHZ, 50 Hz, Nanometrics Trillium 120 + Quanterra).**

| role | stream | coordinates | distance from reference |
|---|---|---|---|
| MAKZ (reference) | AK.CUT..BHZ (Chulitna) | 62.4058, -150.2625 | – |
| MK31 (nearest neighbour, regime station) | AK.L22K..BHZ (Petersville) | 62.5258, -150.7703 | 29 km |
| KURK | AK.COLD..BHZ (Coldfoot) | 67.2278, -150.2070 | 536 km |
| WUS | AK.E22K..BHZ (Anaktuvuk Pass) | 68.1343, -151.8132 | 641 km |

Weights follow distance rank exactly as in every earlier test (0.25 / 0.20 / 0.15 for nearest / second / third neighbour,
SNR 0.40), computed by the scorer from the distances in the run logs. This is a deliberately sparse subset of a denser
network (many AK stations lie between 29 and 536 km); the test is of the decision rule on this geometry, not of the AK
network's real detection capability.

**Detector.** pipeline/extended_stalta_criteria.py unchanged (run on the VM as p10_stalta_criteria_kz.py, byte-identical),
stations through P10_STATIONS, script p10_runAK.sh. Same STA/LTA, band 1–8 Hz, episode and window rules. Thresholds =
99.9th percentile per station on the tuning week 2024-01-01 .. 2024-01-07 only (the instruments differ, so earlier
thresholds are not reused), then frozen (P10_FIXED_THR). Evaluation 2024-01-08 .. 2025-07-01 (540 days) in six quarterly
chunks run in parallel. Regime by AK.L22K (MK31 role) daily valid share: < 10 % = outage, >= 90 % = normal.
Catalogue and association rules unchanged (ISC + USGS regional within 15 degrees, M >= 2.0; USGS M >= 5.5 teleseismic;
de-duplication 20 s / 0.5 degree; one association window). A chunk whose summary.json lists a catalogue failure is
reprocessed before scoring and logged as a protocol deviation in EXPERIMENT_LEDGER.md.

**Policies frozen (no re-tuning on these data).** P1; P1t (SNR 8.0 dB); P2 10.5 dB; P3 7.5 dB; CG with weights by distance
rank 0.25 / 0.20 / 0.15 + SNR 0.40, delta 0.45, theta_A 0.60, theta_D 0.16, c = 1 for a valid NO; CG-D with the IU.MAKZ
development detectability table of results/prereg/detectability_tables_dev.json (table "MAKZ", roles MK31 / KURK / WUS
mapped as above); secondary pre-specified variant CG with constant c = 0.5 for every valid NO.

**Hypotheses (all against the same associated episodes; day bootstrap over episode dates, 2000 resamples, seed 7).**
- R1 On outage days of the nearest neighbour, CG dismisses fewer catalogue-associated episodes than P1
  (not exercised if no associated episode falls on an outage day).
- R2 CG forwards fewer unassociated alerts than P3 and fewer than P1t.
- R3 Non-inferiority of CG vs P3 on dismissed associated episodes: upper 95 % bootstrap bound of the difference <= 3 pp.
- R4 Every episode with all three neighbours MISSING is escalated by CG (not exercised if there is none).
- R5 Non-inferiority of CG-D vs P3, same margin.
- R6 Non-inferiority of CG with constant c = 0.5 vs P3, same margin.
Escalations per day are reported for every policy. The calendar-day bootstrap is reported as a sensitivity check.

**Run script:** pipeline/p10_runAK.sh (pushed with this file).

**Scorer:** analysis/ak_network.py (pushed with this file; reuses evaluate() of analysis/cgd_2024.py unchanged) →
results/ak/ak_eval.json. Run outputs go to results/ak/outAK_* (without the waveform cache), with the transfer sha256 in
results/ak/transfer_record.txt.

**Reported regardless of outcome.** Failed hypotheses are reported as failed; no threshold, weight or margin is changed
after the data are seen.
