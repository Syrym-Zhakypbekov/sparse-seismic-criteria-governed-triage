# Deviations from PREREGISTRATION_CONTEXT_C_2026-11-08.md (d25b86c)

D1 (2026-11-08, before the model was fitted and before any decision was scored). The second noise proxy `lrate`
(tuning-week trigger rate of the site relative to the reference) needs the tuning-week trigger counts. Most tune
run.log files of the v2 networks contain only the threshold line, not the run summary (summary present for 12 of 53
network folders; 2 of the 6 batch-A training networks lack it). `lrate` is therefore dropped for every set, training and
test alike. The noise proxy N_j is the tuning-week STA/LTA 99.9th-percentile threshold `thr` alone, read from the
`thresholds {...}` line that every tune run.log starts with. Nothing else changes.
