"""Checks requested by review R16 (07.11.2026), all post hoc, no tuning:
A. Circular calendar-block bootstrap (10,000 resamples, seed 7; blocks of 1, 7, 14, 28 days; every calendar day kept) for
   the AK contrasts R3 (CG - P3), R5 (CG-D - P3) and R6 (CG with constant c = 0.5 - P3), same code as analysis/r12_checks.py.
   Sanity: the dismissed counts recomputed here must equal results/ak/ak_eval.json.
B. Measured daily availability of the AK stations in the evaluated period (from the pipeline's availability.csv): days with
   valid share < 10 %, 10-90 %, >= 90 % per station, and the longest run of days below 90 % for AK.L22K (MK31 role).
C. StationXML (response level) of the four AK channels from the EarthScope FDSN station service, archived in
   results/metadata/AK.*.xml with retrieval time; summary in results/metadata/ak_station_comparison.json.
D. Repository-host activity records (GitHub activity API) for the AK plan commit 6825835 and results commit 4c04855,
   archived as returned, in results/provenance/ak_host_activity.json.
Output: results/posthoc/r16_checks.json
"""
import os, json, glob, subprocess, datetime
import importlib.util
import numpy as np

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
spec = importlib.util.spec_from_file_location("r12", os.path.join(root, "analysis", "r12_checks.py"))
src = open(os.path.join(root, "analysis", "r12_checks.py"), encoding="utf-8").read()
cut = src.index("E = os.path.join(R, \"extended\")")          # reuse only the helper functions, not the R12 runs
ns = {"__file__": os.path.join(root, "analysis", "r12_checks.py")}
exec(compile(src[:cut], "r12_checks_helpers", "exec"), ns)
load, policies, block_boot = ns["load"], ns["policies"], ns["block_boot"]

out = {"status": "post hoc checks after review R16"}
dirs = sorted(glob.glob(os.path.join(R, "ak", "outAK_20*")))
ep, av, dist = load(dirs)
P = policies(ep, dist, "MAKZ")
assoc = (ep.assoc_event >= 0).to_numpy()
ref = json.load(open(os.path.join(R, "ak", "ak_eval.json")))
check = {k: int(((P[k] == "D") & assoc).sum()) for k in ["P3", "CG", "CG-D", "CG(c=0.5)"]}
stored = {"P3": ref["all"]["P3"]["missed"], "CG": ref["all"]["CG"]["missed"], "CG-D": ref["all"]["CG-D"]["missed"],
          "CG(c=0.5)": ref["constant_c05"]["all"]["missed"]}
out["sanity_dismissed_counts"] = {"recomputed": check, "ak_eval": stored, "equal": check == stored}
out["A_block_bootstrap"] = {name: {"contrast": f"{pol} - P3", "calendar_days": int(len(av)), **block_boot(ep, av.day, P[pol], P["P3"], assoc)}
                            for name, pol in [("R3", "CG"), ("R5", "CG-D"), ("R6", "CG(c=0.5)")]}

cols = [c for c in av.columns if c.endswith("_valid_share")]
B = {}
for c in cols:
    v = av[c].fillna(0).to_numpy(); run = best = 0
    for x in v:
        run = run + 1 if x < 0.9 else 0; best = max(best, run)
    B[c.replace("_valid_share", "")] = {"days": int(len(v)), "lt10": int((v < 0.1).sum()), "10to90": int(((v >= 0.1) & (v < 0.9)).sum()),
                                        "ge90": int((v >= 0.9).sum()), "longest_run_below90_days": int(best),
                                        "min_share": round(float(v.min()), 3)}
out["B_daily_availability"] = B

# C. StationXML
try:
    from obspy.clients.fdsn import Client
    from obspy import UTCDateTime
    MD = os.path.join(R, "metadata"); os.makedirs(MD, exist_ok=True); rows = []
    cl = Client("EARTHSCOPE"); t0, t1 = UTCDateTime("2024-01-01"), UTCDateTime("2025-07-02")
    for sta in ["CUT", "L22K", "COLD", "E22K"]:
        inv = cl.get_stations(network="AK", station=sta, channel="BHZ", starttime=t0, endtime=t1, level="response")
        inv.write(os.path.join(MD, f"AK.{sta}.xml"), format="STATIONXML")
        for n in inv:
            for s in n:
                for ch in s:
                    rows.append({"stream": f"{n.code}.{s.code}.{ch.location_code}.{ch.code}", "start": str(ch.start_date)[:10],
                                 "end": str(ch.end_date)[:10] if ch.end_date else None, "lat": ch.latitude, "lon": ch.longitude,
                                 "depth_m": ch.depth, "sample_rate": ch.sample_rate,
                                 "sensor": (ch.sensor.description or ch.sensor.model) if ch.sensor else None,
                                 "datalogger": (ch.data_logger.description or ch.data_logger.model) if ch.data_logger else None})
    json.dump({"retrieved_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
               "service": "https://service.earthscope.org/fdsnws/station/1/", "rows": rows},
              open(os.path.join(MD, "ak_station_comparison.json"), "w"), indent=1, default=str)
    out["C_stationxml"] = {"channels": len(rows), "file": "results/metadata/ak_station_comparison.json"}
except Exception as e:
    out["C_stationxml"] = {"error": str(e)[:300]}

# D. host activity records
try:
    raw = subprocess.run(["gh", "api", "repos/Syrym-Zhakypbekov/criteria-governed-seismic-alarm-decisions/activity?per_page=100"],
                         capture_output=True, text=True, timeout=60).stdout
    acts = [a for a in json.loads(raw) if a.get("after", "")[:7] in ("6825835", "4c04855")]
    os.makedirs(os.path.join(R, "provenance"), exist_ok=True)
    json.dump({"retrieved_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
               "source": "GitHub REST API repos/{owner}/{repo}/activity (server-side push log)", "records": acts},
              open(os.path.join(R, "provenance", "ak_host_activity.json"), "w"), indent=1)
    out["D_host_activity"] = [{"after": a["after"][:7], "timestamp": a["timestamp"], "activity_type": a.get("activity_type")} for a in acts]
except Exception as e:
    out["D_host_activity"] = {"error": str(e)[:300]}

out["run_script_launch_time"] = open(os.path.join(R, "ak", "outAK_tune", "started_utc.txt")).read().strip()
os.makedirs(os.path.join(R, "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(R, "posthoc", "r16_checks.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
