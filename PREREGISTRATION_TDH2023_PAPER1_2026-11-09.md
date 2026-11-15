# Pre-registration: time-disjoint validation of the frozen Paper 1 rule on 2023 (IU.MAKZ network and AK network)

Author: Syrym Zhakypbekov. Written on 2026-11-09 and pushed BEFORE any waveform, catalogue event, detection or reviewed label of
calendar year 2023 was requested for either network below. The binding timestamp is the GitHub push of the commit that adds this
file (read back from the remote and written into results/tdh2023_p1/chronology.json). Code files named here that are not in that
commit are committed and pushed after it and before their first use; their commit times are recorded in the result.

## 1. Purpose
Paper 1 (manuscript/P10_paper1_v1_2026-11-09.md) reports the criteria-governed (CG) rule with all parameters fixed on the
development period 2026-07-01 .. 09-30 and tested on 2024-2026 at IU.MAKZ, II.KURK, the KZ network and the AK network. Every test
period lies within about two years of development. This test applies the SAME frozen rule, thresholds, detector and comparator to
calendar year 2023, which no earlier analysis of these two networks touched, to ask whether the published verdicts hold on a
time-disjoint year. Nothing is re-tuned; the outcome is reported whatever it is.

## 2. Disjointness (verified before this plan was written)
analysis/tdh2023_p1/verify_disjoint.py (requests no waveform, event or label), output results/tdh2023_p1/disjoint_check.json
(2026-11-09T02:49:47Z): 309 availability.csv, 309 episodes.csv and 310 summary.json under results/ scanned; the only files with
2023 days are the 12 runs of the 33-network test results/tdh2023/runs/<NET>/out_2023-06-01 (networks A2 AE AG AU AV C1 EE FN HC HE ND
NS; none uses a station of the two networks below); no summary.json of either network mentions 2023; the bucket gs://p10-raw-waveforms
holds no object under tdh2023_p1/, AK/ or IU/. Earlier periods of these networks: development 2026-07-01 .. 09-30 (+ held-out
2026-10), tests 2024-01-01 .. 2026-06-30; AK tuning week 2024-01-01 .. 01-07.
Disclosure: the 33-network test includes network AV (Alaska Volcano Observatory), whose pipeline catalogue (ISC + USGS within 15 deg)
and reviewed labels for 2023-05-31 .. 2023-08-31 cover a circle that overlaps the AK circle. No AK or IU.MAKZ decision, episode or
association of 2023 was computed, and those AV results were not looked at for this plan (no 2023 output of that test has been scored,
commit 1677439).

