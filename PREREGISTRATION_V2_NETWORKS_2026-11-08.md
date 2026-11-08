# Pre-registration: multi-network confirmatory test of the merged-site rule (rule v2)

Author: Syrym Zhakypbekov. Date of the plan: 08.11.2026 (written in the night of 07/08.11, Almaty). Committed and pushed before any
waveform, catalogue event or detection of the networks below was requested. The network-selection rule was pushed separately and
earlier (SELECTION_RULE_V2_2026-11-08.md and analysis/v2_select_networks.py, commit 9a8436c, pushed 2026-11-07 18:49:53 UTC) and was
then applied by that script to metadata only. The outputs of that application are in results/v2/selection/ and are pushed with this
file.

## 1. Why
Post hoc analysis 4 of the internal review (results/posthoc/review_posthoc.json, block "4_KURK_merged_site") showed that on
the II.KURK reference IU.MAKZ and IM.MK31, 24 km apart, are in the same state in 75 % of episodes, and that 179 of the 180 excess
dismissals of CG against P3 had a NO from both. Counting them as two independent neighbours explained more than half of the K3
failure (CG - P3: 10.19 pp frozen; 4.72 pp with the pair merged and weights re-ranked; 3.24 pp with G.WUS keeping 0.15). That was
found after the data were seen. This plan tests the corrected rule on networks the study has never used, with everything else frozen.

## 2. Rule v2 (exact)
- Neighbour stations of a reference are grouped into sites with D = 50 km: neighbours are taken in order of distance from the
  reference; a station joins the first existing site whose seed (its first, nearest member) is within 50 km of it, otherwise it
  becomes the seed of a new site. Site distance = seed distance. The three nearest sites are used.
- Site state per episode: YES if any member is YES; NO if no member is YES and at least one member is NO (equivalently, every
  valid member is NO); MISSING if every member is MISSING.
- One weight per site by site distance rank: 0.25 / 0.20 / 0.15; SNR weight 0.40. A member's state enters only through its site.
- Why 50 km: the one co-located pair in the study (IU.MAKZ - IM.MK31, 24 km) agreed in 75 % of episodes; in the development geometry the other
  neighbour distances are hundreds of kilometres (II.KURK 499.6 km and G.WUS 661.1 km from IU.MAKZ; IM.MK31 - II.KURK 512.7 km), so
  every D between 25 km and several hundred kilometres groups the development neighbours the same way; 50 km is about twice the only observed co-located distance and
  well below the inter-site spacing of sparse regional networks. D was fixed before the networks were selected and is part of the
  selection rule. 25 km and 100 km are reported as a sensitivity analysis only (no hypothesis).

## 3. Frozen parameters (unchanged; sources)
| item | value | source |
|---|---|---|
| detector | pipeline/extended_stalta_criteria.py, byte-identical (LF-normalised sha256 4c8c9a71…68284); STA 1 s, LTA 30 s, band 1–8 Hz, 99.9th percentile thresholds on the network's own tuning week, then frozen | PREREGISTRATION_EXTENDED.md, PREREGISTRATION_AK_NETWORK.md |
| neighbour window, coverage | d / 5.5 km/s + 5 s; observed if >= 90 % valid seconds | same pipeline |
| catalogue, association | ISC + USGS within 15 deg M >= 2.0, USGS M >= 5.5 teleseismic, de-duplication 20 s / 0.5 deg, predicted P in [t_on - 15 s, t_off] | same pipeline |
| CG | theta_A 0.60, delta 0.45, theta_D 0.16, c = 1 for a valid NO | PREREGISTRATION_KURK_EXTENDED.md |
| CG c05 | constant c = 0.5 for every valid NO | PREREGISTRATION_AK_NETWORK.md R6 |
| CG-D | IU.MAKZ development detectability table (results/prereg/detectability_tables_dev.json, table "MAKZ") mapped by site rank: rank 1 -> MK31, rank 2 -> KURK, rank 3 -> WUS; a missing bin -> p = 0.5. Documented fallback: no development table exists for a merged site or for these networks, so the rank-mapped single-station table is used, as in the AK plan | PREREGISTRATION_DETECTABILITY_2024.md, AK plan |
| baselines | P1; P1t (SNR 8.0 dB); P2 10.5 dB; P3 7.5 dB (primary comparator, as frozen); P3 8.0 dB reported as secondary comparator because results/posthoc/threshold_consistency.json shows 8.0 dB is the full-development optimum while 7.5 dB came from cross-validation | threshold_consistency.json |
| bootstrap | per network: days with episodes, 2000 resamples, seed 7 | every earlier plan |

