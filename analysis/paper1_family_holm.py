"""Addendum of PLAN_PAPER1_HARMONISED_2026-11-09.md: Holm over the enlarged Paper 1 primary family.
Inputs: results/paper1/harmonised.json (this repo) and the registry v4-P10 outputs of criteria-governed-cross-domain
(results/p10x/holm.json, onethreshold.json, chance_margins.json, delta_cost.json). Output: results/paper1/primary_family.json."""
import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X = os.environ.get("P10X_DIR", os.path.join(ROOT, "results", "paper1", "p10x"))  # copies of registry v4-P10 outputs
h = json.load(open(os.path.join(ROOT, "results", "paper1", "harmonised.json")))["primary_family_holm"]
px = json.load(open(os.path.join(X, "holm.json")))["p"]
fam = {"E1": h["E1"]["p_one_sided"], "E3": h["E3"]["p_one_sided"], "K3": h["K3"]["p_one_sided"],
       "D1 IU.MAKZ": h["D1 IU.MAKZ"]["p_one_sided"], "D1 II.KURK": h["D1 II.KURK"]["p_one_sided"],
       "P10X-03a": px["P10X-03a"], "P10X-05a": px["P10X-05a"], "P10X-05b": px["P10X-05b"], "P10X-05c": px["P10X-05c"],
       "P10X-06a": px["P10X-06a"]}
ks = sorted(fam, key=lambda k: fam[k]); run = 0.0; out = {}
for i, k in enumerate(ks):
    run = max(run, min(1.0, (len(ks) - i) * fam[k])); out[k] = {"p": fam[k], "p_holm": round(run, 5), "met": run <= 0.025}
json.dump({"alpha_one_sided": 0.025, "members": out}, open(os.path.join(ROOT, "results", "paper1", "primary_family.json"), "w"), indent=1)
for k in ks: print(k, out[k])
