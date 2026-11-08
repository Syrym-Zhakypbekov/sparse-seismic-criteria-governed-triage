# Rule-v2 fleet runs: runner-only deviations and not-run networks (log)

Method, parameters, pipeline (sha256 4c8c9a71...68284) and run lists are unchanged. Only the fleet runner
(analysis/v2_fleet/) changed during the run; each change, its commit and its effect:

| commit | change | effect on data |
|---|---|---|
| 3e4ea4d | fleet tooling first pushed (after pre-registration 4464e34) | none |
| 421503c | slot runner + assignment; scp path fix | none |
| 71031f6 | threshold-line parser read `nan` as `'n'` and crashed (AB, C at 19:22-19:23 UTC); now a NaN threshold ends the network as `tuning_failed`, as p10_runAK.sh did (asserts every threshold finite) | none (AB, C re-run only to write status) |
| dd077cb | Kaggle kernel builder lacked networks_batchB.json: Kaggle v1 kernels ran nothing ("network not found") | none; re-pushed |
| aed0bf1 | tuning-week process stopped once the thresholds line is printed. The frozen pipeline also evaluates one day after tuning and fetches its catalogue; an empty one-day USGS catalogue (HTTP 204) in quiet regions was retried ~36 min. Only the thresholds are used (as in p10_runAK.sh). Networks then in that retry (AF, AU, IV, AW, NS, S1, AB) were stopped and re-queued; their waveform cache was deleted by the slot and re-downloaded | thresholds identical (computed from the same tuning-week data before the stop) |

## Not run (tuning failed: no data in the tuning week 2024-01-01..2024-01-08 for a role), frozen procedure kept (authors' decision 08.11)
| network | roles with NaN threshold | evidence |
|---|---|---|
| AF | all four (MAKZ=AF.ALKP..BHZ, S1_1 AF.UPI, S2_1 AF.CVNA, S3_1 AF.HVD.00) | EarthScope dataselect HTTP 204 for AF.ALKP BHZ on 2024-01-02, 01-05, 02-15, 04-01 (loc '', '--', '*'; cha *), checked 08.11 ~00:45 Almaty |
| AB | S1_1 (AB.YLVJ.00.HHZ) | NaN threshold in tune run.log |
| C | S1_1 (C.GO03..BHZ), S2_1 (C.GO04..BHZ) | NaN threshold in tune run.log |
| S1 | S1_1 (S1.AUPHS..BHZ), S3_1 (S1.AULRC..BHZ) | NaN threshold in tune run.log (AusPass) |
| AW | S3_1 (AW.FRFJ..HHZ) | NaN threshold in tune run.log (GEOFON) |
| FR | S1_1 (FR.SMPL.00.BHZ) | NaN threshold in tune run.log (EPOS-France) |

Independent check 08.11 ~00:55 Almaty (laptop, obspy 1.5.1, same data centres, 10-min request at 00:00 UTC of each tuning day
2024-01-01..07): every NaN role above answered "no data" (HTTP 204) on all 7 days; no download error. So these are true absences,
not transient failures. From commit 1e27995 the runner records this per day in status.json (tune_nan_evidence) and retries the
tuning run when a NaN role has a failed download instead of a no-data answer.

## ext12 (PREREGISTRATION_V2_EXT12_2026-11-08.md, b23608a) — runner-only support
- load_cfg also reads results/v2/networks_ext12.json and matches the "id" field (OH_EXT12 ...); a plain code still resolves to batch A first.
- An *_EXT12 id does no tuning: thresholds = "thresholds" of results/v2/runs/<NET>/status.json (frozen batch A, same machine that ran
  batch A), passed as P10_FIXED_THR; without finite batch-A thresholds the ext run is recorded "not_run_no_batchA_thresholds".
