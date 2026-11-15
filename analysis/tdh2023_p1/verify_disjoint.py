"""PLAN_TDH2023_PAPER1_2026-11-09.md section 2: is 2023 untouched for the Paper 1 networks (IU.MAKZ set, AK set)?
Requests no waveform, event or label. Scans every availability.csv, episodes.csv and summary.json under results/ for any day in 2023
and for the station codes of the two networks; lists gs://p10-raw-waveforms for any object with 2023 or tdh2023_p1 in its path.
Output: results/tdh2023_p1/disjoint_check.json"""
import os, glob, json, subprocess, datetime as dt
import pandas as pd
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); R = os.path.join(root, "results")
OUT = os.path.join(R, "tdh2023_p1"); os.makedirs(OUT, exist_ok=True)
STA = {"IU.MAKZ set": ["IU.MAKZ", "IM.MK31", "II.KURK", "G.WUS"], "AK set": ["AK.CUT", "AK.L22K", "AK.COLD", "AK.E22K"]}
GCLOUD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
hits, n = [], {"availability": 0, "episodes": 0, "summary": 0}
for f in glob.glob(os.path.join(R, "**", "availability.csv"), recursive=True):
    n["availability"] += 1
    try: d = pd.read_csv(f, usecols=["day"]).day.astype(str)
    except Exception: continue
    if d.str.startswith("2023").any(): hits.append({"file": os.path.relpath(f, root), "days_2023": int(d.str.startswith("2023").sum())})
for f in glob.glob(os.path.join(R, "**", "episodes.csv"), recursive=True):
    n["episodes"] += 1
    try: d = pd.read_csv(f, usecols=["t_on_utc"]).t_on_utc.astype(str)
    except Exception: continue
    if d.str.startswith("2023").any(): hits.append({"file": os.path.relpath(f, root), "episodes_2023": int(d.str.startswith("2023").sum())})
sta_hits = []
for f in glob.glob(os.path.join(R, "**", "summary.json"), recursive=True):
    n["summary"] += 1; s = open(f, encoding="utf-8", errors="ignore").read()
    for name, codes in STA.items():
        if any(c in s for c in codes) and "2023-" in s: sta_hits.append({"file": os.path.relpath(f, root), "set": name})
# which of the 2023 hits belong to the two networks? (the tdh2023 33-network test uses other networks)
p1 = []
for h in hits:
    d = os.path.dirname(os.path.join(root, h["file"])); s = os.path.join(d, "summary.json")
    txt = open(s, encoding="utf-8", errors="ignore").read() if os.path.exists(s) else ""
    st = os.path.join(os.path.dirname(d), "status.json"); txt += open(st, encoding="utf-8", errors="ignore").read() if os.path.exists(st) else ""
    for name, codes in STA.items():
        if any(c.replace(".", '", "') in txt or c in txt for c in codes): p1.append({**h, "set": name})
r = subprocess.run([GCLOUD, "storage", "ls", "-r", "gs://p10-raw-waveforms/**"], capture_output=True, text=True)
objs = r.stdout.splitlines(); b23 = [o for o in objs if "tdh2023_p1" in o or "/AK/" in o or "/IU/" in o]   # the 33-net test stores roles named MAKZ under other network codes (tdh2023/<NET>/MAKZ.*): not this station
res = {"checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "files_scanned": n,
       "files_with_2023_days": hits, "of_which_paper1_networks": p1, "summary_json_with_station_codes_and_2023": sta_hits,
       "bucket_objects": len(objs), "bucket_rc": r.returncode, "bucket_objects_paper1_2023": b23,
       "all_disjoint": not p1 and not b23 and r.returncode == 0}
json.dump(res, open(os.path.join(OUT, "disjoint_check.json"), "w"), indent=1)
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items()}, indent=1))
