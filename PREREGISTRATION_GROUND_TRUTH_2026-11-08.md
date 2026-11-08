# Pre-registration: analyst ground truth for the AK replication (ComCat reviewed vs analyst-deleted events)

Committed and pushed before any label of this test was downloaded. Author: Syrym Zhakypbekov. Date: 2026-11-08.
Runs in parallel with, and independently of, PREREGISTRATION_V2_NETWORKS_2026-11-08.md (no file of results/v2/ or
analysis/v2_fleet/ is read or written).

**Why.** Every earlier test scores alarms against catalogue association: an episode is "real" if a catalogued event's
predicted P falls in its window, and "unassociated" otherwise. Reviewers' strongest complaint is that "unassociated" is not
"false": it mixes noise, events below the catalogue threshold and chance. This test uses labels made by analysts about
individual automatic events: an event kept after review (confirmed) and an automatic event an analyst deleted (rejected).

## 1. Feasibility (metadata and documentation only; decided before any label of the study period was read)

| Candidate | Can it label OUR episodes? | Decision |
|---|---|---|
| USGS ComCat, `includedeleted=only` (documented at https://earthquake.usgs.gov/fdsnws/event/1/: "Boolean, or only … returns only deleted events"; only with format geojson or csv) and `status` = reviewed for kept events | Yes for the AK run (reference AK.CUT, 2024-01-08 .. 2025-07-01, 540 days, 17,126 episodes). The Alaska Earthquake Center (net "ak") is the authoritative network for the region and publishes automatic solutions that its analysts review or delete. Probe outside the study period (2023-12-01 .. 2023-12-31, before the tuning week 2024-01-01 .. 07, within 3 degrees of AK.CUT): 2,012 current events, all `reviewed`, 0 `automatic`; 57 deleted events (48 ak, 9 av), median M 1.3, of which 15 have a current event within 20 s and 0.5 degrees (merged duplicates) and 42 do not. | **Used (primary and only label source).** |
| KZ run (KZ.MAKZ reference) — KZ array beams MKAR/KKAR | A beam detection is another automatic detector, not an analyst decision; producing beams needs the array element waveforms and a beamforming pipeline that does not exist in this repository and cannot be validated tonight. | Not used. |
| KZ run — KNDC bulletins, IDC REB vs SEL3 | KNDC interactive bulletins list confirmed events only (no rejected automatic events in the public pages); REB/SEL3 is restricted to CTBTO-authorised users. ComCat deleted events exist only for US networks. | Not used: no public analyst-rejected label exists for KZ. The KZ run is not part of this test. |
| Meng, Huang, Ma, Ma (2026) expert verdicts (Zenodo concept DOI 10.5281/zenodo.22059218, v1.1.1 10.5281/zenodo.22288706) | Record metadata: 1,200 events of six sequences — Ridgecrest, Iquique, Amatrice, NE Japan forearc, ToC2ME, Kīlauea. None is in Alaska 2024–2025 or Kazakhstan. | Not used (no overlap with our stations or periods); cited as related work. |
| PNW-ML exotic classes (UW/CC) | Labelled signals at Pacific Northwest stations, not at AK.CUT or KZ stations. | Not used. |

## 2. Labels

Source: USGS ComCat FDSN event service, `format=csv`, circle of radius **5 degrees** around AK.CUT (62.4058, -150.2625),
origin times **2024-01-07T23:50:00 .. 2025-07-01T00:00:00 UTC** (10 min before the evaluation start so that P arrivals
inside the period are covered), monthly windows (a window returning 20,000 rows is split), all magnitudes, all event types.
Two queries per window: current events (default) and `includedeleted=only`. Every query URL, row count and sha256 is
written to results/ground_truth/labels/download_record.json.

- **CONFIRMED**: current event with status `reviewed`.
- **REJECTED**: deleted event whose id is not among current events and with no current event within 20 s and 0.5 degrees
  latitude and longitude (the pipeline's de-duplication rule).
- **DELETED_DUPLICATE** (deleted with such a twin) and **AUTOMATIC_CURRENT** (current, not reviewed): counted, not used.

## 3. Matching (fixed; identical to the pipeline's association function)

p_pred = origin time + first arrival among p, P, Pn, Pg, Pdiff (iasp91, TauP, depth = catalogue depth, 0 if missing),
distance from AK.CUT. Signed residual r = p_pred − t_on must lie in [−15 s, (t_off − t_on) + 0 s]. An episode with any
CONFIRMED candidate is **CONFIRMED**; otherwise with any REJECTED candidate **REJECTED**; otherwise **UNLABELLED**.
Self-checks run before scoring (the script stops if either fails): the travel-time function reproduces the stored p_pred
of the AK run's catalog.csv to 0.01 s (checked on 200 rows before this commit: max error 0.0000 s); the action code
reproduces the `missed` and `alert_unassoc` counts of results/ak/ak_eval.json for P1, P1t, P2, P3, CG, CG-D (checked
before this commit: identical). No label was involved in either check.

## 4. Policies (frozen, as in PREREGISTRATION_AK_NETWORK.md; no re-tuning)

P1; **P1t** (SNR 8.0 dB); P2 10.5 dB; **P3 7.5 dB** (comparator of every hypothesis); **P3 at 8.0 dB** (secondary, same rule
with the P1t threshold; descriptive only); **CG** (weights by distance rank 0.25/0.20/0.15 + SNR 0.40, δ 0.45, θ_A 0.60,
θ_D 0.16, c = 1); **CG-D** (MAKZ development detectability table, roles mapped as in the AK plan).

## 5. Metrics

For every policy and class (CONFIRMED, REJECTED, UNLABELLED): share of DISMISS, ESCALATE, ALERT; and for every action the
counts of CONFIRMED / REJECTED / UNLABELLED with the confirmed share among labelled episodes. Confidence intervals: paired
day bootstrap over episode dates, 2000 resamples, seed 7 (as every earlier test).

## 6. Hypotheses (direction and margin fixed now)

- **G1** (safety on analyst-confirmed events) CG dismisses CONFIRMED episodes no more than P3 7.5 beyond the usual margin:
  upper 95 % bound of (CG − P3) dismissed share among CONFIRMED ≤ **3 pp**.
- **G2** same for CG-D vs P3 7.5, margin 3 pp.
- **G3** (false alerts on analyst-rejected events) ALERT share among REJECTED episodes is lower for CG than for P1t and
  lower than for P3 7.5: upper 95 % bound of each paired difference (CG − comparator) **< 0**. Holds only if both hold.
- **G4** (separation) CG dismisses REJECTED episodes more readily than CONFIRMED: lower 95 % bound of
  (DISMISS share | REJECTED − DISMISS share | CONFIRMED) **> 0**. The same quantity is reported for every policy.
- Exercise rule: G1, G2 not exercised with fewer than 20 CONFIRMED episodes; G3, G4 not exercised with fewer than 20
  REJECTED episodes.

**Support** means the stated bound condition holds. A hypothesis that fails is reported as failed.

## 7. Control and interpretation fixed in advance

Chance labelling: label p_pred shifted by ±1, ±2, ±3 days, same matching; mean counts per class reported. If the mean
chance count is ≥ 50 % of the real count for a class, results for that class are reported as dominated by chance
coincidence (not interpretable as analyst labels), whatever the hypothesis outcome. Also reported: the cross-table of the
new classes with the original catalogue association, and CONFIRMED episodes by ComCat event type.
Limitations stated now: a deleted event can also be a mislocated real event that an analyst re-created with a different
time or place beyond 20 s / 0.5 degrees; deleted events are mostly very small (median M 1.3 in the probe), so REJECTED
episodes may be few; ComCat labels exist for the AK run only.

## 8. Code and outputs

Scorer: analysis/ground_truth_v2.py (pushed with this file). `download` writes results/ground_truth/labels/ (two CSV files
and the download record with sha256); `score` writes results/ground_truth/ground_truth_eval.json,
results/ground_truth/episodes_labelled.csv.gz and run logs. No threshold, weight, window, radius or margin is changed after
the labels are seen.
