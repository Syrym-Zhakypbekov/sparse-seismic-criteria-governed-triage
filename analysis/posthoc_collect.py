"""Shared collector for the post-hoc region and workload analyses (PLAN_REGIONS / PLAN_WORKLOAD_2026-11-08.md).

Re-runs the FROZEN per-network evaluation (analysis/v2_networks.evaluate_network) for the 38 networks of the combined
batch-A + batch-B test under two label sets and keeps, per network, the inputs of the frozen policies:
  catalogue  - the plain scorer (as results/v2/v2_eval_AB.json);
  reviewed   - the reviewed-bulletin relabelling of analysis/v2_reviewed_bulletin.py (as results/v2_reviewed/v2_eval_reviewed.json).
Nothing in the decision rules changes; the chance control is skipped because it does not enter inclusion or decisions.
Cache: results/posthoc/_collect_<labels>[_<rundirs>].pkl (local, not committed).
"""
import os, sys, pickle, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
P = os.path.join(root, "results", "posthoc")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


def collect(labels, run_dirs=("runs",), refresh=False):
    tag = labels + ("" if list(run_dirs) == ["runs"] else "_" + "+".join(run_dirs))
    cache = os.path.join(P, f"_collect_{tag}.pkl")
    if os.path.exists(cache) and not refresh: return pickle.load(open(cache, "rb"))
    v2 = _load("v2c_" + tag, os.path.join(here, "v2_networks.py"))
    v2.RUN_DIRS[:] = list(run_dirs)
    v2.chance_control = lambda *a, **k: {"chance_associated_mean": 0.0, "chance_CG_minus_P3_excess_mean": 0.0,
                                         "real_CG_minus_P3_excess": 0, "chance_corrected_CG_minus_P3_pp": 0.0}
    cap = {}; orig_pol = v2.policies

    def pol(S, snr, ok, *a, **k):
        if "S" not in cap: cap.update(S=[np.asarray(s, object) for s in S], snr=np.asarray(snr, float), ok=np.asarray(ok, bool))
        return orig_pol(S, snr, ok, *a, **k)

    v2.policies = pol
    rows = {}; orig_ev = v2.evaluate_network

    def ev(n, cfg):
        cap.clear(); r = orig_ev(n, cfg)
        if isinstance(r, dict): rows[n] = {"status": r.get("status"), "included": False}; return r
        res, (days, assoc, act), outage = r
        rows[n] = {"included": bool(res["included_in_pooled"]), "days": days, "assoc": assoc,
                   "act": {k: act[k] for k in ("P1", "P3", "CG", "CG-D", "CG_c05")},
                   "S": cap["S"], "snr": cap["snr"], "ok": cap["ok"], "calendar_days": res["calendar_days"]}
        return r

    v2.evaluate_network = ev
    vr = _load("vrc_" + tag, os.path.join(here, "v2_reviewed_bulletin.py")); vr.v2 = v2
    C = vr.cfgs()
    if labels == "catalogue":
        for n in vr.NETS: ev(n, C[n])
    else:
        vr.OUT = os.path.join(P, "_collect_reviewed_tmp"); os.makedirs(vr.OUT, exist_ok=True)
        vr.score()
    os.makedirs(P, exist_ok=True); pickle.dump(rows, open(cache, "wb"))
    return rows


if __name__ == "__main__":
    for lab in sys.argv[1:] or ["catalogue", "reviewed"]:
        r = collect(lab, refresh=True); print(lab, sum(v["included"] for v in r.values()), "included of", len(r))
