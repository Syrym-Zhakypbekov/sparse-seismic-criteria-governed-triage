# Pre-registration: time-disjoint confirmatory test (June–August 2023) at matched operating points with a chance-corrected endpoint

Author: Syrym Zhakypbekov. Written on 2026-11-08 and pushed BEFORE any waveform, catalogue event, detection or reviewed label of
the test period below was requested for any of the networks below. The binding timestamp is the GitHub push of the commit that
adds this file (read back from the remote and recorded in RESULT_TIME_DISJOINT_2023.md). Code files named here that are not in
that commit are committed and pushed after it and before their first use; their commit times are recorded in the result.

## 1. Why
The cold review of manuscript v34 (C:/review_p10/cold_v34_0811, reviewer files panel_files/fable.md findings 1–3 and
hostile_opponent/astra.md findings 5, 7, 8) raised three MAJOR points that new analyses of already-scored data cannot answer:
1. No test is confirmatory on data untouched by earlier analyses; the 33-network reviewed-bulletin test re-labels decisions that
   had already been analysed (Fable 3, Astra 5, Astra 7 "use event-disjoint and time-disjoint validation").
2. The dismissal threshold theta_D = 0.16 was frozen on a sparse development catalogue, so the verdicts on the weight c of a
   non-confirmation are calibration-transfer results. A comparison of rules is meaningful only at matched operating points, with
   every rule tuned by ONE procedure on the same tuning window (Fable 1, Astra 8).
