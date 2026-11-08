"""Scoring of PREREGISTRATION_AK_NETWORK.md, written and pushed before any waveform of the AK run was processed.
Second-region replication: Alaska Earthquake Center network (AK), reviewed regional catalogue through the same ISC + USGS
services. Reuses evaluate() of analysis/cgd_2024.py unchanged (same policies, weights by distance rank, day bootstrap
2000 / seed 7, regimes by the nearest neighbour MK31 role) on results/ak/outAK_20*; CG-D uses the IU.MAKZ development
detectability table mapped by role; the constant c = 0.5 variant is the same evaluate() with a table whose every bin is 0.5.
R1 outage days: CG dismisses fewer associated episodes than P1.  R2 CG unassociated alerts < P3 and < P1t.
R3 CG non-inferior to P3 (upper 95 % day-bootstrap bound <= 3 pp).  R4 every all-missing episode escalated by CG.
R5 CG-D non-inferior to P3.  R6 CG with constant c = 0.5 non-inferior to P3.
Output: results/ak/ak_eval.json
"""
import os, json, importlib.util
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("m20", os.path.join(root, "analysis", "cgd_2024.py")); m = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m)
except SystemExit: pass
A = os.path.join(root, "results", "ak")
ROLES = ["MK31", "KURK", "WUS"]
r = m.evaluate("MAKZ", base=A, prefix="outAK_20", table_ref="MAKZ")             # P1, P1t, P2, P3, CG, CG-D (development table)
m.TAB["CONST_C05"] = {k: {} for k in ROLES}                                      # every bin missing -> p = 0.5 inside evaluate()
c = m.evaluate("MAKZ", base=A, prefix="outAK_20", table_ref="CONST_C05")         # its "CG-D" column = constant c = 0.5
a, o = r["all"], r["outage"]
fails = sorted({f for ch in r["chunks"] for f in ch["catalog_failures"]})
out = {"preregistration": "PREREGISTRATION_AK_NETWORK.md", "scorer": "analysis/ak_network.py",
       **{k: r[k] for k in ["chunks", "calendar_days", "outage_days", "neighbours_km", "all", "outage"]},
       "constant_c05": {"all": c["all"]["CG-D"], "outage": c["outage"]["CG-D"]},
       "catalogue_failures_in_scored_chunks": fails,
       "R1_outage_dismissals": {"CG": o["CG"]["missed"], "P1": o["P1"]["missed"], "P3": o["P3"]["missed"], "assoc": o["CG"]["assoc"],
                                "holds": (o["CG"]["missed"] < o["P1"]["missed"]) if o["CG"]["assoc"] else None},
       "R2_unassociated_alerts": {"CG": a["CG"]["alert_unassoc"], "P3": a["P3"]["alert_unassoc"], "P1t": a["P1t"]["alert_unassoc"],
                                  "holds": a["CG"]["alert_unassoc"] < a["P3"]["alert_unassoc"] and a["CG"]["alert_unassoc"] < a["P1t"]["alert_unassoc"]},
       "R3_CG_noninferiority": r["NI_CG"], "R4_all_missing_escalated": r["ALLMISSING"],
       "R5_CGD_noninferiority": r["D1"], "R6_constant_c05_noninferiority": c["D1"]}
json.dump(out, open(os.path.join(A, "ak_eval.json"), "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ["calendar_days", "outage_days", "neighbours_km", "R1_outage_dismissals", "R2_unassociated_alerts",
                                      "R3_CG_noninferiority", "R4_all_missing_escalated", "R5_CGD_noninferiority", "R6_constant_c05_noninferiority"]}, indent=1))
