# Protocol deviation, explosion test (PREREGISTRATION_EXPLOSIONS_2026-11-08.md, pushed 0b4eb6e)

First scoring run (08.11.2026, 00:17-00:55 Almaty) matched 0 of 17,126 AK episodes to any ComCat label, including
41,420 earthquakes, although the AK run itself has 2,034 catalogue-associated episodes. Cause: an implementation error in
analysis/explosions_v2.py, labels(): label origin times were converted with `astype("int64") / 1e9`, which assumes
nanoseconds, while pandas 3.1.1 parses these strings to microseconds; every label time was therefore about 1.7e3 s after
1970 and no window could contain it. The output of that run is kept unchanged in results/explosions/first_run_unit_error/.

Fix: unit-free conversion `(ts - 1970-01-01 UTC).dt.total_seconds()` plus a self-check that the converted times equal
ObsPy UTCDateTime to 1 ms (the script stops otherwise). Nothing else is changed: type lists, radius, period, matching
window, policies, hypotheses, margins, exercise rule and chance control are as pushed in 0b4eb6e. What was seen before the
fix: the label counts by class and type and the explosion magnitude quantiles (no episode-level result, no action share).
The same expression appears in analysis/ground_truth_v2.py (another test; not modified here).