3. The endpoint "dismissed reviewed-associated alarms" is dominated by chance time matches (shifted-catalogue control: 132.7 of
   P3's 151 such dismissals expected by chance) and the shifted-catalogue correction saturates; a per-episode, non-saturating
   chance correction is needed, with a pre-set exclusion of chance-dominated networks (Fable 2).
Two minor points are answered in the same test: a pre-set alarm-rate bound (Fable 8) and the chance-YES control from stored
neighbour trigger times (Fable 9).

## 2. Disjointness of the test period (verified before this plan was written)
Script analysis/tdh2023/verify_disjoint.py, output results/tdh2023/disjoint_check.json (run 2026-11-08 ~11:20 UTC, before this
file existed; it requests no waveform, event or detection). It scanned 146 status.json, 298 summary.json and 297 availability.csv
files under results/ (all run, rescue, replicate, staging and Kaggle copies), the listing of the bucket gs://p10-raw-waveforms
(635 objects, saved as results/tdh2023/bucket_listing_before_plan.txt) and 43 plan files in the repository root.
- Every unit network below was first touched on 2024-01-01 (detector tuning week of batch A/B); the latest day touched is
  2024-07-08 or 2025-01-08 (ext12/ext12B). A2, CA and OT were never run. No run artefact of ANY network lies in 2023.
- The bucket holds only derived outputs (_derived/ext12B, July 2024 – January 2025); no raw MiniSEED and no object with 2023 in
  its path.
- The only plan-file dates inside 2023-05-25 .. 2023-08-30 are the bounds of selection window W1 in SELECTION_RULE_V2_2026-11-08.md.
- Disclosure: for 27 of the 33 networks (selection window W1: AE AU AV BW C0 C1 CN ET FN HC HE HL IV IW KR MB ND NM NY OH OK PL
  RV SI UU UW WW) the selection script read station epochs and daily availability METADATA over 2023-07-08 .. 2024-07-08 when
  their configuration was chosen. No waveform, catalogue event, detection or decision of 2023 was ever requested or computed.
- Reviewed ISC Bulletin coverage: reviewed up to 2024-11-01 (ISC page read 2026-11-08 ~04:35 UTC, recorded in
  PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md §2). USGS ComCat events carry a per-event review status.
- No overlap was found, so the default window is kept.

## 3. Units
- The 33 networks of the reviewed-bulletin test (results/v2_reviewed/v2_eval_reviewed.json, included_in_pooled = true):
  AE AG AU AV BW C0 C1 CN EE ET FN HC HE HL IV IW JP KR MB ND NE NM NS NY OH OK PL RV SI UO UU UW WW.
  Each keeps its frozen station configuration (results/v2/networks.json or networks_batchB.json; roles and streams as in
  results/v2/runs/<NET>/status.json), its frozen detector thresholds (status.json "thresholds", tuned on 2024-01-01 .. 01-07;
  NO detector re-tuning) and the frozen pipeline (pipeline/extended_stalta_criteria.py, sha256 4c8c9a71… checked by the wrapper).
  Site states follow rule v2 (analysis/v2_networks.merge_sites).
- Candidates A2, CA, OT (passing candidates of the frozen selection rule, never run; their passing configuration was found in
  window W3 only). A candidate is included only if the frozen selection rule, applied to the 2023 window, passes. Procedure
  (analysis/tdh2023/select_candidates.py, metadata only, run after this push and before any waveform request): sections 3–6 of
  SELECTION_RULE_V2_2026-11-08.md with the code copied from analysis/v2_select_networks.py; the only change is one window
  T23 = detector tuning week 2023-05-25 .. 06-01 and 90 evaluation days 2023-06-01 .. 08-30 (channel epochs must cover
  2023-05-25 .. 08-30); the availability criteria are computed on those 90 days with the same proportions: reference share
  >= 0.90 on >= 90 % of days; at least one site with >= 3 days of share < 0.10; every neighbour stream share > 0 on >= 45 days.
  The configuration ranked first by section 6 is used, whether or not it equals the W3 configuration. An included candidate has
  no frozen thresholds, so its detector is tuned once by the frozen procedure (99.9th percentile per role) on the 7 days
  2023-05-25 .. 05-31, as every first-run network of the programme was. A failing candidate is reported with the reason.
  Output: results/tdh2023/candidates_2023.json. The final run list results/tdh2023/networks_tdh2023.json is committed and pushed
  before the first waveform request.

## 4. Period
- 90 days 2023-06-01 .. 2023-08-29 (pipeline end 2023-08-30, exclusive), one pipeline chunk per network (as the quarterly chunks
  of the earlier runs; P10_CHUNK_MONTHS 3).
- Days 1–30 (2023-06-01 .. 06-30): TUNING window for the decision thresholds (section 7). Days 31–90 (2023-07-01 .. 08-29, 60
  days): TEST window. A network-day is a calendar day present in the network's availability.csv.

## 5. Data: download once, store, compute from the bucket (owner rule 08.11.2026)
- analysis/tdh2023/download_raw.py, run on the fleet VMs, requests every role-day once from the network's own data centre with the
  pipeline's own request: Client(<data centre> or "EARTHSCOPE").get_waveforms(net, sta, loc, cha, day − 1800 s, day + 86400 s +
  1800 s), first vertical channel id in sorted order, written as MiniSEED. HTTP 204 / "No data" -> empty file (true absence);
  HTTP 429 -> back-off, never stored as absent; other errors -> up to 8 attempts, then "failed" (no file), retried in a later pass.
- Storage: gs://p10-raw-waveforms/tdh2023/<NET>/<ROLE>.<YYYYMMDD>.mseed and a manifest gs://p10-raw-waveforms/tdh2023/_manifest/<NET>.json
  (stream per role; per day bytes, "nodata" or "failed"). Raw objects are never deleted. A local copy on a VM is removed only after
  the bucket object of the same size is listed.
- Load: EarthScope networks are spread over six VMs in the USA and Europe; EIDA networks (GEOFON, INGV, LMU, NOA, EPOS-France,
  UIB-NORSAR) are requested from the European VMs; back-off per data centre.
- Every computation reads the bucket: the compute step copies gs://p10-raw-waveforms/tdh2023/<NET>/ into a fresh local cache and
  runs the frozen pipeline offline through pipeline/p10_tdh_wrapper.py, which disables waveform requests. A role-day missing from
  the bucket becomes a reported fetch failure, never a new download. The pipeline's own catalogue query (ISC + USGS regional
  M >= 2 within 15 deg, USGS teleseismic M >= 5.5) is unchanged.
