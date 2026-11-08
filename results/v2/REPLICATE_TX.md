# TX: unplanned replicate (VM vs laptop) — cross-platform reproducibility

**Unplanned.** It exists only because the laptop's TX skip marker was deleted by mistake during collection (results/v2/FLEET_DEVIATIONS.md,
section "Marker deletion and the unplanned TX replicate"; results/v2/_markers_removed/DELETED_0811.txt). The laptop slot then ran TX a
second time. Authors' decision 08.11: the scored TX run is the p10-fleet-3 run; the laptop run is a replicate, never scored.

| | scored run | replicate |
|---|---|---|
| directory | results/v2/runs/TX | results/v2/_replicate_TX_laptop/TX |
| machine | p10-fleet-3 (GCP e2-standard-4, Linux, /opt/p10 Python 3.11) | laptop "prime" (Windows 11, conda env admission) |
| state | done | done (laptop slot 21:25:31Z .. 22:21:41Z) |

Same frozen pipeline (pipeline/extended_stalta_criteria.py), same parameters, same tuning week 2024-01-01..2024-01-08 (each run tuned
independently), same evaluation period 2024-01-08..2024-07-08, data downloaded independently by each machine from EarthScope.

## Result (analysis/v2_replicate_compare.py → results/v2/replicate_TX.json)
- Thresholds: equal up to floating point; largest absolute difference 1.6e-12 (e.g. MAKZ 7.1801345622988695 vs 7.180134562298733).
- Episodes: 2014 in both; every episode matched on (t_on, t_off); 0 only in one run. Associated: 35 in both.
- Every non-float column identical on all matched episodes (neighbour states YES/NO/MISSING, coverage, associated event, association
  kind). Largest float differences: peak_cft 1.7e-11, snr_db 1.9e-11; assoc_residual_s 0.
- Catalogue: same rows (896 and 775 per chunk), all fields identical except dist_deg (largest difference 2.8e-14 degrees).
- Availability: identical after normalising line endings (the laptop writes CRLF).
- Actions of every policy (P1, P1t, P2, P3, P3 8.0 dB, CG, CG-D, CG c05) identical: same counts of alert / dismiss / escalate and the
  same dismissed associated episodes.
- Files are not byte-identical: line endings (Windows) and the last digits of floating-point values (different platform, numeric
  libraries). These differences change no state, no association and no action.

Conclusion: on TX, the frozen pipeline gives the same decisions on a Linux cloud VM and on the Windows laptop. This holds for one
network; it is reported as a reproducibility check, not as a hypothesis test.
