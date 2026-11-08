"""EXPLORATORY, post hoc (not in PREREGISTRATION_CONTEXT_C_2026-11-08.md), written after context_c.json was read.
Question a reviewer will ask: is CG-ctx better than simply a smaller constant c at the SAME escalation budget?
For T1 (reviewed labels) and T2 (catalogue labels): constant c on a 0.05 grid -> pooled escalations and dismissed associated
episodes; compared with CG-ctx. Output: results/context_c/posthoc_equal_budget.json."""
import os, json, importlib.util
import numpy as np, pandas as pd
here = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("cc", os.path.join(here, "context_c.py")); cc = importlib.util.module_from_spec(s); s.loader.exec_module(cc)
from sklearn.linear_model import LogisticRegression
R = cc.R; C = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}
o = json.load(open(os.path.join(cc.OUT, "context_c.json"))); tr = o["training"]
mu = np.array([tr["feature_mean"][f] for f in cc.FEATS]); sd = np.array([tr["feature_sd"][f] for f in cc.FEATS])
w = np.array([tr["coef_standardised"][f] for f in cc.FEATS]); b0 = tr["intercept"]
class M:
    def predict_proba(self, Z):
        p = 1 / (1 + np.exp(-(((Z - mu) / sd) @ w + b0))); return np.c_[1 - p, p]
model = M(); out = {"note": "exploratory, post hoc; not a pre-specified test", "sets": {}}
for name, key, rev in (("T1", "T1_reviewed_batchB", True), ("T2", "T2_catalogue_batchB", False)):
    nets = o[key]["networks_included"]; ds = [cc.load_v2(n, C[n], reviewed=rev) for n in nets]
    grid = np.round(np.arange(0.05, 1.0001, 0.05), 2); rows = []
    tot = {"esc": 0, "dis": 0, "alert_unassoc": 0}; G = {c: {"esc": 0, "dis": 0, "alert_unassoc": 0} for c in grid}; ncx = []
    for d in ds:
        assoc = (d["ep"].assoc_event >= 0).to_numpy(); act, ctx, _ = cc.actions(d, model)
        a = act["CG-ctx"]; tot["esc"] += int((a == "E").sum()); tot["dis"] += int(((a == "D") & assoc).sum()); tot["alert_unassoc"] += int(((a == "A") & ~assoc).sum())
        for r, f in enumerate(d["F"]): ncx += list(ctx[r][f.state == "NO"])
        for c in grid:
            a = cc.cg_with_q(d["S"], [c] * len(d["S"]), d["snr"], d["ok"])
            G[c]["esc"] += int((a == "E").sum()); G[c]["dis"] += int(((a == "D") & assoc).sum()); G[c]["alert_unassoc"] += int(((a == "A") & ~assoc).sum())
    match = min(grid, key=lambda c: (G[c]["esc"] < tot["esc"], abs(G[c]["esc"] - tot["esc"])))
    out["sets"][name] = {"CG_ctx": tot, "mean_ctx_on_NO": round(float(np.mean(ncx)), 3),
                         "constant_c_grid": {str(c): G[c] for c in grid},
                         "constant_c_with_at_least_ctx_escalations": float(match), "at_that_c": G[match]}
    print(name, tot, "mean ctx on NO", round(float(np.mean(ncx)), 3), "match c", match, G[match], flush=True)
json.dump(out, open(os.path.join(cc.OUT, "posthoc_equal_budget.json"), "w"), indent=1)
