# Analysis plan: regional reference labels from the Kazakhstan National Data Centre (NNC / KNDC)

Committed before the NNC event list was downloaded. Author: Syrym Zhakypbekov. Date: 2026-11-07.

**Source.** ISC FDSN event service, contributor=NNC, within 6° of IU.MAKZ, 2025-01-01 to 2026-02-28 (NNC data in ISC end on 2026-02-28). Event type as given by NNC: "earthquake" or "mining explosion" (agency judgement, not ground truth; ISC solutions after 2024-11-01 unreviewed).

**Episodes.** The extended-test episodes of IU.MAKZ (PREREGISTRATION_EXTENDED.md) in the same window, with the frozen decision parameters of that pre-registration. No parameter is changed.

**Association.** Predicted first P arrival at IU.MAKZ (TauP iasp91) within [t_on − 15 s, t_off], the rule of the main analysis.

**Reported (descriptive, exploratory relative to the pre-registration):**
1. Number of episodes associated with an NNC earthquake, an NNC mining explosion, or neither.
2. For each policy: share of NNC-earthquake episodes dismissed; share of NNC-explosion episodes dismissed; number of automatic alerts with no ISC, USGS or NNC event.
3. The same CG − P3 difference in dismissed share as E3, computed with NNC earthquakes as the reference.

No hypothesis is tested; the purpose is to see whether the conclusions depend on the global catalogue.
