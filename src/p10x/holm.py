"""Holm over family F-P10X (registry v4-P10, 9063f88) and final verdicts in results/registry/P10X-*.json.
Rows whose registered primary rule was not applicable enter with p = 1 (conservative)."""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

J = {os.path.basename(f)[:-5]: json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(REG, "P10X-*.json")))}
p, unadj = {}, {}
for rid in ("P10X-01", "P10X-02"):
    p[rid] = J[rid]["p"] if J[rid]["primary_rule_applicable"] else 1.0; unadj[rid] = J[rid]["verdict_unadjusted"]
p["P10X-03a"] = J["P10X-03"]["sub"]["03a"]["p"]; unadj["P10X-03a"] = J["P10X-03"]["sub"]["03a"]["verdict_unadjusted"]
p["P10X-03b"] = J["P10X-03"]["sub"]["03b"]["p"]; unadj["P10X-03b"] = J["P10X-03"]["sub"]["03b"]["verdict_unadjusted"]
for s in "abc": p[f"P10X-05{s}"] = J[f"P10X-05{s}"]["p"]; unadj[f"P10X-05{s}"] = J[f"P10X-05{s}"]["verdict_unadjusted"]
p["P10X-06a"] = J["P10X-06"]["p"]; unadj["P10X-06a"] = J["P10X-06"]["verdict_unadjusted"]
H = holm(p)
final = {}
for k in p:
    v = unadj[k]
    if v == "HELD" and k != "P10X-06a" and H[k] > 0.025: v = "inconclusive"
    final[k] = v
print(json.dumps({k: [p[k], H[k], unadj[k], final[k]] for k in p}, indent=0))


def put(rid, **kw):
    d = J[rid]; d.update(kw); dump(os.path.join(REG, rid + ".json"), d)


for rid in ("P10X-01", "P10X-02"): put(rid, verdict=final[rid], p_holm=H[rid], p_used_in_holm=p[rid])
d = J["P10X-03"]; d["sub"]["03a"].update(verdict=final["P10X-03a"], p_holm=H["P10X-03a"]); d["sub"]["03b"].update(verdict=final["P10X-03b"], p_holm=H["P10X-03b"])
put("P10X-03", verdict=final["P10X-03a"], p_holm=H["P10X-03a"], sub=d["sub"])
for s in "abc": put(f"P10X-05{s}", verdict=final[f"P10X-05{s}"], p_holm=H[f"P10X-05{s}"])
put("P10X-06", verdict=final["P10X-06a"], p_holm=H["P10X-06a"])
dump(os.path.join(OUT, "holm.json"), {"family": "F-P10X", "alpha_one_sided": 0.025, "p": p, "p_holm": H, "verdict_unadjusted": unadj, "verdict": final})
