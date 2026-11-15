"""PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md section 5: reviewed labels for 2023, downloaded once.
Queries and parsers of analysis/v2_reviewed_bulletin.py (ISC FDSN QuakeML preferred origin + evaluationStatus; USGS ComCat GeoJSON
with status; ComCat global M >= 5.5) in each network's pipeline circle (reference, 15 deg, M >= 2), monthly pieces
2022-12-31 .. 2024-01-01 -> results/tdh2023_p1/labels/ + SHA256.txt -> gs://p10-raw-waveforms/tdh2023_p1/_labels/."""
import os, sys, json, glob, hashlib, subprocess, importlib.util
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(os.path.dirname(here))
spec = importlib.util.spec_from_file_location("vr", os.path.join(root, "analysis", "v2_reviewed_bulletin.py"))
vr = importlib.util.module_from_spec(spec); sys.modules["vr"] = vr; spec.loader.exec_module(vr)
LAB = os.path.join(root, "results", "tdh2023_p1", "labels"); os.makedirs(LAB, exist_ok=True); vr.LAB = LAB
B = ["2022-12-31"] + [f"2023-{m:02d}-01" for m in range(2, 13)] + ["2024-01-01"]
MONTHS = list(zip(B[:-1], B[1:]))
GCLOUD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
CFG = json.load(open(os.path.join(root, "results", "tdh2023_p1", "networks_tdh2023_p1.json"), encoding="utf-8"))["networks"]
jobs = []
for n, c in CFG.items():
    la, lo = c["stations"]["MAKZ"][4:6]
    for t0, t1 in MONTHS: jobs += [("ISC", n, la, lo, t0, t1), ("USGS", n, la, lo, t0, t1)]
jobs += [("TELE", "ALL", 0, 0, t0, t1) for t0, t1 in MONTHS]
isc = [j for j in jobs if j[0] == "ISC"]; other = [j for j in jobs if j[0] != "ISC"]
with ThreadPoolExecutor(4) as ex: list(ex.map(vr.dl_one, other))
with ThreadPoolExecutor(2) as ex:
    for i, f in enumerate(ex.map(vr.dl_one, isc)): print("ISC", i + 1, len(isc), os.path.basename(f), flush=True)
with open(os.path.join(LAB, "SHA256.txt"), "w") as h:
    for f in sorted(glob.glob(os.path.join(LAB, "*.*"))):
        if not f.endswith("SHA256.txt"): h.write(hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + os.path.basename(f) + "\n")
r = subprocess.run([GCLOUD, "storage", "rsync", LAB, "gs://p10-raw-waveforms/tdh2023_p1/_labels", "--no-clobber", "--quiet"], capture_output=True, text=True)
print("labels", len(jobs), "bucket rc", r.returncode, r.stderr[-300:])