P1, P1t and P3 depend only on "any neighbour YES" and are therefore identical under v1 and v2; P2 uses "any site NO".

## 4. Networks, stations and periods
Chosen by SELECTION_RULE_V2_2026-11-08.md, applied once by analysis/v2_select_networks.py (metadata only). Every data centre,
network and rejected configuration with its reason: results/v2/selection/datacentres.json, candidates.json, rejections.csv;
the chosen set: results/v2/selection/chosen.json; service responses: results/v2/selection/raw/ with sha256 in raw_sha256.json.

| # | region | network (data centre) | reference | site 1 | site 2 | site 3 | site outage days (<10 %) in selection window |
|---|---|---|---|---|---|---|---|
| 1 | USA-Mexico | OH (EarthScope) | OH.BSPO..HHZ (40.0431, -81.0094) | OH.O53A..BHZ 28.7 km | OH.WODO.10.HHZ 111.2 km, OH.FOXO.10.HHZ 130.1 km | OH.SROH..HHZ 121.8 km | [136, 0, 33] (W1) |
| 2 | Europe incl. Alps-Balkans | IV (INGV) | IV.CGL..BHZ (39.3660, 9.2960) | IV.DGI..HHZ 109.1 km | IV.AGLI..HHZ 196.1 km | IV.MARS..HHZ 336.0 km, IV.MTGR..HHZ 342.5 km | [165, 0, 0] (W1) |
| 3 | Caucasus-Turkey-Iran | AB (EarthScope) | AB.TELL.00.HHZ (41.7609, 48.6436) | AB.YLVJ.00.HHZ 72.0 km | AB.ZRNV.00.HHZ 109.7 km | AB.SHUR.00.HHZ 131.7 km, AB.MV12.00.HHZ 148.8 km | [66, 29, 0] (W1) |
| 4 | New Zealand-SW Pacific | AU (EarthScope) | AU.RKGY.00.BHZ (-34.6094, 116.9773) | AU.ONGER..BHZ 154.5 km | AU.NWAO..BHZ 188.6 km | AU.MUN.00.BHZ 301.1 km, AU.CARL.00.BHZ 307.9 km | [45, 19, 0] (W1) |
| 5 | South America | C1 (EarthScope) | C1.BO02..BHZ (-34.7924, -70.7814) | C1.BO01..BHZ 52.5 km | C1.BO04..BHZ 90.7 km, C1.MT09..BHZ 114.6 km | C1.MT01..BHZ 111.9 km, C1.VA05..BHZ 147.6 km | [15, 0, 0] (W1) |
| 6 | Alaska-Aleutians-Canada | AV (EarthScope) | AV.DOL..BHZ (55.1496, -161.8647) | AV.PS4A..BHZ 21.8 km, AV.DTN..BHZ 25.1 km | AV.DEER..BHZ 35.4 km, AV.BLDW..BHZ 58.8 km | AV.ISLZ..BHZ 127.1 km | [13, 0, 9] (W1) |
| 7 | Central Asia | KR (EarthScope) | KR.DRK.00.HHZ (39.4776, 71.7995) | KR.BTK..BHZ 106.6 km | KR.OHH..BHZ 143.5 km | KR.SFK.00.HHZ 157.8 km | [43, 5, 7] (W1) |
| 8 | East Asia-West Pacific | JP (EarthScope) | JP.JEM..BHZ (42.0185, 143.1535) | JP.JEW..BHZ 167.4 km | JP.JTM..BHZ 221.4 km | JP.JKA..BHZ 237.9 km | [16, 16, 16] (W2) |
| 9 | Africa | AF (EarthScope) | AF.ALKP..BHZ (-29.9418, 22.2467) | AF.UPI..BHZ 200.4 km | AF.CVNA..BHZ 292.8 km | AF.HVD.00.BHZ 320.5 km | [6, 119, 10] (W1) |
| 10 | Antarctica | AW (GEOFON) | AW.VNA1..BHZ (-70.6720, -8.2900) | AW.VNA2..BHZ 43.2 km | AW.VNA3..BHZ 80.6 km | AW.FRFJ..HHZ 158.9 km | [0, 96, 38] (W2) |

