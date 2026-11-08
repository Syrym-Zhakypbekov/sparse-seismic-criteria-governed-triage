"""Section 4.1: share of catalogue events whose predicted P arrival falls on valid IU.MAKZ data and that coincide
with an STA/LTA episode (development period). Writes results/stage1_v3/detector_coverage.json.

Run from the repository root:  python analysis/detector_coverage.py
Input: results/stage1_v3/catalog.csv (one row per de-duplicated catalogue event; assoc_episode = -1 if no episode;
makz_valid_at_p = IU.MAKZ had valid data at the predicted P arrival).
Bins: magnitude M <= 3, 3 < M <= 4, M > 4; distance <= 7 degrees, 7-15 degrees.
"""
import json
import os
import sys

import pandas as pd

root = sys.argv[1] if len(sys.argv) > 1 else "."
c = pd.read_csv(os.path.join(root, "results", "stage1_v3", "catalog.csv"))
c = c[c["makz_valid_at_p"].astype(str).str.lower() == "true"].copy()
c["hit"] = c["assoc_episode"] >= 0


def share(df):
    n = int(len(df))
    k = int(df["hit"].sum())
    return {"events": n, "with_episode": k, "share": round(k / n, 4) if n else None}


reg = c[c["kind"] == "regional"]
tel = c[c["kind"] == "tele"]
res = {
    "regional_all": share(reg),
    "regional_by_magnitude": {
        "M<=3": share(reg[reg["mag"] <= 3]),
        "3<M<=4": share(reg[(reg["mag"] > 3) & (reg["mag"] <= 4)]),
        "M>4": share(reg[reg["mag"] > 4]),
    },
    "regional_by_distance": {
        "<=7deg": share(reg[reg["dist_deg"] <= 7]),
        "7-15deg": share(reg[reg["dist_deg"] > 7]),
    },
    "teleseismic": share(tel),
}
json.dump(res, open(os.path.join(root, "results", "stage1_v3", "detector_coverage.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
