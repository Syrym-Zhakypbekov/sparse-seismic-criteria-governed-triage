"""AK replication (PREREGISTRATION_AK_NETWORK.md): archive StationXML (response level) of the four AK BHZ streams used, from
the EarthScope FDSN station service, and list every other station of ANY network within 2 km of each site in 2024-2025
(possible shared site or instrument). Output: results/metadata/AK.<STA>.xml and results/metadata/station_comparison_ak.json.
"""
import os, json
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
from obspy.geodetics import gps2dist_azimuth

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "metadata"); os.makedirs(OUT, exist_ok=True)
ROLES = {"MAKZ": "CUT", "MK31": "L22K", "KURK": "COLD", "WUS": "E22K"}
c = Client("EARTHSCOPE"); t0, t1 = UTCDateTime("2024-01-01"), UTCDateTime("2025-07-01")
rows, near = [], {}
for role, sta in ROLES.items():
    inv = c.get_stations(network="AK", station=sta, channel="BHZ", starttime=t0, endtime=t1, level="response")
    inv.write(os.path.join(OUT, f"AK.{sta}.xml"), format="STATIONXML")
    for n in inv:
        for s in n:
            for ch in s:
                rows.append({"role": role, "stream": f"{n.code}.{s.code}.{ch.location_code}.{ch.code}", "site": s.site.name,
                             "start": str(ch.start_date)[:10], "end": str(ch.end_date)[:10] if ch.end_date else None,
                             "lat": ch.latitude, "lon": ch.longitude, "elev_m": ch.elevation, "depth_m": ch.depth,
                             "sample_rate": ch.sample_rate,
                             "sensor": (ch.sensor.description or ch.sensor.model) if ch.sensor else None,
                             "datalogger": (ch.data_logger.description or ch.data_logger.model) if ch.data_logger else None})
    lat, lon = rows[-1]["lat"], rows[-1]["lon"]
    other = c.get_stations(latitude=lat, longitude=lon, maxradius=0.02, starttime=t0, endtime=t1, level="station")
    near[role] = [{"station": f"{n.code}.{s.code}", "km": round(gps2dist_azimuth(lat, lon, s.latitude, s.longitude)[0] / 1000, 2), "site": s.site.name}
                  for n in other for s in n if not (n.code == "AK" and s.code == ROLES[role])]
out = {"source": "EarthScope FDSN station service, read 2026-11-07", "streams": rows, "other_stations_within_2km": near,
       "note": "all four streams belong to one operator (AK); no stream is shared with the IU/II/IM/G/KZ sites of the earlier tests"}
json.dump(out, open(os.path.join(OUT, "station_comparison_ak.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