### Amendment A1 (compute budget), written before any data
The selection rule as pushed (cap 24 networks, 366-day windows) was applied first: 481 network listings seen
in 26 usable data centres, 269 eligible networks, 155 with a
valid geometry, 57 passing every metadata criterion, 24 chosen in 10 regions (results/v2/selection/chosen.json).
Because the compute available for the run is fixed (about 24 vCPU on Google Cloud plus Kaggle CPU notebooks and the laptop, for about
five hours), the run list is reduced BEFORE any data by analysis/v2_finalize_networks.py -> results/v2/networks.json:
- one uniform period for every network: tuning 2024-01-01 .. 2024-01-08, evaluation 2024-01-08 .. 2024-07-08 (182 days). Only
  networks whose passing configuration lies in W1 or W2 qualify (their stream epochs cover the period by construction); networks
  passing only in W3 are listed as "eligible, period not covered by metadata" (3);
- 10 networks, by the pushed ranking key (section 6 of the rule) and round-robin over regions (section 7), cap 10 instead of 24;
- every other passing network is listed as "eligible, not run (compute budget)" (44:
  AE, AG, BW, C, C0, CN, CO, CU, CZ, EE, EI, ET, FN, FR, HC, HE, HL, IW, KO, LD, MB, N4, ND, NE, NM, NS, NY, O2, OK, PE, PL, PQ, QZ, RV, S1, SC, SI, TX, UO, US, UU, UW, WU, WW).
The target of 20 networks in 8 regions is therefore NOT met by design of this amendment: 10 networks in 10 regions
(Africa, Alaska-Aleutians-Canada, Antarctica, Caucasus-Turkey-Iran, Central Asia, East Asia-West Pacific, Europe incl. Alps-Balkans, New Zealand-SW Pacific, South America, USA-Mexico). Iceland-North Atlantic has no passing network (none of its networks met the rule; see rejections.csv).
Data centres that returned no usable station list (recorded in datacentres.json, not retried with other parameters so as not to
change the pushed rule): NCEDC and SCEDC (HTTP 400 to the channel-level text request), KIT (connection refused), IGN and IESDMC
(empty answers); their networks contributed no candidates. Outage days in the table were computed from metadata over the 366-day selection window; outages inside the 182-day period are
decided from the processed availability only.
Compute fallback: a network whose processing has not finished by 05:00 Almaty (00:00 UTC) on 08.11.2026 is reported as
"not completed (compute)", with the chunks that did finish described but not scored; it is never dropped silently and never
replaced. The pooled analysis uses the networks completed and included under section 4.
Candidate list from a separate web-research note (KR, QZ, KZ open subset, AK, UW/CC, AF, C1, AW, NZ, IV; avoid KN, TJ, UZ, VI) was
received while the rule was being applied; it was not used to choose: every listed network went through the same pushed rule
(KZ and AK are excluded as already used; KR, AF, C1, AW, IV are among the 10; QZ and UW passed but are "eligible, not run";
NZ failed (no site with >= 3 outage days), CC failed (reference inside a dense cluster); KN, TJ, VI failed as in rejections.csv).

Roles in the run: reference "MAKZ"; neighbours "S<site>_<member>" (S1_1 = seed of the nearest site). Each network runs its own
tuning week 2024-01-01 .. 2024-01-08 and the evaluation period 2024-01-08 .. 2024-07-08 (amendment A1), in monthly or two-monthly
chunks. A chunk whose summary.json lists a catalogue failure is
reprocessed before scoring and logged as a protocol deviation; a network with an unrecovered catalogue failure or with fewer
than 30 associated episodes is excluded from the pooled analysis (reported, not replaced).

## 5. Hypotheses
Unit of analysis: catalogue-associated episodes of the reference ("dismissed" = DISMISS action on an associated episode).
Margin 3 percentage points (pp) as in every earlier plan. Relative criterion (fixed now): ratio of dismissed associated counts
(CG + 0.5) / (P3 + 0.5), pooled; it holds if the upper 95 % bound is <= 1.5.

