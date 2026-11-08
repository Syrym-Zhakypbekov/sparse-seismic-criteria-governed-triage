"""Equivalent SNR thresholds of the frozen rules per neighbour-state pattern (sites by distance rank 1-3).
For each pattern of YES/NO/MISSING states the frozen CG rule (c = 1, c = 0.5, CG-D) is evaluated on an SNR grid (0-40 dB, 0.01 dB)
with a valid SNR; reported: highest SNR still DISMISSED and lowest SNR ALERTED (or none / always escalated).
Uses analysis/v2_networks.policies unchanged. Output: results/posthoc/threshold_table.json and .md.
"""
import os, sys, json, itertools, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
spec = importlib.util.spec_from_file_location("v2t", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec)
sys.modules["v2t"] = v2; spec.loader.exec_module(v2)

snr = np.round(np.arange(0, 40.0001, 0.01), 2); n = len(snr); ok = np.ones(n, bool)
POL = {"CG": "c = 1", "CG_c05": "c = 0.5", "CG-D": "CG-D", "P3": "P3 7.5 dB"}
rows = []
for pat in itertools.product(["YES", "NO", "MISSING"], repeat=3):
    if pat == ("MISSING",) * 3: pass
    S = [np.full(n, s, dtype=object) for s in pat]
    act = v2.policies(S, snr, ok)
    r = {"pattern": "/".join({"YES": "Y", "NO": "N", "MISSING": "M"}[s] for s in pat)}
    for k in POL:
        a = act[k]
        d = snr[a == "D"]; al = snr[a == "A"]
        r[k] = {"dismiss_max_db": float(d.max()) if len(d) else None, "alert_min_db": float(al.min()) if len(al) else None,
                "dismiss_all_below": bool(len(d) == 0 or (a[snr <= d.max()] == "D").all()),
                "alert_all_above": bool(len(al) == 0 or (a[snr >= al.min()] == "A").all())}
    rows.append(r)
out = os.path.join(root, "results", "posthoc"); json.dump(rows, open(os.path.join(out, "threshold_table.json"), "w"), indent=1)
fmt = lambda x: "–" if x is None else f"{x:.2f}"
md = ["| sites 1/2/3 | " + " | ".join(f"{v} dismiss ≤ / alert ≥" for v in POL.values()) + " |", "|---" * (len(POL) + 1) + "|"]
for r in rows:
    md.append(f"| {r['pattern']} | " + " | ".join(f"{fmt(r[k]['dismiss_max_db'])} / {fmt(r[k]['alert_min_db'])}" +
                                               ("" if r[k]["dismiss_all_below"] and r[k]["alert_all_above"] else " *") for k in POL) + " |")
open(os.path.join(out, "threshold_table.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
