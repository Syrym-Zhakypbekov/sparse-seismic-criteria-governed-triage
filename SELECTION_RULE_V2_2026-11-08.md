# Network selection rule for the multi-network confirmatory test of rule v2 (written and pushed before it was applied)

Author: Syrym Zhakypbekov. Written 07.11.2026 late evening Almaty time (08.11 by the plan's date), before any candidate list was
computed. The rule is implemented by analysis/v2_select_networks.py, pushed in the same commit. Only metadata is read: FDSN
station metadata (epochs, coordinates, channel codes, restriction status) and daily availability metadata (fdsnws-availability
where the data centre offers it, otherwise the EarthScope MUSTANG `percent_availability` quality metric). No event catalogue, no
waveform (not even a one-minute probe, unlike the AK plan), no detection is requested before the pre-registration is pushed.

## 1. Data centres
All entries of the FDSN data-centre registry (https://www.fdsn.org/ws/datacenters/1/query, read when the script runs, response
archived) whose repository offers both fdsnws-station-1 and an anonymous fdsnws-dataselect-1 (a dataselect URL containing
`auth` is excluded). Data centres that fail to answer the station request after 3 attempts are recorded with the error and
contribute no candidates. Data centres added by name to the candidate list from outside the registry are treated the same way.

## 2. Window (fixed per network by rule, never by results)
Three candidate windows, each a tuning week followed by 366 evaluation days:
W1 tuning 2023-07-01 .. 07-08, evaluation 2023-07-08 .. 2024-07-08; W2 tuning 2024-01-01 .. 01-08, evaluation 2024-01-08 ..
2025-01-08; W3 tuning 2024-07-01 .. 07-08, evaluation 2024-07-08 .. 2025-07-09. A network gets the EARLIEST window in which it
has a configuration passing sections 3-5 (earlier = deeper inside the ISC reviewed-bulletin period). Channel epochs must cover
the whole chosen window (tuning week included).

## 3. Eligible networks and channels
- Network codes never used in the study are eligible; excluded: IU, II, IM, G, KZ, AK. Temporary network codes (first
  character a digit or X, Y, Z) are excluded.
- Eligible stream: vertical broadband channel BHZ or HHZ (BHZ preferred when both exist; then the lexically smallest location
  code), whose channel epoch covers the whole chosen window (section 2).
- A network is read from the first data centre in registry order that (a) lists it with eligible streams and (b) offers daily
  availability metadata for it (fdsnws-availability of that data centre, or MUSTANG if the data centre is EarthScope).
- Networks whose network-level restrictedStatus is "closed" are excluded; for "partial", the selected streams are checked at
  channel level and any closed stream excludes the configuration.

## 4. Geometry of one configuration (reference + neighbour sites)
For each eligible station R of a network (candidate reference), distances are great-circle on a sphere of radius 6371 km:
- R must have no other eligible station of its network within 20 km (no reference inside a dense cluster).
- Neighbour candidates: eligible stations of the same network at 20-700 km from R, sorted by distance.
- Sites (rule v2 grouping, D = 50 km): walking the sorted list, a station joins the first existing site whose seed is within
  50 km of it; otherwise it becomes the seed of a new site. Site distance = seed distance. Only the three nearest sites are
  kept; each keeps at most its two members nearest to R; if the three sites together hold six stations, the farthest site keeps
  only its nearest member (3-5 neighbour stations in total).
- Required: exactly three sites, third-site distance >= 100 km and <= 700 km.

## 5. Availability (metadata only)
Daily availability share of each stream for each evaluation day of the window (fdsnws-availability time spans, or MUSTANG percent_availability
/ 100). A site's daily share = the largest share among its members.
- Reliable reference: share >= 0.90 on >= 90 % of the 366 evaluation days.
- Outage history: at least one of the three sites has >= 3 days with share < 0.10.
- Every neighbour stream has share > 0 on at least 50 % of the days (not a dead station).
Configurations failing these are rejected with the reason recorded.

## 6. One configuration per network
Among the passing configurations of a network, take the one ranked first by: (1) a site with two members exists (rule v2
exercised), (2) outage days (< 0.10) of the nearest site, capped at 60, (3) total outage days over the three sites, capped at
120, (4) the reference's share of days >= 0.90, (5) station code (alphabetical). Ties beyond that cannot occur.

## 7. Choice of networks
Region of a network = first matching macro-region of its reference coordinates (lat, lon in degrees), in this order:
1 Antarctica (lat < -60); 2 Iceland-North Atlantic (lat 55-75, lon -45 to -5); 3 Caucasus-Turkey-Iran (lat 25-45, lon 26-63);
4 Central Asia (lat 30-56, lon 45-100); 5 Europe incl. Alps-Balkans (lat 34-72, lon -25 to 45); 6 Africa (lat -40 to 37,
lon -20 to 55); 7 East Asia-West Pacific incl. Japan, Taiwan, Philippines, SE Asia (lat -11 to 56, lon 95-160); 8 New Zealand-SW
Pacific islands (lat -60 to -11, lon 110-180, or lon < -170 and lat < 0); 9 Alaska-Aleutians-Canada (lat >= 50, lon -180 to -50);
10 USA-Mexico (lat 13-50, lon -130 to -60); 11 Central America-Caribbean (lat 5-25, lon -95 to -55, if not 10); 12 South America
(lat -60 to 13, lon -95 to -30); 13 Other (oceanic islands and anything else).
Networks are ranked within their region by the key of section 6 applied to their chosen configuration (earlier window first is
NOT part of the key). Selection is round-robin over regions, regions ordered by the key of their best network: the first network
of each region, then the second of each, and so on, until 24 networks are chosen (target >= 20 networks in >= 8 regions). If fewer
than 20 networks pass, all passing networks are taken and the shortfall is reported with the rejection counts per reason; the
bar is not lowered. If fewer than 8 regions are represented, that is reported, not repaired.

## 8. Records
Every data centre, every network seen, and every rejected configuration or network with its reason is written to
results/v2/selection/ (candidates.json, rejections.csv, chosen.json, raw service responses or their sha256).
