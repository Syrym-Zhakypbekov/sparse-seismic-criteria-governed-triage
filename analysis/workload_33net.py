"""Post hoc (08.11.2026, internal review v30): operator workload of the reviewed-bulletin test (Section 4.12, 33 networks).

For each included network and policy (P1, P3, CG, CG-D, CG c = 0.5): automatic alerts, automatic dismissals and escalations
among ALL episodes and among reviewed-associated episodes, and escalations per day. Frozen actions (analysis/v2_networks.py)
with the reviewed labels of analysis/v2_reviewed_bulletin.py. Writes results/posthoc/workload_33net.json only.
"""
import os, sys, json, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
P = os.path.join(root, "results", "posthoc")
spec = importlib.util.spec_from_file_location("v2", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
v2.chance_control = lambda *a, **k: {"chance_associated_mean": 0.0}
POL = ["P1", "P3", "CG", "CG-D", "CG_c05"]
rows = {}
orig = v2.evaluate_network


def ev(n, cfg):
    r = orig(n, cfg)
    if not isinstance(r, dict) and r[0]["included_in_pooled"]:
        days, assoc, act = r[1]; nd = r[0]["calendar_days"]
        rows[n] = {"days": nd, "episodes": int(len(assoc)), "reviewed_associated": int(assoc.sum()),
                   **{k: {"all": {w: int((act[k] == w).sum()) for w in "ADE"},
                          "reviewed_associated": {w: int(((act[k] == w) & assoc).sum()) for w in "ADE"},
                          "escalations_per_day": round(float((act[k] == "E").sum()) / max(nd, 1), 2)} for k in POL}}
    return r


v2.evaluate_network = ev
spec = importlib.util.spec_from_file_location("vr", os.path.join(here, "v2_reviewed_bulletin.py")); vr = importlib.util.module_from_spec(spec)
sys.modules["vr"] = vr; spec.loader.exec_module(vr); vr.v2 = v2
vr.OUT = os.path.join(P, "workload_reviewed_tmp")
vr.score()
tot = {k: {s: {w: sum(r[k][s][w] for r in rows.values()) for w in "ADE"} for s in ("all", "reviewed_associated")} for k in POL}
epd = {k: [r[k]["escalations_per_day"] for r in rows.values()] for k in POL}
out = {"status": "post hoc (internal review v30)", "networks": len(rows), "episodes": sum(r["episodes"] for r in rows.values()),
       "reviewed_associated": sum(r["reviewed_associated"] for r in rows.values()), "totals": tot,
       "escalations_per_day_per_network": {k: {"median": round(float(np.median(v)), 2), "min": min(v), "max": max(v)} for k, v in epd.items()},
       "per_network": rows}
json.dump(out, open(os.path.join(P, "workload_33net.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in ("networks", "episodes", "reviewed_associated", "totals", "escalations_per_day_per_network")}, indent=1))
