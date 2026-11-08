"""Scoring of PREREGISTRATION_KZ_NETWORK.md (repository commit f947bfa), written before any KZ result was read.
Reuses evaluate() of code/20 (same policies, bootstrap and regimes) on results/kz/outKZ_*; roles MAKZ/MK31/KURK/WUS =
KZ.MAKZ/KZ.MKAR/KZ.KURK/KZ.PDGK; CG-D uses the MAKZ development detectability table.
N1 = D3 analogue for CG; N2 CG alerts < P3 and < P1t; N3 CG non-inferiority vs P3; N4 all-missing escalated; N5 CG-D non-inferiority.
"""
import os, json, importlib.util, numpy as np
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("m20", os.path.join(root, "analysis", "cgd_2024.py")); m = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m)
except SystemExit: pass
K = os.path.join(root, "results", "kz")
r = m.evaluate("MAKZ", base=K, prefix="outKZ_20", table_ref="MAKZ")
a, o = r["all"], r["outage"]
out = {"preregistration": "PREREGISTRATION_KZ_NETWORK.md, commit f947bfa", **{k: r[k] for k in ["chunks", "calendar_days", "outage_days", "neighbours_km", "all", "outage"]},
       "N1": {"CG": o["CG"]["missed"], "P1": o["P1"]["missed"], "assoc": o["CG"]["assoc"], "holds": (o["CG"]["missed"] < o["P1"]["missed"]) if o["CG"]["assoc"] else None},
       "N2": {"CG": a["CG"]["alert_unassoc"], "P3": a["P3"]["alert_unassoc"], "P1t": a["P1t"]["alert_unassoc"],
              "holds": a["CG"]["alert_unassoc"] < a["P3"]["alert_unassoc"] and a["CG"]["alert_unassoc"] < a["P1t"]["alert_unassoc"]},
       "N3_CG_noninferiority": r["NI_CG"], "N4": r["ALLMISSING"], "N5_CGD_noninferiority": r["D1"]}
json.dump(out, open(os.path.join(K, "kz_eval.json"), "w"), indent=1, default=str); print(json.dumps({k: out[k] for k in ["N1", "N2", "N3_CG_noninferiority", "N4", "N5_CGD_noninferiority"]}, indent=1))
