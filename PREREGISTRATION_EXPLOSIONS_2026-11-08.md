# Pre-registration: alarms from explosions (quarry, mining and other blasts) under the frozen triage policies

Committed and pushed before any event-type label of the study period was downloaded or read. Author: Syrym Zhakypbekov.
Date: 2026-11-08. Independent of PREREGISTRATION_V2_NETWORKS_2026-11-08.md and PREREGISTRATION_GROUND_TRUTH_2026-11-08.md:
no file of results/v2/, analysis/v2_fleet/ or results/ground_truth/ is read or written (the ground-truth labels folder,
which holds ComCat rows with event types, was not opened).

**Why.** An explosion is a real seismic signal but not an earthquake. Every earlier test scores alarms only against
catalogue association, so an explosion counts either as an associated "event" (if catalogued at M >= 2.0 by ISC/USGS) or
as an "unassociated" alarm. A triage rule for an earthquake alarm should do neither of the two silent things with it:
DISMISS it as noise, or ALERT it automatically as an earthquake. The defensible action is ESCALATE (an analyst decides).
This test measures what each frozen policy actually does with explosion-associated alarms. The policies have no
source-type input; nothing is tuned.

## 1. Feasibility and choice of label source (documentation and out-of-period metadata only)

| Candidate | Can it label OUR episodes? | Decision |
|---|---|---|
| USGS ComCat event type (FDSN event service, parameter `eventtype`, documented at https://earthquake.usgs.gov/fdsnws/event/1/ ; vocabulary from https://earthquake.usgs.gov/fdsnws/event/1/application.json) for the AK run (reference AK.CUT, 2024-01-08 .. 2025-07-01, 540 days, 17,126 episodes) | Yes. The Alaska Earthquake Center (net "ak") types reviewed events as earthquake, explosion, ice quake etc. Probe outside the study period (2023-12-01 .. 2024-01-01, within 5 degrees of AK.CUT): 2,756 events = 2,672 earthquake, 47 ice quake, 37 explosion (most near 65.0 N, 147.4 W, about 2.9 degrees from AK.CUT, M 0.9–1.2, all `reviewed`). A comma-separated `eventtype` list is accepted (probe count 37 for "explosion,quarry blast,mining explosion" = 37 for "explosion"). | **Primary (confirmatory).** Risk stated now: explosions are small (M about 1 in the probe) and about 3 degrees away, so few may be detected by the STA/LTA at AK.CUT; X1–X4 may be "not exercised". |
| IU.MAKZ extended run with the NNC (KNDC) agency labels "mining explosion" / "earthquake" (results/nnc/episodes_nnc.csv, 308 explosion episodes, 2025-01 .. 2026-02) | Yes, but the labels were already seen: run 23 of EXPERIMENT_LEDGER.md published dismiss and alert counts for P1, P1t, P2, P3 and CG on these episodes. | **Secondary, descriptive only** (no hypothesis is tested on it). New quantities: ESCALATE shares, CG-D, P3 at 8.0 dB, intervals. |
| Kazakhstan public blast catalogue other than KNDC via ISC | KNDC bulletins are already the NNC source above; no other public typed catalogue for the KZ stations. | Not used separately. |
| PNW-ML non-earthquake classes (explosion, surface event; UW/CC) | Labelled waveforms at Pacific Northwest stations, not at AK.CUT, IU.MAKZ or KZ stations; would need a new waveform run. | Not used tonight (possible future run, needs new waveform processing). |

## 2. Labels (primary)

USGS ComCat FDSN event service, `format=csv`, circle of radius **5 degrees** around AK.CUT (62.4058, -150.2625), origin
times **2024-01-07T23:50:00 .. 2025-07-01T00:00:00 UTC**, monthly windows (a window returning 20,000 rows is split), all
magnitudes, all statuses. Three queries per window: (a) `eventtype` = the explosion family below; (b) `eventtype=earthquake`;
(c) no `eventtype` (all types; the reference for classification and the only source of OTHER_NONEQ). The filtered queries
are cross-checked against (c) and the counts reported. Every URL, row count and sha256 →
results/explosions/labels/download_record.json.

Event-type classes (ComCat vocabulary, fixed now):
- **EXPLOSION** = accidental explosion, chemical explosion, chemical_explosion, experimental explosion, explosion,
  industrial explosion, mining explosion, mining_explosion, nuclear explosion, nuclear_explosion, quarry, quarry blast,
  quarry_blast, rock burst, rock_burst, mine collapse, mine_collapse, anthropogenic_event.
- **EARTHQUAKE** = earthquake, eq.
- **OTHER_NONEQ** = every other type (ice quake, landslide, acoustic noise, sonic boom, other event, volcanic …); descriptive.

## 3. Matching (fixed; the pipeline's association function)

p_pred = origin time + first arrival among p, P, Pn, Pg, Pdiff (iasp91, TauP, depth = catalogue depth, 0 if missing),
distance from AK.CUT. Signed residual r = p_pred − t_on in [−15 s, (t_off − t_on) + 0 s]. An episode's class is the class
shared by **all** its candidate events (EXPLOSION, EARTHQUAKE or OTHER_NONEQ); **MIXED** if its candidates belong to more
than one class (reported, not used); **UNLABELLED** if none.
Self-checks run before this commit (no label involved), repeated by the scorer, which stops if any fails: the action code
reproduces `missed` and `alert_unassoc` of results/ak/ak_eval.json for P1, P1t, P2, P3, CG, CG-D (identical); p_pred
reproduces the stored p_pred of 200 AK catalogue rows (max error 0.0000 s); for the secondary analysis the recomputed P1,
P1t, P3, P2, CG actions equal the action columns of results/nnc/episodes_nnc.csv on all 15,208 episodes (identical).

## 4. Policies (frozen; no re-tuning)

P1; **P1t** (SNR 8.0 dB); P2 10.5 dB; **P3 7.5 dB** (comparator); **P3 at 8.0 dB** (secondary, descriptive); **CG**
(weights by distance rank 0.25/0.20/0.15 + SNR 0.40, δ 0.45, θ_A 0.60, θ_D 0.16, c = 1); **CG-D** (MAKZ development
detectability table, roles mapped as in the AK plan).

## 5. Metrics

For every policy and class: share of DISMISS, ESCALATE, ALERT (with 95 % intervals for EXPLOSION). For every policy: the
number of its originally "unassociated" ALERTs (the R2 count of the AK plan) that fall in each class. Original catalogue
association of the EXPLOSION episodes (associated / unassociated in the AK run). SNR quantiles and UTC hour of EXPLOSION
episodes. Intervals: paired day bootstrap over episode dates, 2000 resamples, seed 7 (as every earlier test).

## 6. Hypotheses (primary, AK; direction and margin fixed now)

- **X1** (no silent dismissal) CG dismisses EXPLOSION episodes no more than P3 7.5 beyond the usual margin: upper 95 %
  bound of (CG − P3) DISMISS share among EXPLOSION episodes **≤ 3 pp**.
- **X2** same for CG-D vs P3 7.5, margin 3 pp.
- **X3** (no automatic earthquake alert for explosions) ALERT share among EXPLOSION episodes is lower for CG than for P1t
  and lower than for P3 7.5: upper 95 % bound of each paired difference (CG − comparator) **< 0**. Holds only if both hold.
- **X4** (routing to an analyst) CG escalates EXPLOSION episodes more often than EARTHQUAKE episodes: lower 95 % bound of
  (ESCALATE share | EXPLOSION − ESCALATE share | EARTHQUAKE) **> 0**. Expected direction because explosions in this region
  are small (lower SNR, fewer neighbour detections); CG has no source-type input, so a failure is plausible and will be
  reported. The same quantity, and the DISMISS difference, are reported for every policy.
- Exercise rule: X1–X3 not exercised with fewer than **20** EXPLOSION episodes; X4 not exercised with fewer than 20
  EXPLOSION or fewer than 20 EARTHQUAKE episodes.

**Support** means the stated bound condition holds. A hypothesis that fails is reported as failed; a hypothesis that is not
exercised is reported as not exercised, never as held.

## 7. Control and interpretation fixed in advance

Chance labelling: label p_pred shifted by ±1, ±2, ±3 days, same matching; mean counts per class reported. If the mean
chance count is ≥ 50 % of the real count for a class, results for that class are reported as dominated by chance
coincidence, whatever the hypothesis outcome. Limitations stated now: ComCat event types are analyst judgements (not
ground truth); an unclassified explosion typed "earthquake" would be scored as EARTHQUAKE; the secondary KZ analysis
reuses labels already seen and is descriptive only.

## 8. Code and outputs

Scorer: analysis/explosions_v2.py (pushed with this file). `selfcheck` (no labels), `download` writes
results/explosions/labels/ (three CSV files, download record with sha256, run_download.log), `score` writes
results/explosions/explosions_eval.json, results/explosions/episodes_labelled.csv.gz and results/explosions/run.log.
No new waveform processing is needed. No threshold, weight, window, radius, type list or margin is changed after the labels
are seen.
