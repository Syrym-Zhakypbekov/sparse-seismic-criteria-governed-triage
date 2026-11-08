"""Review R12-m05: archive StationXML (response level) for every channel used, from the EarthScope FDSN station service,
and compare sensor, data logger, sample rate, coordinates and channel epochs of the IU/II/IM/G streams with the KZ
streams at the same sites. Output: results/metadata/*.xml (raw) and results/metadata/station_comparison.json.
"""
import os, json
from obspy.clients.fdsn import Client
from obspy import UTCDateTime

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "metadata"); os.makedirs(OUT, exist_ok=True)
CH = [("IU", "MAKZ", "00", "BHZ"), ("IM", "MK31", "", "BHZ"), ("II", "KURK", "00", "BHZ"), ("G", "WUS", "00", "BHZ"),
      ("KZ", "MAKZ", "*", "BHZ"), ("KZ", "MKAR", "*", "BHZ"), ("KZ", "KURK", "*", "BHZ"), ("KZ", "PDGK", "*", "BHZ")]
c = Client("EARTHSCOPE")
t0, t1 = UTCDateTime("2024-01-01"), UTCDateTime("2026-11-07")
rows = []
for net, sta, loc, cha in CH:
    try:
        inv = c.get_stations(network=net, station=sta, location=loc, channel=cha, starttime=t0, endtime=t1, level="response")
    except Exception as e:
        rows.append({"stream": f"{net}.{sta}.{loc}.{cha}", "error": str(e)[:200]}); continue
    inv.write(os.path.join(OUT, f"{net}.{sta}.xml"), format="STATIONXML")
    for n in inv:
        for s in n:
            for ch in s:
                rows.append({"stream": f"{n.code}.{s.code}.{ch.location_code}.{ch.code}",
                             "start": str(ch.start_date)[:10], "end": str(ch.end_date)[:10] if ch.end_date else None,
                             "lat": ch.latitude, "lon": ch.longitude, "elev_m": ch.elevation, "depth_m": ch.depth,
                             "sample_rate": ch.sample_rate,
                             "sensor": (ch.sensor.description or ch.sensor.model or ch.sensor.type) if ch.sensor else None,
                             "datalogger": (ch.data_logger.description or ch.data_logger.model or ch.data_logger.type) if ch.data_logger else None,
                             "network_description": n.description})
json.dump(rows, open(os.path.join(OUT, "station_comparison.json"), "w"), indent=1, default=str)
for r in rows: print(r)
