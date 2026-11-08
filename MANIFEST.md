# Manifest: table, figure or section of the paper → script → result file

Numbering follows the manuscript version submitted to *Sensors* (v35, 8 November 2026). Run every script from the repository
root with the environment in `requirements.txt`. "Post hoc" marks analyses added after an earlier result; the paper labels them
the same way. Scripts not listed here produced intermediate files or earlier versions of an analysis and are kept for the record.

## Main text

| Item | Script | Result file |
|---|---|---|
| Table 1, Table A1 (stations, detection and evidence parameters) | pipeline/extended_stalta_criteria.py (parameters in its header) | results/*/summary.json |
| Tables 2, 3 (criteria, weights, policies; specification) | analysis/criteria_governed_model.py, analysis/extended_eval.py, analysis/posthoc_extended.py | — |
| Section 4.1 (detector coverage of catalogued events) | analysis/detector_coverage.py | results/stage1_v3/detector_coverage.json |
| Tables 4, 5 (development period, contiguous-block CV, paired bootstrap) | analysis/cg_evaluation.py | results/criteria_governed/cg_evaluation.json |
| Remarks 1–2 numerical checks, development ledger | analysis/criteria_governed_model.py | results/criteria_governed/dm_ledger_dev.csv, dm_summary.json |
| Section 4.3 (held-out period, five policies, 37 calendar days) | analysis/heldout_table6.py | results/heldout/table6.json |
| Table 6, E1–E4 (extended test, IU.MAKZ) | analysis/extended_eval.py | results/extended/extended_eval.json |
| Section 4.4 calendar-preserving block bootstrap, ledgers with folds | analysis/r5_analyses.py | results/r5/r5_analyses.json, results/r5/ledger_*.csv* |
| Section 4.5 II.KURK development run (exploratory) | analysis/ref_kurk.py | results/extended/ref_KURK/ |
| Table 7, K1–K4 (II.KURK extended test) | analysis/kurk_extended.py | results/kurk_ext/kurk_ext_eval.json, results/chunk_boundary_check.json |
| Table 8, D1–D4 (CG-D, 2024) | analysis/cgd_2024.py | results/y2024/cgd_2024_eval.json |
| Table 9 (constant c, 2024; post hoc) | analysis/discount_sweep.py | results/y2024/discount_sweep.json |
| Table 10 (discounting on the failed periods; post hoc) | analysis/posthoc_extended.py | results/posthoc/extended_discount.json |
| Section 4.7 mechanism paragraph (post hoc) | analysis/mechanism_extended.py | results/posthoc/mechanism_extended.json |
| Table 11, N1–N5 (KZ network) | analysis/kz_network.py | results/kz/kz_eval.json |
| Section 4.8 StationXML comparison | analysis/station_metadata.py, analysis/station_metadata_ak.py | results/metadata/station_comparison.json, results/metadata/ak_station_comparison.json |
| Table 12, R1–R6 (AK network, Alaska) | analysis/ak_network.py | results/ak/ak_eval.json |
| Table 13 (batch-A networks, selection from metadata) | analysis/v2_select_networks.py, analysis/v2_finalize_networks.py | results/v2/networks.json, results/v2/selection/ |
| Table 14 (multi-network test, catalogue labels) | analysis/v2_networks.py (modes A, B, AB, EXT, AEXT), analysis/v2_report_tables.py | results/v2/v2_eval_batchA.json, v2_eval_batchB.json, v2_eval_AB.json, results/posthoc/v2_report_tables.json |
| Table 15 (12-month extension of batch B) | analysis/v2_networks.py | results/v2/v2_eval_ext12B.json, results/v2/v2_eval_B_ext12B.json |
| Table 16 (rescued networks) | analysis/v2_rescue_score.py (download, score) | results/v2_rescue/v2_eval_rescue.json, v2_rescue_table.md |
| Table 17, G1–G4 (Alaska analyst-confirmed and analyst-deleted events) | analysis/ground_truth_v2.py (download, score) | results/ground_truth/ground_truth_eval.json |
| Table 18 (33 networks against analyst-reviewed bulletins) | analysis/v2_reviewed_bulletin.py (download, score) | results/v2_reviewed/v2_eval_reviewed.json, v2_reviewed_table.md |
| Table 19 (actions over the 33 networks, chance-expected dismissals) | analysis/workload_33net.py, analysis/calendar_bootstrap.py | results/posthoc/workload_33net.json, results/posthoc/chance_by_policy.json |
| Section 4.12 calendar-dependence bootstrap (post hoc) | analysis/calendar_bootstrap.py | results/posthoc/calendar_bootstrap.json |
| Table 20 (Kazakhstan runs against ISC-reviewed events) | analysis/kz_reviewed_labels.py (download, score) | results/kz_analyst/kz_reviewed_eval.json, kz_reviewed_table.md |
| Section 4.13 (explosions; not exercised) | analysis/explosions_v2.py (selfcheck, download, score) | results/explosions/explosions_eval.json |
| Section 4.14 (learned baselines, LLM triage baseline, latency) | analysis/baselines_ml_llm.py | results/baselines_ml_llm/baselines_ml_llm.json, results/baselines_ml_llm/llm/calls.jsonl |
| Table 21 (context-dependent reliability c_j(x)) | analysis/context_c.py | results/context_c/context_c.json |
| Section 4.15 recalibration (post hoc) | analysis/context_c_recal.py | results/context_c/recal.json |
| Table 22 (regions; post hoc) | analysis/posthoc_regions.py | results/posthoc/regions.json |
| Section 4.16 analyst workload (post hoc) | analysis/posthoc_workload.py | results/posthoc/workload.json |
| Section 4.16 training-chosen two-threshold rule, δ sweep (post hoc) | analysis/review4.py | results/review4/ |
| Section 4.16 controlled loss of neighbour evidence | analysis/sufficiency_stress.py | results/sufficiency/stress.json |

## Appendices

| Item | Script | Result file |
|---|---|---|
| Table A2 (equivalent SNR thresholds per neighbour-state pattern) | analysis/threshold_table.py | results/posthoc/threshold_table.json, threshold_table.md |
| Table B1 (ablation), binary SNR, controlled station loss, shift control | analysis/r3_analyses.py, analysis/r4_analyses.py | results/r3/, results/r4/ |
| Table B2 (one threshold procedure for every baseline; post hoc) | analysis/same_procedure_baselines.py | results/posthoc/same_procedure_baselines.json |
| Table B3 (further post hoc analyses) | analysis/review_posthoc.py, analysis/assoc_actions.py, analysis/threshold_consistency.py | results/posthoc/review_posthoc.json, assoc_actions.json, threshold_consistency.json |
| Appendix B out-of-sample operating points (post hoc) | analysis/oos_operating_points.py | results/posthoc/oos_operating_points.json, .md |
| Appendix B block bootstrap, KZ constant c, KZ simultaneous gaps (post hoc) | analysis/r12_checks.py | results/posthoc/r12_checks.json |
| Appendix B AK block bootstrap, AK availability, AK StationXML (post hoc) | analysis/r16_checks.py | results/posthoc/r16_checks.json |
| Appendix B common caps on escalations | analysis/r5_analyses.py | results/r5/frontier_exact_best.csv |
| Appendix C (NNC regional labels, provenance) | analysis/nnc_reference.py, analysis/nnc_provenance.py | results/nnc/ |
| Tables D1–D3 (every scored network) | analysis/v2_report_tables.py | results/posthoc/v2_report_tables.json, v2_report_tables.md |
| Table D4 (rescued networks) | analysis/v2_rescue_score.py | results/v2_rescue/v2_eval_rescue.json, v2_rescue_table.md |
| Appendix E (overlap, chance correction, margin, leave-one-out; post hoc) | analysis/gap_reviewed.py | results/gap/gap_reviewed.json |
| Appendix F (weights and thresholds sensitivity, ablation of the sufficiency condition; post hoc) | analysis/sens_weights.py | results/sensitivity/sens_weights.json, ablations.json |
| Table G1 (detection-probability likelihood baseline; post hoc) | analysis/detprob_baseline.py | results/detprob/detprob.json |
| Appendix H (forward re-tuning, low-chance subset, G.WUS removed; post hoc) | analysis/gap2.py | results/gap2/forward_retune.json, low_chance.json, wus_removed.json |
| Table I1 and Appendix I (learned baselines with a reject band, calendar bootstrap, Holm, margin cost, undefined SNR; post hoc) | analysis/review2.py | results/review2/ |
| Appendix J (Schorlemmer-style detection probability, cost-optimal thresholds, Draelos-style screen; post hoc) | analysis/review3.py | results/review3/ |
| Tables K1–K3 (evidence-sufficiency stress test; post hoc) | analysis/sufficiency_stress.py, analysis/sufficiency_tables.py | results/sufficiency/stress.json, thin_subset.json, tables_K.md |
| Section 3.6 pre-specification chronology | analysis/prespec_timeline.py | results/provenance/prespecification_timeline.json |

## Figures

| Figure | Script | File |
|---|---|---|
| Figures 1–3 | analysis/figures.py | figures/fig1_availability.png, fig2_policies.png, fig3_outage_event.png |
| Figure 4 | analysis/context_c.py (written as results/context_c/calibration_T1.png; copied) | figures/fig4_context_c_calibration.png |
| Figure 5 | analysis/posthoc_regions.py | figures/fig5_regions.png |
| Figure 6 | analysis/fig6_twothreshold.py | figures/fig6_workload.png |
| Appendix E, F figures | analysis/gap_reviewed.py, analysis/sens_weights.py | figures/fig_gap_overlap_loo.png, fig_sens_weights.png |
| README animations | analysis/make_readme_gifs.py, analysis/gifs.py, analysis/gifs_v21.py | figures/gif/, figures/gif_*.gif |

## Detector runs (secondary analyses)

| Item | Script | Result file |
|---|---|---|
| EQTransformer and PhaseNet on the development episodes | pipeline/eqtransformer/, pipeline/phasenet_laptop.py | results/eqt/, results/phasenet/ (environment: docs/DETECTOR_ENVIRONMENT.md) |
| EQTransformer on the extended episodes, CPU repeat | pipeline/eqt_extended_colab.py, pipeline/eqt_vm.py, analysis/eqt_cpu_gpu_check.py | results/eqt_extended/, results/eqt_vm_cpu/ |
| Learned criterion CG-L (not in the paper) | analysis/cgl_extended.py | results/eqt_extended/cgl_eval.json |
| Blast and earthquake features (exploratory; not in the paper) | pipeline/blast_features.py, analysis/blast_eval.py | results/blast/ |
