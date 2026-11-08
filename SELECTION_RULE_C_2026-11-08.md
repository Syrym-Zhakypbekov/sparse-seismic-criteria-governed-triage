# Network selection rule for batch C of the multi-network test of rule v2 (written and pushed before it was applied)

Author: Syrym Zhakypbekov. Written 08.11.2026, about 13:20 Almaty (08:20 UTC), before any batch-C candidate list was computed.
The rule is implemented by analysis/v2_select_networks_c.py, pushed in the same commit. Only metadata is read, as in
SELECTION_RULE_V2_2026-11-08.md: the station listings archived by the rule-v2 run of 07.11.2026 (results/v2/selection/raw/,
sha256 in raw_sha256.json) and daily availability metadata (archived responses re-used; missing ones requested from the same
services and archived in results/v2/selection_c/raw/). No event catalogue, no waveform and no detection is requested before
PREREGISTRATION_V2_BATCHC_2026-11-08.md is pushed.

## Why batch C
Batch A+B used all 54 networks that passed rule v2 in windows W1/W2. Of the 33 networks scored against reviewed labels, 15 are
in the USA-Mexico region. Batch C adds networks from regions outside North America, so that the pooled result rests less on
one region. The reason is region coverage only. Results of batch A/B are known (they are reported in the manuscript); batch C
is therefore a disclosed post hoc extension of the sample, selected by metadata only, with the decision rule, parameters and
hypotheses frozen before any batch-C waveform is requested.

## Differences from SELECTION_RULE_V2 (everything else is identical)
1. **Window.** One window only: tuning 2024-01-01 .. 01-08, evaluation 2024-01-08 .. 2024-07-08 (182 days), the period run
   for batches A and B. Channel epochs must cover 2024-01-01 .. 2024-07-08. Availability shares are taken over the 182
   evaluation days: reliable reference = share >= 0.90 on >= 90 % of the 182 days; every neighbour stream has share > 0 on at
   least 50 % of the days.
2. **No outage-history requirement.** The rule-v2 condition "at least one site has >= 3 days with share < 0.10" served the
   outage hypothesis only. Batch C does not test the outage hypothesis (R7/V-outage); the condition is dropped. It removed 512+
   configurations in the rule-v2 run, which is the main reason so few networks passed.
3. **Networks excluded:** the 54 networks of batches A and B, and IU, II, IM, G, KZ, AK (used elsewhere in the study); temporary
   codes (digit, X, Y, Z); RASPISHAKE (citizen stations); every network whose chosen reference lies in the USA-Mexico or
   Alaska-Aleutians-Canada macro-regions of rule v2 section 7.
4. **Regions (finer than rule v2, to spread countries).** First match in this order:
   Middle East-Caucasus-Turkey-Iran (lat 25-45, lon 26-63); Central Asia (lat 30-56, lon 45-100); Iberia (lat 35-44.5,
   lon -10 to 4); Scandinavia-Iceland-North Atlantic (lat 55-75, lon -45 to 32); Eastern Europe-Balkans (lat 34-56, lon 13-45);
   Western-Central Europe (lat 34-72, lon -25 to 45, not above); Africa (lat -40 to 37, lon -20 to 55); South-East Asia-East Asia
   (lat -11 to 56, lon 95-160); Oceania (rule-v2 New Zealand-SW Pacific box); South America (lat -60 to 13, lon -95 to -30);
   Central America-Caribbean (rule-v2 box); Antarctica (lat < -60); Other.
5. **Ranking within a region** (one configuration per network, as rule v2 section 6, keys in order): (1) the data centre is not
   EarthScope (EarthScope throttles per address, so other data centres download faster: a property of the service, not of the
   data); (2) a site with two members exists; (3) the reference's share of days >= 0.90; (4) station code.
   Regions are ordered by the key of their best network; regions in which none of the 33 reviewed-label networks of batches A/B
   lies come first (new regions first), then the others. Round-robin over regions until 15 networks are chosen.
6. **Size.** The configuration already limits a network to the reference plus 3-5 neighbour streams. The expected raw volume
   (about 0.45 GB per 100 Hz stream per 6 months, from the batch-A/B downloads) is recorded per network; nothing is excluded by
   size.

## Records
results/v2/selection_c/: candidates.json, rejections.csv, chosen.json, raw/ (newly requested responses) and raw_sha256.json.
The batch-C run list results/v2/networks_batchC.json is written in the networks_batchB.json format by the same script.