## 3. Units, detector and stations (frozen, no substitution)
- IU.MAKZ network: reference IU.MAKZ 00 BHZ; neighbours IM.MK31 (* ?HZ, first Z id in sorted order), II.KURK 00 BHZ, G.WUS 00 BHZ
  (the pipeline's default STATIONS). Detector thresholds frozen as in the extended and 2024 tests:
  {"MAKZ": 7.010977, "MK31": 7.384668, "KURK": 6.796058, "WUS": 3.490711}.
- AK network: reference AK.CUT BHZ; neighbours AK.L22K, AK.COLD, AK.E22K BHZ (roles MAKZ / MK31 / KURK / WUS as in
  pipeline/p10_runAK.sh). Detector thresholds frozen from the AK tuning week (results/ak/outAK_tune/thresholds.txt):
  {"MAKZ": 10.931966748358949, "MK31": 10.614749965111498, "KURK": 8.705359582398017, "WUS": 8.8048861838634}.
- Pipeline pipeline/extended_stalta_criteria.py unchanged (sha256 4c8c9a71..., checked by pipeline/p10_tdh_wrapper.py), run OFFLINE
  (P10_OFFLINE=1) on the raw copy stored in the bucket. Its own catalogue query (ISC + USGS regional M >= 2 within 15 deg, USGS
  teleseismic M >= 5.5) is unchanged. Station configuration file: results/tdh2023_p1/networks_tdh2023_p1.json.

## 4. Period
2023-01-01 .. 2023-12-31 (365 days; pipeline end 2024-01-01 exclusive), four quarterly chunks per network (2023-01-01, 04-01, 07-01,
10-01), each run with P10_T0 = P10_TUNE_END = P10_EVAL_START = chunk start and P10_T1 = next chunk start (as the AK and extended runs).
The whole year is a TEST period: there is no tuning window, because no parameter is tuned.

## 5. Data: download once, store, compute from the stored copy (owner rule 08.11.2026)
- analysis/tdh2023_p1/download.py (laptop, the only machine with write access to the bucket) requests every role-day once with the
  pipeline's own request: Client("EARTHSCOPE").get_waveforms(net, sta, loc, cha, day - 1800 s, day + 86400 s + 1800 s), keeps the
  first Z channel id in sorted order, writes MiniSEED <ROLE>.<YYYYMMDD>.mseed. HTTP 204 / "No data" -> empty file (true absence);
  HTTP 429 -> back-off, never stored as absent; other errors -> up to 8 attempts, then "failed" (no file), requested again in one
  later pass. Every request is recorded (results/tdh2023_p1/download/<NET>.json: stream id, bytes, state, UTC time).
- Storage: gs://p10-raw-waveforms/tdh2023_p1/<NET>/ (NET = IU_MAKZ or AK). Raw objects are never deleted. Before compute every local
  file is checked against its bucket object (same size and MD5), result in results/tdh2023_p1/runs/<NET>/bucket_verify.json; the
  pipeline then reads that verified copy offline. A role-day missing after the second pass is a reported fetch failure (the
  pipeline marks it MISSING), never re-downloaded later.
- Reviewed labels: ISC FDSN events (QuakeML, preferred origin, evaluationStatus) and USGS ComCat events (GeoJSON, status) in each
  network's pipeline circle (reference coordinates, 15 deg, M >= 2) for 2022-12-31 .. 2024-01-01 in monthly pieces, plus the ComCat
  global M >= 5.5 list, downloaded once (queries and parsers of analysis/v2_reviewed_bulletin.py) to results/tdh2023_p1/labels/
  (SHA256.txt) and copied to gs://p10-raw-waveforms/tdh2023_p1/_labels/.
- Machine: the laptop (download, bucket copy, compute). No VM is needed; if one is started it is stopped (never deleted) when its
  work ends. Kaggle is not used (it cannot read the private bucket without a second download).

## 6. Policies (frozen exactly as Paper 1, analysis/paper1_harmonised.py function actions(); no re-tuning)
P1; P3 at 7.5 dB (the registered comparator of the pre-specified tests); P3-2t (dismiss if no neighbour YES and valid SNR < 8.0 dB;
alert if any YES and valid SNR >= 10.0 dB; escalate otherwise); CG (c = 1 for a valid NO; site weights 0.25 / 0.20 / 0.15 by distance
rank, SNR weight 0.40 with min(SNR/30, 1); delta = 0.45; theta_A = 0.60; theta_D = 0.16); CG c = 0.5; CG-D (c of a NO from the
IU.MAKZ development table results/prereg/detectability_tables_dev.json by role and reference-SNR bin, as for the AK set in Paper 1).
Distances from each run's run.log ("distance_km").

## 7. Labels and endpoints
- REVIEWED catalogue row: ISC preferred origin with evaluationStatus "reviewed", or ComCat event with status "reviewed", matched to
  the pipeline's catalogue row by source, |origin time difference| <= 2 s, <= 0.5 deg, nearest in time (v2_reviewed_bulletin.label_rows).
- Reviewed-associated episode: a REVIEWED row's predicted P arrival in [t_on - 15 s, t_off] (v2_networks.assoc_vec on the REVIEWED
  rows). Self-check: assoc_vec on ALL catalogue rows must reproduce the pipeline's assoc_event flags for >= 99.5 % of episodes,
  otherwise the network is reported as failing the check and not scored on reviewed labels.