- Reviewed labels: analysis/tdh2023/labels.py downloads, once, the ISC FDSN events (QuakeML, preferred origin) and USGS ComCat
  events (GeoJSON, status) in each network's pipeline query circle and the ComCat global M >= 5.5 list for 2023-05-31 .. 2023-08-31
  (the queries of analysis/v2_reviewed_bulletin.py); stored in results/tdh2023/labels/ (sha256 list) and copied to
  gs://p10-raw-waveforms/tdh2023/_labels/.

## 6. Neighbour trigger times (stored for the chance-YES control)
The frozen pipeline keeps every role's trigger list (variable trig: onset, end, peak) in memory but writes only YES / NO / MISSING
per neighbour. pipeline/p10_tdh_wrapper.py runs the frozen pipeline unchanged (same sha256 check, same data-centre redirect) and,
after the pipeline has written all its outputs, writes triggers.csv (role, t_on, t_off, peak_cft) and triggers_meta.json (YES
window d/5.5 km/s + 5 s per neighbour role) from the finished run's globals. No decision code changes.
Verification BEFORE the main compute: an earlier network with raw data on the laptop (S1, rescue run, frozen thresholds of
results/v2/runs_rescue/S1/status.json), days 2024-01-24 .. 2024-01-27, run once through pipeline/p10_v2_datacentre_wrapper.py and
once through pipeline/p10_tdh_wrapper.py (offline) on the same cache. Pass = episodes.csv byte-identical between the two runs, and
the decision columns (t_on, t_off, peak_cft, snr_db, snr_status, n_*, cov_*) equal to the stored S1 episodes of the same days
(episodes within 300 s of the end of the short span excluded, because the original run also saw the next day). Output:
results/tdh2023/wrapper_check.json. If it fails, the main compute does not start and the failure is reported.

## 7. Tuning: ONE procedure for every rule (days 1–30, reviewed labels)
- Pool: all networks passing inclusion steps (a) and (b) of section 8.
- Target workload E* = escalations of P3-2t at its review4 training setting (tD 8.0 dB, tA 13.5 dB) on the tuning days, pooled,
  divided by the pooled network-days of the tuning window.
- Reject-band rules and grids:
  - P3-2t: dismiss if no site is YES and the SNR is valid and < tD; alert if any site is YES and the SNR is valid and >= tA;
    escalate otherwise. tD in 5.0, 5.5, …, 12.0 dB; tA in tD, tD + 0.5, …, 20.0 dB (the review4 grid).
  - CG c = 1, CG c = 0.5, CG-D (rule v2: site weights 0.25 / 0.20 / 0.15 by rank, SNR weight 0.40, delta = 0.45 fixed, CG-D table
    unchanged): theta_D in 0.04, 0.05, …, 0.40; theta_A in max(0.40, theta_D + 0.01), …, 0.90 in steps of 0.01 (the grids of
    the forward re-tuning, Appendix H, analysis/gap2.py).
- Choice per rule: among the settings whose pooled escalations per network-day on the tuning days are within ±5 % of E*, the one
  that dismisses the fewest reviewed-associated alarms on the tuning days; ties: fewest unassociated alerts; then escalations
  closest to E*; then the smaller dismissal threshold; then the smaller alert threshold. If no setting is within ±5 %, the setting
  with escalations closest to E* (same ties), reported as such. Every rule is re-tuned by this procedure, P3-2t included (its
  chosen setting may differ from 8.0 / 13.5).
- Single-threshold rules (secondary, descriptive): P1 (no parameter) at its frozen definition; P3 at the frozen 7.5 dB; P3 tuned
  on t in 5.0, 5.25, …, 12.0 dB (i) by the procedure without the escalation match (fewest tuning-day reviewed-associated
  dismissals; ties fewest unassociated alerts, then the larger t) — this selects a low t and is reported for completeness — and
  (ii) with the escalations closest to E* (ties as above). All rules are also reported at their frozen thresholds (CG family
  theta_D 0.16 / theta_A 0.60; P3-2t 8.0 / 13.5) on the test days.
- Output: results/tdh2023/tuning.json (E*, every grid point's pooled tuning-day escalations, dismissals and unassociated alerts,
  the chosen settings). Thresholds are not changed after this step; exclusions in step (d) do not trigger re-tuning.