- Outputs go to results/v2/runs_ext12/<NET>/ only. Eval 2024-07-08..2025-01-08, chunks 07-08..10-08 and 10-08..2025-01-08.
- Queued on each machine after that machine's batch-A/B queues are empty (waiter on slots.log), same machine as its batch-A run
  (OH p10-seismic, IV fleet-1, AU fleet-3, C1 fleet-4, AV fleet-5, KR fleet-6, JP laptop).

## Rebalancing (runner-only, no method change)
Not-yet-started networks were moved from a queue to a free machine (marker DONE+MOVED on the source so its slot skips them) or to Kaggle; each runs once, on one platform:
```
19:56:03 MOVED NE from laptop to kaggle: Kernel version 1 successfully pushed.  Please check progress at https://www.kaggle.com/code/syrym95/p10-v2-ne
19:58:29 MOVED CO from p10-fleet-6 to kaggle: Kernel version 1 successfully pushed.  Please check progress at https://www.kaggle.com/code/syrym95/p10-v2-co
20:00:57 MOVED AG from p10-fleet-5 to kaggle: Kernel version 1 successfully pushed.  Please check progress at https://www.kaggle.com/code/syrym95/p10-v2-ag
20:03:25 MOVED N4 from p10-fleet-6 to kaggle: Kernel version 1 successfully pushed.  Please check progress at https://www.kaggle.com/code/syrym95/p10-v2-n4
20:13:44 STOLE O2 p10-fleet-2 -> p10-fleet-5
20:17:00 STOLE EI p10-fleet-2 -> p10-fleet-6
20:19:28 STOLE WU p10-fleet-4 -> p10-fleet-5
20:20:20 STOLE UU p10-fleet-5 -> p10-fleet-2
20:20:23 STOLE PL p10-seismic -> p10-fleet-6
20:20:23 STOLE HL p10-fleet-2 -> p10-seismic
20:20:23 STOLE FN p10-seismic -> p10-fleet-3
20:20:23 STOLE UW p10-fleet-1 -> p10-fleet-4
20:20:23 STOLE SC p10-fleet-3 -> p10-seismic
20:15 TX laptop -> p10-fleet-3 (started 20:15:16)
Kaggle from the start: ET CU AE WW MB UO(moved from p10-seismic)
Colab (separate run): JP_EXT12 (laptop waiter cancelled 20:25)
ext12 runs started 20:22 UTC on the machine of their batch-A run after networks_ext12.json was copied to the VMs (first start at 20:21 failed: file missing, nothing ran)
```

## Marker deletion and the unplanned TX replicate (laptop)
- 08.11.2026 ~20:35 UTC (laptop, collection process): `rm -rf NE TX` in results/v2/runs. Both directories held only the DONE/MOVED skip
  markers of networks moved elsewhere (NE -> Kaggle, TX -> p10-fleet-3); no output, status or log. Record:
  results/v2/_markers_removed/DELETED_0811.txt. NE was re-filled by the Kaggle download (with DONE), so the laptop slot skipped it.
- Effect: the laptop slot (queue JP C0 TX NE) no longer saw TX/DONE and started TX again at 21:25:31 UTC after C0 ended. TX had already
  run on p10-fleet-3. Authors' decision 08.11: let it finish; it is an UNPLANNED REPLICATE, not scored. The scored TX is the
  p10-fleet-3 run. The laptop run is kept under results/v2/_replicate_TX_laptop/ and compared in results/v2/REPLICATE_TX.md
  (cross-platform reproducibility: same code, parameters and period on a VM and on the laptop).
- From then on collection never deletes or overwrites: collect.sh skips a network already present locally and can stage a VM into a
  separate directory (COLLECT_DEST); marker-only directories are moved to results/v2/_markers_removed/.

