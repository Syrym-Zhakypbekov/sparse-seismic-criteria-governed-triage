# PROGRESS — time-disjoint test 2023 (PLAN_TIME_DISJOINT_2023_2026-11-08.md)

Append-only log, UTC.

- 2026-11-08T11:22:25Z plan written; disjointness verified (results/tdh2023/disjoint_check.json, all_disjoint=true); about to commit+push the plan before any 2023 data.
- 2026-11-08T11:23:02Z plan commit 1bb05f3 pushed (GitHub activity API timestamp 11:23:02Z). No 2023 waveform/event/label requested before this.
- 2026-11-08T11:25Z the storage write scope was not added to the fleet VMs; VMs keep read-only bucket scope. Plan: raw download on the laptop (only machine with bucket write) -> bucket; VMs compute from the bucket (read-only is enough).
- 2026-11-08T11:25:21Z the authors turned all Google VMs off (~16:30 Almaty); do not start p10-seismic or p10-fleet-*. No VM was started by this run (the scope change was denied before any start). Compute = laptop + Kaggle only.
- 2026-11-08T11:26:57Z candidates (metadata only, analysis/tdh2023/select_candidates.py): A2 included (2023 configuration ref A2.KCHK.00.HHZ, differs from W3); CA not included (no configuration passes sections 4-5 in the 2023 window); OT not included (3 eligible stations). Run list results/tdh2023/networks_tdh2023.json = 33 + A2.
- 2026-11-08T11:27:24Z FIRST WAVEFORM REQUEST (download pass 1 start; 14,428 role-day jobs, 34 networks; laptop). Pass 1 stopped at ~11:29Z after 118 files (~12 MB/s, day-major order); restarted with one pool per data centre, network-major order (EarthScope 14 parallel, others 3) so networks finish one by one. Files already downloaded are kept and not requested again.