- Primary endpoint: dismissed share of reviewed-associated episodes; difference X - P3-2t in percentage points.
- Chance-corrected endpoint (per episode, non-saturating; PLAN_TIME_DISJOINT_2023_2026-11-08.md section 9): p_i = 1 - exp(-L w_i),
  w_i = (t_off - t_on) + 15 s, L = REVIEWED rows of the network whose predicted P lies in 2023 / (365 x 86400 s). Corrected difference
  X - P3-2t = 100 * sum_i (D_X,i - D_b,i)(a_i - p_i) / sum_i (a_i - p_i), a = reviewed-associated, D = dismissed. Also reported:
  sum of p_i against the reviewed-associated count, per policy.
- Workload: escalations per calendar day; unassociated alerts (alerts that are not reviewed-associated) per calendar day.
- Outage days: days on which the nearest neighbour (role MK31) has valid share < 0.10 (availability.csv).

## 8. Hypotheses
Bootstrap for all margin tests: the published paired day bootstrap (analysis/paper1_harmonised.published_boot: calendar days that
contain episodes of the endpoint population, resampled with replacement; 2000 resamples; seed 7); one-sided p = (#resamples with
difference >= 3 + 1) / (B + 1); 95 % percentile interval reported. Margin 3 percentage points (as E3, K3, D1, N3, R3).

Confirmatory family (Holm, one-sided alpha 0.025, over the hypotheses that are exercised):
- T1-<net>-<X> for net in {IU.MAKZ, AK} and X in {CG, CG c=0.5, CG-D} (6 tests): H0: X - P3-2t >= 3 points in the dismissed share of
  reviewed-associated episodes. Met after Holm = non-inferiority shown. Exercised only if the network has >= 30 reviewed-associated
  episodes.
- T2-<net> (2 tests): outage days, CG - P1 in the dismissed share of reviewed-associated episodes on outage days, H0: >= 0 (p from the
  same bootstrap over outage days, H0 boundary 0). Exercised only if >= 10 reviewed-associated outage episodes on >= 5 outage days;
  otherwise reported "not exercised" and removed from the family before Holm.
Expectation stated in advance (not a hypothesis): Paper 1's 2024-2026 results lead us to expect T1 to hold for c = 0.5 and CG-D and
possibly to fail for CG c = 1 at IU.MAKZ (E3 failed at +2.44 [1.74, 3.18] against P3 7.5).

Secondary (no multiplicity adjustment):
- S1: the T1 contrasts on the chance-corrected endpoint (same bootstrap and margin; "met" if the upper 95 % bound <= 3).
- S2: escalations per day and unassociated alerts per day, X - P3-2t, 95 % intervals from the same day bootstrap over calendar days
  with episodes (scaled to calendar days); no direction claimed in advance.
- S3: replication of the published comparator: CG - P3 7.5 and CG-D - P3 7.5 on the reviewed and on the pipeline's own catalogue
  association (the endpoint of E3, K3, D1, R3), same bootstrap and margin.
- S4: all T1 and S2 contrasts on the pipeline's catalogue association (as in Paper 1 Table 12 style).
- Descriptive: per policy and network the counts (dismissed reviewed-associated, dismissed on outage days, alerts, unassociated
  alerts, escalations), episodes per day, catalogue rows reviewed / all, fetch failures, episode duration distribution.

## 9. Completion, cutoff, deviations
- A chunk that stops with an error is run once more offline (a retry adds no data); if it still fails the quarter is "not completed"
  and the network is scored on its completed quarters, with the missing quarter reported. Nothing replaces it.
- Cutoff for compute: 2026-11-10 00:00 UTC.
- Any departure from this plan goes to results/tdh2023_p1/DEVIATIONS.md with its UTC time and reason before the affected step is
  scored where possible.

## 10. Outputs
results/tdh2023_p1/: disjoint_check.json, networks_tdh2023_p1.json, download/, labels/, runs/<NET>/out_<chunk>/ (episodes.csv,
catalog.csv, availability.csv, summary.json, run.log, triggers.csv, triggers_meta.json), tdh2023_p1_eval.json (every hypothesis with
verdict, interval, p and Holm p), chronology.json, DEVIATIONS.md, RESULTS_tdh2023.md (numbers copied by code from the JSON).
Code: analysis/tdh2023_p1/{verify_disjoint, download, labels, run, score}.py.
