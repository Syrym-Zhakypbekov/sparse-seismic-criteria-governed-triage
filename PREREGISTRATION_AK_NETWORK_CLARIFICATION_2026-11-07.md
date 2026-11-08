# Clarification to PREREGISTRATION_AK_NETWORK.md (added 07.11.2026, after the results, at review R16)

The original plan above is kept unchanged as a historical record. This note corrects how its station-selection
sentence should be read; it changes no hypothesis, parameter or result.

- The plan says AK.L22K "has real multi-day outages" and was "empty on 40 probe days". The probes were one minute per day.
  The processed data (results/posthoc/r16_checks.json, B_daily_availability) show no full-day outage of AK.L22K in the
  evaluated period: 0 days below 10 % valid data, 164 of 540 days between 10 % and 90 %, longest run of days below 90 % = 18.
  The probes therefore indicated intermittent gaps, not multi-day outages, and hypothesis R1 was not exercised.
- The choice of AK.CUT / AK.L22K / AK.COLD / AK.E22K was purposive (reliable reference, a 20–60 km neighbour with probe gaps,
  far roles approximating the development geometry); it was not uniquely determined by the probe statistics.
- Chronology: plan commit 6825835 pushed 16:46:31 UTC (host activity record, results/provenance/ak_host_activity.json);
  launch time written by the run script 16:47:07 UTC (results/ak/outAK_tune/started_utc.txt, authors' machine clock);
  results commit 4c04855 pushed 17:36:41 UTC. No separate transfer record of the outputs was kept; the outputs were copied
  from the VM with gcloud scp on 07.11.2026 and are integrity-identified by the repository commit 4c04855.

## Addendum 08.11.2026 (review R17)
- Distance: the plan's "about 8 000 km away" overstates it. The great-circle distance between the reference stations IU.MAKZ
  (46.808, 81.977) and AK.CUT (62.4058, -150.2625), radius 6371 km, is 7019.6 km; IU.MAKZ to the other AK stations is about
  6478-6993 km.
- Catalogue: the plan and the scorer's docstring speak of "AK solutions in USGS ComCat" and a "reviewed regional catalogue".
  The retained catalogue columns record only the retrieval service (ISC or USGS), not the originating agency or review status,
  and the ISC review frontier is 1 November 2024 while the evaluation runs to 30 June 2025. The supported statement is: different
  stations, operator, instruments and region, queried through the same ISC and USGS event services. The scorer file is kept
  unchanged as pushed before the data.
- Evaluation period: 8 January 2024 - 30 June 2025 inclusive (540 days); 1 July 2025 is the exclusive end used by the run script.
