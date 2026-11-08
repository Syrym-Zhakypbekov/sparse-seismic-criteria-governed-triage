# Criteria-Governed Decision-Making in Sparse Seismic Networks

Code, test plans, decision ledgers and result files for the paper

> Zhakypbekov, S.; Bykov, A.; Shaikemelova, A.; Chinibayeva, T. Criteria-Governed Decision-Making in Sparse Seismic Networks:
> Evidence Sufficiency, Non-Confirmation Reliability, and Analyst Escalation. Submitted to *Sensors* (MDPI), 2026.

International Information Technology University, Almaty, Kazakhstan. Correspondence: s.zhakypbekov@iitu.edu.kz.

Test plans are registered on OSF: https://osf.io/y8qxz (DOI [10.17605/OSF.IO/Y8QXZ](https://doi.org/10.17605/OSF.IO/Y8QXZ)).

## What the study does

A sparse seismic network confirms an alarm at one station by checking its neighbours. A neighbour that recorded and did not
trigger and a neighbour that has no data are different evidence, but a fixed coincidence rule treats both as "no confirmation".
The criteria-governed rule (CG) encodes each neighbour site as YES, NO or MISSING, weights a NO by a reliability factor c,
requires a minimum amount of valid evidence (δ) before an automatic action, and passes alarms between two score thresholds to
an analyst. Each alarm ends as alert, dismiss or escalate.

The rule is compared with classic coincidence (P1, P1t), an SNR rule (P2) and an abstaining SNR rule (P3) on:

- two reference stations in Kazakhstan (IU.MAKZ, II.KURK) over 546 days, a 2024 test of the discounted variant, a second
  network at the same sites (KZ) and a network in Alaska (AK);
- 38 networks in eight regions, selected from FDSN station metadata by a rule fixed before any waveform was requested, scored
  against catalogue association and against analyst-reviewed bulletins (ISC Reviewed Bulletin, USGS ComCat reviewed events);
- analyst-confirmed and analyst-deleted events in Alaska, learned and language-model baselines, and post hoc stress tests.

The detector is a recursive STA/LTA trigger; labels associate alarms with bulletin events by predicted P arrival time.

## Repository layout

| Path | Contents |
|---|---|
| `pipeline/` | waveform download, STA/LTA detection, episodes, neighbour states, catalogue association |
| `analysis/` | scoring of every table, multi-network and reviewed-bulletin scoring, post hoc analyses, figures |
| `analysis/v2_fleet/` | per-network runner of the multi-network test (`run_network.py`, `run_rescue.py`) |
| `results/` | episode tables, run logs, evaluation JSON per test, post hoc outputs, StationXML, provenance |
| `figures/` | figures of the paper; `figures/gif/` animations of each experiment |
| `adjudication/blind_v1/` | blind waveform-adjudication package (prepared, not yet adjudicated) |
| `PREREGISTRATION_*.md`, `SELECTION_RULE_*.md`, `ANALYSIS_PLAN_NNC.md` | plans of the pre-specified tests |
| `PLAN_*.md` | plans of post hoc analyses, each written before the analysis was computed |
| `docs/` | detector environment, reference list |
| `MANIFEST.md` | every table, figure and section of the paper → script → result file |
| `scripts/fetch_labels.sh` | re-downloads the bulletin label files that are not redistributed here |

## Reproducing the results

Python 3.12. The scoring scripts read only files in `results/`; they do not download data.