## p10-seismic disk full; RV re-run; CZ data error; hung chunks (08.11, authors' decisions)
- p10-seismic root disk (59 GB) was 100 % full (39 GB of earlier P10 work in ~/p10, 14 GB fleet waveform cache). RV crashed at
  ~21:07 UTC with "OSError: [Errno 28] No space left on device" in run_network.py (writing an attempt log); slots.log
  "END RV rc=0 state=running", no summary.json in either chunk. The disk was then resized to 120 GB (growpart + resize2fs;
  only apt cache and journald cleaned, no research file touched); the authors' note says 21:58 UTC, while the VM's slots.log
  shows the RV re-run (started after the resize, / = 118 GB) at 21:42:35Z, so the note's clock is not the VM clock.
- RV is re-run with the same frozen pipeline (compute failure, no method change): the crashed attempt was MOVED (not deleted) to
  results/v2/_failed_attempts/RV_diskfull/ on p10-seismic; new slot rRV started 2026-11-07T21:42:35Z (VM clock). If it has not
  finished by 00:00 UTC it is "not completed (compute)".
- CZ: "not completed - data error". Ended 20:18:45 UTC state "incomplete" after 4 attempts per chunk; ObsPy refused to merge
  CZ.ZVC..HHZ traces with differing sampling rates (100.0 vs 99.99999237060547 Hz). Not re-run; no station substituted.
- Hung at 21:36 UTC (process alive, no log output for > 80 min): p10-fleet-2 CN out_2024-04-08 (last day 2024-05-23), NM
  out_2024-01-08 (last day 2024-03-17), UU tuning week (empty run.log). Left running; whatever has no summary.json at 00:00 UTC is
  "not completed (compute: hung download)".

## Compute retries of hung runs on idle machines (authors' decision 08.11, written BEFORE the retries start)
- Retries, same frozen pipeline, parameters and own tuning week (no method change, nothing re-tuned by hand): UU -> fresh full run on
  p10-fleet-6; CN -> fresh full run on p10-fleet-1; NM -> fresh full run on p10-fleet-1. The fleet-2 originals keep running.
  Each retry writes only on its own VM (~/p10v2/results/v2/runs/<NET> there; those VMs never held these networks); collection stages
  them separately and never copies over the fleet-2 directories.
- Rule: for a network with a hung original run, the scored run is the first one that completes on any machine before 00:00 UTC;
  the other is kept as an unplanned replicate and compared with analysis/v2_replicate_compare.py. Neither finished by 00:00 UTC ->
  "not completed (compute: hung download)".