## 8. Inclusion (pre-set, applied in this order)
- (a) Completion: the network's chunk has episodes.csv. A chunk without outputs = "not completed (compute)" or "not completed
  (data)", excluded, never partially scored, not replaced. Fetch failures are reported per network.
- (b) Alarm rate: reference episodes on the tuning days / tuning network-days <= 200 per day. Otherwise excluded (reported with
  its counts).
- (c) Tuning (section 7) on the networks passing (a) and (b).
- (d) Chance share: on the TUNING days, at the P3-2t setting chosen in (c), S = sum over episodes dismissed by P3-2t of p_i
  divided by max(A, 1), where A = reviewed-associated episodes dismissed by P3-2t and p_i is the per-episode chance probability of
  section 9 with Lambda from the tuning days. S > 0.5 -> excluded from the primary analysis and reported separately; a secondary
  analysis with these networks included is also reported.
- (e) Primary pooled set: networks passing (a)–(d) with >= 10 reviewed-associated episodes on the test days (the earlier minimum of
  30 over 182 days, scaled to 60 days) and no catalogue failure. Self-check (as the reviewed-bulletin test): v2_networks.assoc_vec
  on all catalogue rows must reproduce the pipeline's association flags for >= 99.5 % of the network's episodes; a network failing
  it is reported and excluded.

## 9. Endpoint: reviewed association and the per-episode chance correction
- Labels as PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md §4: a catalogue row is REVIEWED if its ISC preferred origin has
  evaluationStatus "reviewed" or its ComCat event has status "reviewed" (matched by source, |origin time difference| <= 2 s,
  <= 0.5 deg, nearest in time). An episode is reviewed-associated if a REVIEWED row's predicted P arrival lies in
  [t_on − 15 s, t_off] (v2_networks.assoc_vec).
- Per-episode chance probability: p_i = 1 − exp(−Lambda_s · w_i), where w_i = (t_off − t_on) + 15 s is the association window and
  Lambda_s = (number of REVIEWED catalogue rows of network s whose predicted P arrival falls in the period) / (number of seconds in
  the period: calendar days × 86400). Period = the test days for the endpoint, the tuning days for step 8(d).
- For rule r: raw count A_r = reviewed-associated episodes dismissed by r; chance-corrected count C_r = A_r − sum over all episodes
  dismissed by r of p_i; chance-corrected denominator N_c = (reviewed-associated episodes) − sum over all episodes of p_i;
  chance-corrected dismissed share = C_r / N_c. The pooled difference of rule r minus rule b is
  100 · sum_i (D_r,i − D_b,i)(a_i − p_i) / sum_i (a_i − p_i), where D = dismissed (0/1) and a = reviewed-associated (0/1).
- Reported per network and pooled: raw and corrected counts and shares of every rule; Lambda_s; sum of p_i against the
  reviewed-associated count; episode duration (t_off − t_on) and window width w (median, 10th and 90th percentile, mean).

## 10. Hypotheses (test days 31–90, primary pooled set, each rule at its tuned setting)
- H1 (primary, the only confirmatory test; one-sided): CG c = 0.5 minus P3-2t in the chance-corrected dismissed share of
  reviewed-associated alarms. Two-stage cluster bootstrap as analysis/v2_networks.cluster_boot (networks with replacement, then
  the days with episodes within each drawn network; 2000 resamples; seed 7). H1 holds if the upper bound (97.5th percentile) of
  the corrected difference is at most 3 percentage points AND the upper bound of the ratio of raw dismissed counts
  (A_c05 + 0.5) / (A_P3-2t + 0.5) is at most 1.5 (the joint criterion of the paper; "at most" as in the paper's code, and a bound
  exactly on a margin is reported as such).
  Refutation: H1 is not supported ("non-inferiority not established") if either upper bound exceeds its margin. "Excess shown"
  is stated only if the lower bound of the corrected difference exceeds 3 points.
  Sensitivity (reported, not replacing the verdict): (i) shared-calendar bootstrap — networks with replacement and ONE common
  resample of test calendar days applied to every drawn network (circular blocks of 1 and 7 days; 2000 resamples; seed 7);
  (ii) the raw (uncorrected) difference with the same bootstrap; (iii) the secondary set including networks excluded by 8(d).
