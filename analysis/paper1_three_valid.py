"""Paper 1 v5, Section 3.6 (calibration transfer): share of extended-test episodes (IU.MAKZ, January 2025 - June 2026)
with all three neighbours valid (YES or NO), overall and among catalogue-associated episodes; development for contrast.
Episodes loaded exactly as in analysis/extended_eval.py (same chunks, rerun replacements, usable flag).
Output: results/paper1/three_valid.json. Post hoc bookkeeping (15.11.2026), no new scoring.
"""
import os, json, glob
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = os.path.join(root, "results", "extended"); NB = ["MK31", "KURK", "WUS"]
chunks = sorted(glob.glob(os.path.join(E, "vm_2025", "out_*"))) + [os.path.join(E, "kaggle_2026h1")]
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
frames = []
for d in chunks:
    name = os.path.basename(d); src = rerun.get(name, d)
    s = json.load(open(os.path.join(src, "summary.json"))); fails = s.get("catalog_failures", [])
    log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(src, "*.log")))
    if "regional catalog error" in log and not s.get("catalog_failures") and "catalog_failures" not in s:
        fails = ["ISC (rate limit, first run)"]
    ep = pd.read_csv(os.path.join(src, "episodes.csv")); ep["usable"] = not fails; frames.append(ep)
ep = pd.concat(frames, ignore_index=True)


def share(df):
    v = np.ones(len(df), bool)
    for k in NB:
        v &= df[f"n_{k}"].astype(str).isin(["YES", "NO"]).to_numpy()
    a = (df.assoc_event >= 0).to_numpy()
    return {"episodes": int(len(df)), "three_valid": int(v.sum()), "share": round(float(v.mean()), 4),
            "associated": int(a.sum()), "associated_three_valid": int((v & a).sum()), "associated_share": round(float(v[a].mean()), 4)}


out = {"status": "post hoc bookkeeping for Paper 1 v5 Section 3.6", "all_chunks": share(ep), "usable_chunks": share(ep[ep.usable])}
json.dump(out, open(os.path.join(root, "results", "paper1", "three_valid.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
