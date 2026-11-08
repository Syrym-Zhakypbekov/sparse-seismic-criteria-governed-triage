"""Read-only: associated alarms by action (alert / escalate / dismiss) for CG, CG-D and P3 (frozen) on every test set.
Post hoc (08.11.2026, written for the manuscript text). Reuses the helpers of analysis/r12_checks.py and the set
definitions of analysis/threshold_consistency.py. Output: results/posthoc/assoc_actions.json"""
import os, json, glob, sys
import numpy as np, pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(root, "results")
src = open(os.path.join(root, "analysis", "r12_checks.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(root, "analysis", "r12_checks.py")}
exec(compile(src[:src.index("E = os.path.join(R, \"extended\")")], "r12_helpers", "exec"), ns)
load, policies = ns["load"], ns["policies"]
E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
        "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
        "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}
out = {}
for t, (dirs, ref) in SETS.items():
    ep, av, dist = load(dirs); P = policies(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy()
    row = {"episodes": int(len(ep)), "associated": int(assoc.sum())}
    for name in ["P3", "CG", "CG-D"]:
        a = np.asarray(P[name]).astype(str)
        row[name] = {k: int(((a == k) & assoc).sum()) for k in sorted(set(a))}
        row[name]["all_escalated"] = int((a == "E").sum()) if "E" in set(a) else int((a == "ESCALATE").sum())
    out[t] = row; print(t, row, flush=True)
json.dump(out, open(os.path.join(R, "posthoc", "assoc_actions.json"), "w"), indent=1)