```bash
git clone https://github.com/Syrym-Zhakypbekov/sparse-seismic-criteria-governed-triage
cd sparse-seismic-criteria-governed-triage
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Each command below rewrites one result file; compare it with the committed version (`git diff results/`).

```bash
python analysis/cg_evaluation.py           # Tables 4-5 (development period)
python analysis/heldout_table6.py          # Section 4.3 (held-out period)
python analysis/extended_eval.py           # Table 6, E1-E4
python analysis/kurk_extended.py           # Table 7, K1-K4
python analysis/cgd_2024.py                # Table 8, D1-D4
python analysis/discount_sweep.py          # Table 9 (post hoc)
python analysis/posthoc_extended.py        # Table 10 (post hoc)
python analysis/kz_network.py              # Table 11, N1-N5
python analysis/ak_network.py              # Table 12, R1-R6
python analysis/v2_networks.py AB          # Table 14 (also A, B, EXT, AEXT)
python analysis/v2_report_tables.py        # Tables D1-D3
python analysis/context_c.py               # Table 21, Figure 4
python analysis/posthoc_regions.py         # Table 22, Figure 5 (post hoc)
python analysis/sufficiency_stress.py && python analysis/sufficiency_tables.py   # Tables K1-K3 (post hoc)
python analysis/figures.py                 # Figures 1-3
```

Scripts that score against analyst-reviewed bulletins (Tables 16, 17, 18, 20 and Section 4.13) need the bulletin files first:

```bash
bash scripts/fetch_labels.sh               # ISC and USGS ComCat queries, a few hundred MB
python analysis/v2_reviewed_bulletin.py score
python analysis/ground_truth_v2.py score
python analysis/kz_reviewed_labels.py score
python analysis/v2_rescue_score.py score
python analysis/explosions_v2.py score
```

The SHA-256 of every label file used in the paper is stored next to its output (`results/*/labels/SHA256.txt`,
`results/*/labels/download_record.json`, `results/nnc/raw/manifest.json`). Bulletins are revised over time, so a new download
may differ from the stored hashes; the differences then show which events changed.

Re-running the pipeline itself (waveforms → episodes) is possible but slow. `pipeline/extended_stalta_criteria.py` requests
waveforms from the EarthScope FDSN service and catalogue events from ISC and USGS. The multi-network runs go through
`analysis/v2_fleet/run_network.py <NET>`, which reads the network's configuration from `results/v2/`, tunes the detector on
the week before the evaluation period and runs the frozen pipeline through `pipeline/p10_v2_datacentre_wrapper.py`. Each run
folder keeps its `run.log`, `summary.json` and a `transfer.txt` with the SHA-256 of every output file.

The learned and LLM baselines (`analysis/baselines_ml_llm.py`, Section 4.14) need scikit-learn. The LLM part sends episode
descriptions to a Gemini model on Google Cloud Vertex AI and needs a project (`GCP_PROJECT`) and `gcloud` credentials; the
responses used in the paper are stored in `results/baselines_ml_llm/llm/calls.jsonl`, so the scoring step runs without a call.
The EQTransformer and PhaseNet runs need SeisBench and PyTorch (`requirements-detectors.txt`, `docs/DETECTOR_ENVIRONMENT.md`).

## Pre-registration

Each pre-specified test has a plan file that was pushed to the development repository before the earliest output of the
test. The push times, read from the GitHub activity record, are in `results/provenance/prespecification_timeline.json`. The
reviewed-bulletin test (Table 18) and the prospective test are also registered on OSF (https://osf.io/y8qxz). Analyses added
after a result are labelled post hoc here, in `MANIFEST.md` and in the paper. Deviations from a plan are logged next to the
results (`results/v2/FLEET_DEVIATIONS.md`, `results/*/DEVIATIONS.md`).

## Data sources

| Source | Use | Reference |
|---|---|---|
| EarthScope FDSN dataselect and station services | waveforms, StationXML | https://service.earthscope.org/fdsnws/ |
| ISC Bulletin and ISC Reviewed Bulletin (FDSN event) | catalogue association, reviewed labels | https://doi.org/10.31905/D808B830 |
| USGS ANSS ComCat (FDSN event) | catalogue association, reviewed and deleted events | https://doi.org/10.5066/F7MS3QZH |
| NNC/KNDC events via the ISC event service | regional labels, Kazakhstan | Appendix C of the paper |

Seismic networks of the single-network tests:

- IU: Albuquerque Seismological Laboratory/USGS (1988), Global Seismograph Network (GSN – IRIS/USGS). https://doi.org/10.7914/SN/IU
- II: Scripps Institution of Oceanography (1986), Global Seismograph Network – IRIS/IDA. https://doi.org/10.7914/SN/II
- G: Institut de physique du globe de Paris and EOST (1982), GEOSCOPE. https://doi.org/10.18715/GEOSCOPE.G
- IM: International Miscellaneous Stations, Makanchi array. https://www.fdsn.org/networks/detail/IM/
- KZ: Institute of Geophysical Research (KNDC) (1994), Kazakhstan Network. https://doi.org/10.7914/SN/KZ
- AK: Alaska Earthquake Center, University of Alaska Fairbanks (1987), Alaska Geophysical Network. https://doi.org/10.7914/SN/AK

The networks of the multi-network test and their data centres are listed in `results/v2/NETWORK_CHECK.md` and
`results/v2/selection/datacentres.json`; each is described at https://www.fdsn.org/networks/. Waveform data are not
redistributed here and remain under the terms of their networks.

## Known limitations of this repository

- Raw waveforms are not included. Episode tables, availability tables and catalogue extracts produced by the pipeline are.
- Bulletin label files (ISC, USGS ComCat, teleseismic queries and the raw NNC QuakeML) are not included; `scripts/fetch_labels.sh`
  re-downloads them, and the stored hashes allow a comparison (see above).
- Plan files mention commit hashes of the development repository, which is not public. The push times of those commits are kept
  in `results/provenance/`. In the plan files, local file paths and internal review labels were replaced by neutral wording; no
  method, parameter or decision rule was changed. `analysis/r16_checks.py` reads the activity record of the development
  repository and cannot be re-run against this one.
- The first comment line of `pipeline/extended_stalta_criteria.py`, `pipeline/stage1_pipeline.py` and
  `pipeline/heldout/p10_heldout.py` was edited for this release. The frozen pipeline was checked at run time by SHA-256
  4c8c9a715bdfc94c7790ac0793f85360ae6a75489ca197acc2aad92483168284 (LF line endings). The copy here has SHA-256
  1dca53557217715edeb61dc9beb95ebf55467bfeea80dbf169ea14c336d82193; without its first line both versions hash to
  b7698235f9aee24205c4aea5c2236304dd2c834bd9e423ad0f4406fe2a83aa85. The wrappers check the new value.
- Figure 4 is a copy of `results/context_c/calibration_T1.png` written by `analysis/context_c.py`; no separate script copies it.
- Orchestration scripts for the cloud machines that ran the multi-network test are not included; the per-network runner and the
  run logs are. Raw run logs are kept verbatim and contain machine paths.
- The time-disjoint test of June–August 2023 (`PLAN_TIME_DISJOINT_2023_2026-11-08.md`) is registered but has no result.
- The blind waveform adjudication (`adjudication/blind_v1/`) is prepared but has not been done; the answer key is not here.

## Licence

Code: MIT (`LICENSE`). Results, tables and figures in `results/` and `figures/`: CC BY 4.0 (`LICENSE-results.md`).

## Citation

See `CITATION.cff`. Until the paper is published, please cite this repository and the OSF registration
(DOI 10.17605/OSF.IO/Y8QXZ).