- Kaggle CPU retries under the same rule (authors' decision 08.11): RV, UU, CN, NM as kernels syrym95/p10-v2-<net>-r2, built by
  analysis/v2_fleet/make_kaggle.py --suffix r2 from the commit that adds this line; launch logged at 2026-11-07T21:58:48Z (laptop clock, UTC),
  before the kernels are pushed. Outputs are staged in results/v2/_staging_kaggle_r2/<NET>, never over an existing run directory.
  Whichever run of a network completes first before 00:00 UTC is scored; the rest are replicates.
- Colab UU retry, started 2026-11-07T22:00:17Z (bundle FLEET_COMMIT 2e211c1, pipeline unchanged; its tuning thresholds MAKZ 6.469,
  S1_1 7.643, S1_2 2.571, S2_1 8.573, S2_2 9.680, S3_1 7.869). It was started BEFORE it was logged here, so it is an UNPLANNED
  REPLICATE only and can never be the scored UU run, whatever its finish time. If it finishes it is staged in
  results/v2/_staging_colab_r2/UU and compared with analysis/v2_replicate_compare.py.
- p10-fleet-2: the hung download worker processes of CN, NM and UU were stopped at ~22:16 UTC by the authors' decision; the runner's own
  per-chunk retry restarted them (same frozen pipeline and thresholds), and their logs are fresh again. These fleet-2 runs stay
  under the first-to-complete rule above.
- First-to-complete decisions (rule above; completion = status.json "finished_utc" with state done; checked ~22:45 UTC):
  - NM: scored = Kaggle syrym95/p10-v2-nm-r2 (started 21:59:31Z, done 22:29:16Z), first to complete. fleet-1 NM and fleet-2 NM were
    still "running" at the check; whichever finishes later is a replicate.
  - UU: scored = Kaggle syrym95/p10-v2-uu-r2 (started 21:59:23Z, done 22:36:48Z), first to complete. Replicates: p10-fleet-6 rUU
    (started 21:56:37Z, done 22:38:24Z) in results/v2/_replicates/UU_fleet6; fleet-2 UU still "running" at the check; Colab UU
    (replicate only, see above). Kaggle vs fleet-6 (results/v2/replicate_UU.json): identical thresholds, the same 3583 episodes and
    278 associated, identical actions of every policy; only difference assoc_residual_s on 7 episodes by <= 4.8e-7 s.
  - CN and RV: no run complete at the check (fleet-1 CN, fleet-2 CN, Kaggle cn-r2, p10-seismic RV re-run, Kaggle rv-r2 running).
- Batch-B states from p10-fleet-5: AV, BW, ND, WU done; O2, S1, US tuning_failed (a role without data in the tuning week).
  - RV: scored = Kaggle syrym95/p10-v2-rv-r2 (started 21:59:17Z, done 22:47:42Z), first to complete; its tuning thresholds equal those
    of the crashed disk-full attempt to every digit. The p10-seismic RV re-run (started 21:42:35Z) was still "running" at that time and
    becomes a replicate.
- Found ~23:01 UTC (authors): on p10-seismic, SC/out_2024-01-08 and runs_ext12/OH/out_2024-07-08 logs end with "OSError: [Errno 28]
  No space left on device" (before the disk resize); these chunks are incomplete and are not scored as they are. The three US VMs
  show no download traffic; their logs hold 192 x HTTP 429 and 213 x HTTP 503: the data centre throttles the GCP addresses.
- Kaggle r2 retries (other egress), logged at 2026-11-08T02:16:54Z before the push, same frozen pipeline and first-to-complete rule: SC (batch B,
  own tuning week) and OH_EXT12 (frozen batch-A OH thresholds from results/v2/runs/OH/status.json, no re-tuning, as the ext12 plan).
  make_kaggle.py bundles networks_ext12.json and, for an *_EXT12 id, the batch-A status.json of that network (runner-only change).
  Whatever is not done at 00:00 UTC is "not completed (compute: disk-full chunk / data-centre throttling)".
- Correction (2026-11-08T02:18:16Z): the Kaggle r2 retries of SC and OH_EXT12 logged in commit e242991 were NOT launched (the collection process was
  interrupted before building them; no kernel p10-v2-sc-r2 or p10-v2-oh_ext12-r2 exists). The only runs of SC and OH_EXT12 are those on
  p10-seismic; their state at 00:00 UTC is read from the VM once it is reachable again.
- Kaggle syrym95/p10-v2-cn-r2: done, started 21:59:27Z, finished 23:17:36Z (staged in results/v2/_staging_kaggle_r2/CN). The CN
  first-to-complete decision waits for the finished_utc of the p10-fleet-1 CN retry (laptop gcloud credentials expired after the
  cutoff; the VMs could not be read).
- Status at the 00:00 UTC cutoff (authors' decision): SC r2 and OH_EXT12 r2 = logged but never launched before cutoff. SC (batch B)
  and OH_EXT12 (ext12) = "not completed (compute: disk-full chunk on p10-seismic + data-centre throttling of GCP addresses)"; their
  p10-seismic chunks are not scored. Remaining fleet-2 copies (CN, NM, UU) and the p10-seismic RV re-run = replicates.
- Final collection 2026-11-08 (after gcloud re-login): p10-seismic, p10-fleet-1, p10-fleet-2 collected per VM into results/v2/_staging_final/<vm>
  (an earlier mixed collection into one folder was moved to _markers_removed/_staging_final_mixed_0811, not used).
- CN first-to-complete decision: Kaggle cn-r2 finished 23:17:36Z, p10-fleet-1 CN 23:29:20Z, p10-fleet-2 CN 2026-11-08T01:26:13Z (after cutoff)
  -> scored CN = Kaggle cn-r2 (moved to results/v2/runs/CN); fleet-1 and fleet-2 CN are replicates. fleet-2 NM (00:22:58Z) and UU
  (01:33:52Z) finished after the cutoff and are replicates.
- CZ (batch B, p10-seismic): state "incomplete", both chunks without outputs after 4 attempts -> "not completed (compute)".
  Scorer change, run handling only: load_network returns "not completed" when any chunk lacks episodes.csv (it raised
  FileNotFoundError); no computation changed, no network partially scored.

## Rescue extension (PREREGISTRATION_V2_RESCUE_2026-11-08.md, pushed 89e7fa4 at 2026-11-08T06:54:47Z; post hoc)
- EarthScope's FDSN availability service answers "This service has been retired" (HTTP 404), so the plan's fallback applies to its
  networks: 5-min dataselect probes at 00:00 and 12:00 UTC (run in parallel, commit ed4e3ef; rule unchanged). GEOFON (AW),
  EPOS-France (FR) and AusPass (S1) answered the availability service.
- Window search (laptop, 07:00-07:03Z): no qualifying tuning window for AF (no role has data 2024-01-01..2024-03-31), C (S1_1 data
  on 2 days, S2_1 on 0) and EI (S1_1 EI.IGLA no data) -> these three stay excluded. Qualifying first windows: AB 2024-01-07,
  AW 01-11, CU 02-07, FR 01-28, KO 02-07, O2 01-08, PQ 03-15, S1 01-17, US 03-05, CZ 01-01 (the windows are re-derived inside each run).
- Machines: Kaggle CPU kernels syrym95/p10-v2-<net>-rescue for SC (07:01Z), AB, AW, CU, FR (07:03Z); Kaggle allows 5 batch CPU
  sessions at a time, so KO, O2, PQ, S1, US and CZ run on the laptop (obspy 1.5.1, P10_PLATFORM=laptop, from 07:06Z).
  No GCP VM is used by the rescue (the VMs serve the batch-B 12-month extension).
- ext12B (PREREGISTRATION_V2_EXT12_B_2026-11-08.md, plan e1693e4 pushed 2026-11-08T06:58:11Z before any ext12B data): 31 batch-B
  networks launched 2026-11-08T07:04:30Z on the 7 GCP VMs (deployed commit 7ee7f5c; p10-fleet-6 ed4e3ef, same runner), launcher
  analysis/v2_fleet/launch_ext12B.sh: slot xb_a = EarthScope networks spread over 7 IPs, slot xb_b = other data centres.
  p10-fleet-4 NM CN UU ET | NS EE; p10-fleet-5 RV C0 TX AE | HC HE; p10-fleet-6 QZ NY UW WW | ND FN; p10-seismic PL HL MB | SI;
  p10-fleet-1 IW PE AG | BW; p10-fleet-2 OK N4 CO; p10-fleet-3 NE UO. Kaggle kernels left to the parallel rescue run.
  Reviewed-bulletin labels for 2024-07..2025-01 downloaded 2026-11-08 ~07:05 UTC (results/v2_reviewed_ext12B/labels, 378 files,
  SHA256.txt committed, raw files not committed).
- ext12B restart (2026-11-08): the 07:04Z launch failed in 0 s on every VM. Cause: commit 12c0399 had edited a header comment of the
  frozen pipeline/extended_stalta_criteria.py, so the wrapper's sha256 check refused to run (fixed upstream in 7a9b5ff); in addition,
  `git archive` on the Windows laptop ships CRLF files, so the deployed sha was b92c7c12. The failed run trees were moved (not
  deleted) to ~/p10v2/results/v2/_failed_attempts/ext12B_sha_mismatch_0708Z on each VM; CR was stripped on the VMs and the deployed
  pipeline sha256 verified = frozen 4c8c9a71 on all 7; relaunched 2026-11-08T07:13:13Z with the same assignment. No parameter changed.
- 07:05Z incident: the repository cleanup commit 12c0399 had edited a header comment of the frozen pipeline files, so the
  frozen-pipeline sha256 check stopped every run ("pipeline sha256 fbc8762b... differs from the frozen 4c8c9a71..."). No run
  produced output with the edited file. The files were restored byte-identical from 117e163 (commit 7a9b5ff, sha256 4c8c9a71...
  verified); the first laptop attempts were moved to results/v2/_rescue_aborted_sha/ and restarted at 07:07Z; Kaggle version 1
  of SC, AB, AW, CU, FR (built at ed4e3ef with the edited file) ended without output and version 2 (commit 2fd8b9a, embedded
  pipeline sha256 4c8c9a71... checked) was pushed at 07:21-07:22Z, all RUNNING at 07:22Z.
- The day probes are live requests, so the qualifying windows found inside each run can differ from the 07:00Z search (PQ:
  02-17 inside the run vs 03-15 at 07:00Z); the window recorded in each run's status.json is the one used and scored.
- O2: the first window inside the run (2024-01-01) gave a non-finite threshold; the next qualifying window was used (rule 2.1).
- Raw-waveform retention (authors' decision 2026-11-08 ~07:45 UTC): all raw miniSEED is kept. slot.sh deletes each network's cache when the
  network ends, so a keeper loop (~/keep_raw.sh, every 20 s) hard-links ~/p10v2cache into ~/p10raw on every VM; nothing downloaded
  is lost and nothing is downloaded twice. Bucket gs://p10-raw-waveforms (project the authors' Google Cloud project, us-central1, Standard) was
  created. The VMs have read-only storage scope; changing it needs a VM stop, so the upload to gs://p10-raw-waveforms/<NET>/<STA>/
  <YYYY-MM-DD>.mseed (with a gsutil size check before any local file is removed) is done after the ext12B runs, before the final stop.
- Data source: the 8 non-EarthScope networks already use their home data centres (GEOFON EE HE FN, INGV SI, LMU BW, UIB-NORSAR NS,
  NOA HC, EPOSFR ND). The other networks keep the data centre of their batch-B run, so the ext period is drawn from the same source as
  the batch-B period; no source was changed (no throttling observed at launch).
- ext12B slot b (non-EarthScope networks NS EE, HC HE, ND FN, SI, BW) did not start at the 07:13Z launch (the second background
  command of the combined ssh line was not detached); started separately 2026-11-08T07:32Z. Launcher fixed (subshell-detached).
- ext12B NM (data fact, not a deviation): chunk 2024-10-08..2025-01-08 fails deterministically (KeyError 't_on' = no episodes)
  because NM.BLO (reference), NM.OLIL and NM.USIN have station epochs that end 2024-09-18/19 (EarthScope station service) and
  every Q4 day was returned empty; only S3_1 (NM.SIUC) has data. Chunk 2024-07-08..10-08 finished. Network state "incomplete";
  handled by the pre-registered exclusion "no reference data" at scoring, nothing re-run or changed.
- CZ: the first laptop attempt after the restart (07:07Z) stopped at the merge with «differing data types (int32, float64)»: the
  resampled trace came back as float. The rescue wrapper now rounds it back to the channel's integer type (commit 0eed448; the
  rate fix itself and the frozen pipeline unchanged); attempt moved to results/v2/_rescue_aborted_dtype/CZ. The laptop rerun
  (07:29Z) hung for 28 min in the day-probe step (sockets to EarthScope stuck in CLOSE_WAIT) and was stopped (moved to
  results/v2/_rescue_aborted_hang/CZ_laptop_0729); CZ runs on Kaggle p10-v2-cz-rescue (commit 62f2b94) from 07:58Z.
- Finished on Kaggle: CU 07:21-07:45Z, AW 07:21-07:50Z, AB 07:21-07:54Z (each first window, rescue_window_try 1); outputs
  copied unchanged from results/v2/_staging_kaggle_rescue/<net>/out/<NET> into results/v2/runs_rescue/<NET>.
- ext12B DEVIATION (authors' decision, logged 2026-11-08T08:17Z, before the cutoff): the compute cutoff of prereg section 7
  (08.11.2026 23:00 Almaty) is moved EARLIER to 08.11.2026 17:00 Almaty (12:00Z). At 12:00Z the slots are stopped; only networks
  whose both quarterly chunks finished are collected and scored (catalogue + reviewed labels) and reported as a sensitivity check
  "N of 31 networks extended to 12 months"; every other network is reported "not completed (compute)". No threshold, rule or code
  change. Raw waveforms already on the VMs (~/p10raw) and derived results are archived to gs://p10-raw-waveforms (NEARLINE,
  size-verified); all VMs are then stopped (never deleted). A VM that finishes all its networks earlier is stopped (or its EU
  slots handed to batch C on request).
- ext12B DEVIATION (authors' decision, logged 2026-11-08T08:30Z): the 12:00Z cutoff is replaced by an immediate cutoff at
  the time of this entry. Slots are killed now; only networks with both quarterly chunks finished are collected and scored
  (catalogue + reviewed labels) as a sensitivity check; all others are "not completed (compute)". No new downloads, no code,
  threshold or rule change. All 7 VMs are stopped (never deleted).
- ext12B at cutoff (08.11 ~08:31Z): both chunks finished in 12 of 31 networks (BW CN FN IW ND NE OK PE PL QZ RV UO); NM and HL had a
  chunk without outputs; 17 not completed (NS UU HC C0 NY SI MB N4 EE HE TX UW ET AE WW AG CO). PE: both chunks rc=0 (08:18Z, 08:24Z)
  before the cutoff but its status flag was still "running" when the slot was killed; set to "done" by the cutoff step (noted in
  its status.json). Machines: fleet-4 NM CN (+NS UU unfinished), fleet-5 RV (+HC C0), fleet-6 QZ ND FN (+NY), p10-seismic PL HL
  (+SI MB), fleet-1 IW BW PE, fleet-2 OK (+N4), fleet-3 NE UO. Derived results archived to gs://p10-raw-waveforms/_derived/ext12B
  (635 objects, counts match the local copy). Raw waveforms (~129 GB in ~/p10raw on the 7 VMs) were NOT uploaded: the VM service
  account has read-only storage scope and no bucket IAM; they stay on the stopped VM disks. All 7 VMs stopped (TERMINATED), none deleted.
- Rescue, remaining runs. Laptop: KO 07:07-08:37Z, PQ 07:07-08:26Z, US 07:07-08:18Z (done; US has 25 associated episodes, below
  inclusion). Kaggle: FR 07:21-08:02Z, SC 07:21-08:03Z, CZ 07:58-08:32Z (rate_fix resampled 6 traces); outputs copied unchanged
  from results/v2/_staging_kaggle_rescue/<net>/out/<NET>. O2: non-finite thresholds in all three windows (rescue_failed_thresholds).
  AF, C, EI: no qualifying window (rescue_failed_no_window).
- S1: left INCOMPLETE (decision 08.11, not rerun). Chunk 2024-04-24..2024-07-08 attempt 1 ended with a catalogue failure: the USGS
  regional catalogue has no event for that period within 15 deg of S1.AUDCS at M >= 2 (checked directly: geojson 0 events, quakeml
  HTTP 204), so every pre-specified retry would fail the same way; retries were stopped at 08:48Z and status.json set to incomplete.
- Scoring (analysis/v2_rescue_score.py, 08:5xZ): 8 rescued networks pass inclusion in both endpoints (AB AW CU FR KO PQ CZ SC);
  results/v2_rescue/v2_eval_rescue.json, v2_rescue_table.md.
