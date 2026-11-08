# Deviations, II.KURK extended test (PREREGISTRATION_KURK_EXTENDED.md)

- 2026-11-08, K4 (all neighbours missing -> escalated). The scorer recorded K4 as holding. Its only qualifying episode lies at a
  processing-chunk boundary: neighbour validity is looked up per processed day, so the seconds before the chunk start counted as
  missing although the neighbours had data on both days. The episode is therefore not a real all-missing case, and the manuscript
  reports K4 as not exercised, overriding the scorer record. A check of all runs found no other such episode
  (results/chunk_boundary_check.json). Decisions, thresholds and every other K verdict are unchanged.
