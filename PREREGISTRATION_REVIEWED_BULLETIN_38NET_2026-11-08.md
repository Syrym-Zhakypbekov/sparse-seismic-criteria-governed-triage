# Pre-registration: rule v2 on the 38 multi-network networks scored against analyst-reviewed bulletins

Written and pushed on 2026-11-08, BEFORE any reviewed-bulletin label of these networks was downloaded and before any decision
outcome on reviewed labels was computed. The binding timestamp of this retrospective test is the time of the GitHub push of the
commit that adds this file. An OSF registration of the same text follows; it is a copy, not the timestamp of record.

## 1. Why
The multi-network test (PREREGISTRATION_V2_NETWORKS_2026-11-08.md, batch B, ext12) used catalogue association as its outcome,
where the catalogue mixes reviewed and automatic solutions. Analyst labels were available only for Alaska
(PREREGISTRATION_GROUND_TRUTH_2026-11-08.md). This test re-scores the same frozen decisions of the same 38 networks against
events that an analyst has reviewed.

## 2. What was checked before writing (metadata only, 2026-11-08 ~04:35 UTC)
- ISC: the Reviewed ISC Bulletin "is currently up to 2024-11-01" (http://www.isc.ac.uk/iscbulletin/, read 2026-11-08). The
  evaluation period 2024-01-08 .. 2024-07-07 is inside it. In the ISC FDSN QuakeML an ISC-relocated preferred origin carries
  evaluationMode manual and evaluationStatus reviewed. A preferred origin from a contributing agency carries neither (one
  probe window, 2024-03-01 00:00–03:00, Central Asia: one ISC reviewed event in Kyrgyzstan, one TEH event without status).
- USGS ComCat: each event has properties.status ("reviewed" / "automatic"). Probe 2024-03-01, central USA: 14 events, all "reviewed".
- Central Asia (KR, QZ): covered by ISC (contributing agencies include KRNET, Kyrgyz Republic).
- No episode, decision or association with these labels was computed.

## 3. Networks, episodes and decisions (unchanged)
- The 38 networks included in the batch-A + batch-B pooled analysis (results/v2/v2_eval_AB.json, included_in_pooled = true):
  AE AG AU AV BW C0 C1 CN CO EE ET FN HC HE HL IV IW JP KR MB N4 ND NE NM NS NY OH OK PE PL QZ RV SI TX UO UU UW WW.
  Batch A: AU AV C1 IV JP KR OH. Batch B: the other 31.
- Episodes, site states, SNR and the actions of every policy: exactly as computed by analysis/v2_networks.py (rule v2,
  frozen parameters, P1, P1t, P2, P3 7.5, P3 8.0, CG, CG-D, CG_c05, CG_v1). No decision rule changes.

## 4. Labels
- The catalogue rows each network's pipeline already stored (results/v2/runs/<NET>/out_*/catalog.csv; ISC + USGS regional
  M >= 2 within 15 deg, USGS teleseismic M >= 5.5) are labelled one by one:
  - REVIEWED: an ISC row whose event's preferred origin in the ISC FDSN service has evaluationStatus "reviewed", or a USGS row
    whose ComCat event has status "reviewed". A row is matched to the bulletin event by source, |origin time difference| <= 2 s
    and epicentral difference <= 0.5 deg; several candidates: the nearest in time.
  - NOT REVIEWED: any other row (agency-only origin in ISC, automatic in ComCat, or no match).
- Episode labels use the pipeline's association rule unchanged (analysis/v2_networks.py assoc_vec: predicted P in
  [t_on - 15 s, t_off]):
  - REVIEWED-ASSOCIATED: associated with at least one REVIEWED row. This is the denominator of every dismissal hypothesis.
  - Otherwise: not reviewed-associated. Counted as unassociated for the alert hypothesis V6.
- Self-check, before any score: assoc_vec on ALL catalogue rows must reproduce the stored association flags of every network
  (agreement >= 99.5 % of episodes per network). Otherwise the script stops and the failure is reported.
- Completeness rule: a period is usable if it is inside the Reviewed ISC Bulletin's stated range (here: all of it). A network
  enters the pooled analysis with >= 30 reviewed-associated episodes (as MIN_ASSOC); otherwise it is reported as "too few
  reviewed-associated episodes".
- Secondary label (reported, not a hypothesis): REVIEWED-OR-ACCEPTED = REVIEWED plus ISC rows whose event appears in the ISC
  service at all, i.e. accepted into the bulletin without ISC relocation.

## 5. Hypotheses (same margin 3 pp, same two-stage cluster bootstrap, 2000 resamples, seed 7, Holm per network)
- R1 (primary): CG (c = 1) vs P3 7.5 dB, dismissed share of REVIEWED-ASSOCIATED episodes, pooled over all included networks:
  upper 95 % bound <= 3 pp.
- R1r: ratio of dismissed counts (+0.5): upper bound <= 1.5.
- R2: CG-D vs P3 7.5, as R1. R3: CG_c05 vs P3 7.5, as R1.
- R7: on outage days of the nearest site, CG dismisses fewer REVIEWED-ASSOCIATED episodes than P1 (exercised with >= 10 such
  episodes from >= 2 networks).
- Reported: V5 (CG v2 vs CG v1), V6 (unassociated alerts with this label), V8, per-network contrasts with Holm.
- Chance control: the shifted-catalogue control of analysis/v2_networks.py (100 shifts of 1..7 days, seed 7), applied to the
  REVIEWED rows only.
- Secondary set (reported, not replacing the primary): the same analysis without networks whose published chance share is
  > 0.5 (results/v2/NETWORK_CHECK.md, computed before this plan): JP (0.946). The primary analysis includes all 38.
- Results are also given per batch (A: 7, B: 31).

## 6. Code
analysis/v2_reviewed_bulletin.py: `download` (labels -> results/v2_reviewed/labels/, sha256 recorded), `score`
(-> results/v2_reviewed/v2_eval_reviewed.json, per-network table v2_reviewed_table.md). It imports v2_networks.py and changes
only the association flags and the catalogue passed to the chance control.

## 7. Reported whatever the outcome
Every network with counts of REVIEWED / NOT REVIEWED rows and reviewed-associated episodes, every verdict, every deviation with
its time.