**Primary (pooled across networks).** Pooled = all associated episodes of the included networks together (episode-weighted).
Uncertainty: two-stage cluster bootstrap, networks resampled with replacement, then days with episodes within each drawn
network, 2000 resamples, seed 7 (analysis/v2_networks.py, cluster_boot).
- V1 (primary): CG (rule v2) is non-inferior to P3 7.5 dB: upper 95 % bound of the pooled difference in dismissed share <= 3 pp.
- V1r (co-primary relative criterion): upper 95 % bound of the pooled ratio <= 1.5.
**Secondary (pooled, same bootstrap and margin):**
- V2 CG-D (rule v2) non-inferior to P3 7.5 dB.  V3 CG c05 (rule v2) non-inferior to P3 7.5 dB.
- V4 CG (rule v2) non-inferior to P3 8.0 dB (secondary baseline).
- V5 rule effect: CG v2 dismisses fewer associated episodes than the frozen v1 rule (three nearest stations, each its own weight)
  on the pooled set (difference < 0 with upper 95 % bound < 0).
- V6 CG (rule v2) forwards fewer unassociated alerts than P3 and than P1t, pooled and in a majority of included networks.
- V7 (outage, R1-type): on days when the nearest site's daily valid share is < 10 % (site share = largest member share), CG dismisses
  fewer associated episodes than P1, pooled. Counted as EXERCISED only if those days hold >= 10 associated episodes in total and
  come from >= 2 networks; otherwise reported as not exercised (the AK lesson: one-minute probes overstated outages; here outages
  are judged from the processed availability, not from the selection metadata).
- V8 every episode with all three sites MISSING is escalated by CG (not exercised if none).
- Equal-weight mean of per-network differences reported beside every pooled difference (descriptive).
**Per network (secondary).** V1 per network with the published day bootstrap; one-sided p = (draws >= 3 pp + 1)/(draws + 1);
Holm step-down across the included networks at one-sided alpha 0.025; unadjusted results also reported.

## 6. Chance-association control (fixed now)
Procedure of analysis/review_posthoc.py block 1, fixed: per network, predicted P arrivals of the catalogue shifted by uniform
1..7 days with random sign, 100 shifts, seed 7, wrapped circularly in the network's calendar span, re-associated with the pipeline
rule; reported: expected chance-associated episodes, expected chance CG - P3 excess dismissals, and the chance-corrected CG - P3
difference in pp. It is a reported control, not a hypothesis; a primary result whose chance-corrected point difference crosses
the margin when the uncorrected one does not is flagged in the text.

## 7. Code plan
- Runs: pipeline/extended_stalta_criteria.py (frozen) per network with P10_STATIONS / P10_REF=MAKZ / P10_T0 / P10_TUNE_END /
  P10_EVAL_START / P10_T1 / P10_FIXED_THR, exactly as pipeline/p10_runAK.sh. For a network outside EarthScope:
  pipeline/p10_v2_datacentre_wrapper.py with P10_FDSN_BASE = the data centre's base URL (the wrapper checks the pipeline sha256 and
  only redirects the waveform client name "EARTHSCOPE"; catalogue clients unchanged).
- Outputs: results/v2/runs/<NET>/out_<chunk>/ (without waveform cache), transfer sha256 in results/v2/runs/<NET>/transfer.txt.
- Scorer: analysis/v2_networks.py -> results/v2/v2_eval.json. Unit tests of the merge on synthetic votes:
  analysis/test_v2_networks.py (6 tests, passing at the push).
- Compute: networks in parallel on several Google Cloud VMs cloned from snapshot p10-seismic-2026-11-08 (one network per process,
  chunks in parallel as in the AK run) plus Kaggle notebooks for the remainder; the platform used per network is logged in
  EXPERIMENT_LEDGER.md. The platform does not change the code or parameters.

## 8. Stopping rule
Each chosen network runs once over its fixed window. No network is added, dropped or replaced after the first waveform request,
except by the exclusion rules of section 4 (catalogue failure not recoverable, < 30 associated episodes, or a data centre that
returns no data for the reference over the window: listed as "not run" with the error). Analysis starts when every chosen network
has either finished or been declared not run; it is run once, by the pushed scorer. A scorer bug found after the run is fixed in a
separate, logged commit, with the before/after output kept.

## 9. Reported whatever the outcome
All hypotheses are reported, including failures and non-exercised ones; no threshold, weight, margin, D, network or period is
changed after data are seen. The earlier pre-specified results (E3, K3, D1, N3, N5, R3, R5, R6) stay as published.