- H2 (secondary, two-sided, NO direction claimed in advance): unassociated alerts (alerts that are not reviewed-associated) per
  network-day, CG c = 0.5 minus P3-2t: difference and ratio ((U + 0.5) ratio) with 95 % intervals from the two-stage bootstrap
  over networks and calendar test days. A direction is stated only if the 95 % interval of the difference excludes 0.
- H3 (secondary): as H1, for CG-D minus P3-2t (H3a) and for CG c = 1 minus P3-2t (H3b), each at its own tuned setting.
- H4 (descriptive): chance confirmations by neighbours.
  - Per network and neighbour site: each member's trigger onsets (triggers.csv) shifted by k · 3600 s, k = ±1, …, ±10, circular
    within the chunk span; a shifted YES = a shifted onset within the pipeline's window (|onset − t_on| <= d/5.5 + 5 s) of the
    reference onset; for every test-day episode at which the site is not MISSING. Chance-YES rate = mean over the 20 shifts of the
    share of such episodes with a shifted YES; reported beside the observed YES share.
  - Self-check: unshifted onsets must reproduce the stored YES states for >= 99.9 % of (site, episode) pairs; otherwise H4 is
    reported as not computable for that network.
  - Discounting: per site and day, p^Y = the site's chance-YES rate on that day (over the 20 shifts and that day's test episodes at
    which the site is not MISSING; a day with fewer than 5 such episodes uses the site's test-period rate). Because the probability
    that an observed YES is chance is at least p^Y, a YES with p^Y > 0.5 is more likely than not attributable to chance; such YES
    states are set to MISSING and the H1 statistic is recomputed at the tuned settings (no re-tuning). Whether the H1 verdict
    changes is reported (descriptive, not a test).
- Only H1 is confirmatory; H2–H4 and all sensitivities are secondary or descriptive and carry no multiplicity adjustment.

## 11. Post hoc, separate (not part of this test)
The per-episode estimator of section 9 is applied to the existing 33-network reviewed data (decisions and labels as in
results/v2_reviewed/v2_eval_reviewed.json via results/posthoc/_collect_reviewed.pkl; durations from
results/v2/runs/<NET>/out_*/episodes.csv; Lambda from the reviewed catalogue rows over the evaluation days), so that the
manuscript can report a non-saturating correction of the existing headline. Output results/posthoc/chance_per_episode_33net.json,
labelled POST HOC; it enters no hypothesis of this plan.

## 12. Compute, cutoff, chronology
- Machines: VMs p10-fleet-1 .. p10-fleet-6 (project astra-placement-iitu), started for this run and stopped (never deleted) when it
  ends or at the latest 8 hours after start; the laptop; Kaggle as a spare. VM p10-seismic is not used.
- Cutoff: 2026-11-08 20:30 UTC. A network whose chunk is not finished by then is "not completed (compute)"; nothing is started in
  its place.
- Chronology recorded in the result: push time of this plan (git log and the GitHub remote), commit times of the code files, the
  time of the first waveform request (first manifest entry), the time of the first label request, the time of scoring.
- Any departure from this plan goes to results/tdh2023/DEVIATIONS.md with its UTC time and reason, before the affected step is
  scored where possible.

## 13. Outputs
results/tdh2023/: disjoint_check.json, candidates_2023.json, networks_tdh2023.json, wrapper_check.json, runs/<NET>/ (pipeline
outputs incl. triggers.csv), labels/, tuning.json, per_network/<NET>.json, tdh2023_eval.json (every hypothesis with its verdict and
intervals), chance_yes.json, durations.json, PROGRESS.md, DEVIATIONS.md; results/posthoc/chance_per_episode_33net.json;
RESULT_TIME_DISJOINT_2023.md with every number copied by code (analysis/tdh2023/write_result.py) from the JSON files.
Code: analysis/tdh2023/{verify_disjoint, select_candidates, make_networks, download_raw, run_tdh, labels, score,
posthoc_chance_33net, write_result}.py, pipeline/p10_tdh_wrapper.py.

## 14. Reported whatever the outcome
Every network with its inclusion path and reason, every chosen setting, every hypothesis verdict with its interval, every
deviation with its time.
