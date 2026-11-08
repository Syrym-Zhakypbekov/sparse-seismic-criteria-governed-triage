"""Post hoc (08.11.2026, internal review v30): every SNR baseline threshold by ONE procedure.

The frozen comparisons mixed two procedures: P3 (7.5 dB) and CG (theta_D 0.16) are medians of the five contiguous-block
development folds, P1t (8.0 dB) and P2 (10.5 dB) are full-development values. Under the fold-median procedure applied to all
(results/posthoc/threshold_consistency.json, "B_cv_median"): P1t 7.5 dB, P2 8.0 dB, P3 7.5 dB (unchanged).
Because P3 is unchanged, every pre-specified CG-P3 contrast (E1/E3, K1/K3, D, N, R, V1-V4, reviewed R1-R3) is unchanged by
construction. This script re-scores the hypotheses that involve P1t (E2, K2, N2, R2 and multi-network V6: "CG forwards fewer
unassociated alerts than P1t") and reports P2, with the frozen code paths of analysis/v2_networks.py (policies patched only
for the two thresholds; CG, CG-D, CG c=0.5 and P3 untouched). Writes results/posthoc/same_procedure_baselines.json only.
"""
import os, sys, json, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
R = os.path.join(root, "results")
P1T_SP, P2_SP = 7.5, 8.0
tc = json.load(open(os.path.join(R, "posthoc", "threshold_consistency.json")))
assert tc["thresholds_dB"]["B_cv_median"] == {"P1t": P1T_SP, "P2": P2_SP, "P3": 7.5}, tc["thresholds_dB"]["B_cv_median"]
out = {"status": "post hoc after the internal review (08.11.2026); pre-specified results unchanged",
       "thresholds_dB": {"frozen": tc["thresholds_dB"]["frozen"], "one_procedure_fold_median": tc["thresholds_dB"]["B_cv_median"]},
       "single_network": {}, "multi_network": {}}

# ---- single-network tests (E, K, D, N, R): from threshold_consistency.json, variant B = one procedure
HYP = {"extended IU.MAKZ": "E2", "extended II.KURK": "K2", "KZ network": "N2", "AK network": "R2",
       "2024 IU.MAKZ": "D (no P1t hypothesis)", "2024 II.KURK": "D (no P1t hypothesis)"}
for k, t in tc["tests"].items():
    cg = t["CG"]["unassoc_alerts"]; fr = t["frozen"]; sp = t["B_cv_median"]
    out["single_network"][k] = {
        "hypothesis": HYP.get(k, "-"),
        "CG_unassoc_alerts": cg,
        "P1t_unassoc_alerts": {"frozen_8.0": fr["P1t"]["unassoc_alerts"], "one_procedure_7.5": sp["P1t"]["unassoc_alerts"]},
        "P2": {"frozen_10.5": fr["P2"], "one_procedure_8.0": sp["P2"]},
        "CG_fewer_than_P1t": {"frozen": cg < fr["P1t"]["unassoc_alerts"], "one_procedure": cg < sp["P1t"]["unassoc_alerts"]},
        "CG_minus_P3_pp": {"frozen": fr["CG_minus_P3"], "one_procedure": sp["CG_minus_P3"]},
        "CGD_minus_P3_pp": {"frozen": fr["CGD_minus_P3"], "one_procedure": sp["CGD_minus_P3"]}}

# ---- multi-network sets: frozen scorer, policies patched to add P1t/P2 at the one-procedure thresholds
spec = importlib.util.spec_from_file_location("v2", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
orig_pol = v2.policies


def pol(S, snr, ok, table_ref="MAKZ"):
    act = orig_pol(S, snr, ok, table_ref)
    St = S[:3]; n = len(snr); yes = np.zeros(n, bool); no = np.zeros(n, bool)
    for s in St: yes |= s == "YES"; no |= s == "NO"
    act["P1t_sp"] = np.where(yes | (ok & (snr >= P1T_SP)), "A", "D").astype(object)
    a = np.full(n, "E", dtype=object); a[yes & ok & (snr >= P2_SP)] = "A"; a[(~yes) & ok & (snr < P2_SP) & no] = "D"; act["P2_sp"] = a
    return act


v2.policies = pol
v2.chance_control = lambda *a, **k: {"chance_associated_mean": 0.0}
v2.day_boot = lambda *a, **k: {"diff_pp": None, "ci95_pp": None, "p_one_sided_H0_ge_margin": 1.0}
KEYS = ["CG", "CG-D", "CG_c05", "P3", "P1t", "P1t_sp", "P2", "P2_sp"]


def run_set(batch):
    cfgs, _, prereg = v2.run_list(batch)
    tot = {k: {"dismissed_assoc": 0, "unassoc_alerts": 0} for k in KEYS}; nets = {}; inc = 0
    for cfg in cfgs:
        r = v2.evaluate_network(cfg["network"], cfg)
        if isinstance(r, dict): continue
        res = r[0]
        if not res["included_in_pooled"]: continue
        inc += 1
        cg = res["all"]["CG"]["unassoc_alerts"]
        nets[cfg["network"]] = {"CG": cg, "P1t_frozen": res["all"]["P1t"]["unassoc_alerts"], "P1t_sp": res["all"]["P1t_sp"]["unassoc_alerts"]}
        for k in KEYS:
            tot[k]["dismissed_assoc"] += res["all"][k]["dismissed_assoc"]; tot[k]["unassoc_alerts"] += res["all"][k]["unassoc_alerts"]
    maj = lambda f: sum(1 for v in nets.values() if v["CG"] < v[f])
    return {"preregistration": prereg, "networks_included": inc, "totals": tot,
            "V6_CG_fewer_than_P1t": {"frozen_pooled": tot["CG"]["unassoc_alerts"] < tot["P1t"]["unassoc_alerts"],
                                     "one_procedure_pooled": tot["CG"]["unassoc_alerts"] < tot["P1t_sp"]["unassoc_alerts"],
                                     "frozen_networks": f"{maj('P1t_frozen')}/{inc}", "one_procedure_networks": f"{maj('P1t_sp')}/{inc}"}}


for b in ["A", "B", "EXT"]:
    v2.RUN_DIRS[:] = ["runs"]
    out["multi_network"][b] = run_set(b)
    print(b, json.dumps(out["multi_network"][b]["V6_CG_fewer_than_P1t"]), flush=True)

# ---- reviewed-bulletin labels: same patched scorer, outputs redirected to results/posthoc (never over results/v2_reviewed)
v2.RUN_DIRS[:] = ["runs"]
spec = importlib.util.spec_from_file_location("vr", os.path.join(here, "v2_reviewed_bulletin.py")); vr = importlib.util.module_from_spec(spec)
sys.modules["vr"] = vr; spec.loader.exec_module(vr)
vr.v2 = v2
tot = {k: {"dismissed_assoc": 0, "unassoc_alerts": 0} for k in KEYS}; inc = 0
orig_eval = v2.evaluate_network


def ev(n, cfg):
    global inc
    r = orig_eval(n, cfg)
    if not isinstance(r, dict) and r[0]["included_in_pooled"]:
        inc += 1
        for k in KEYS:
            tot[k]["dismissed_assoc"] += r[0]["all"][k]["dismissed_assoc"]; tot[k]["unassoc_alerts"] += r[0]["all"][k]["unassoc_alerts"]
    return r


v2.evaluate_network = ev
vr.OUT = os.path.join(R, "posthoc", "same_procedure_reviewed_tmp")
vr.score()
out["reviewed_bulletin"] = {"networks_included": inc, "totals": tot,
                            "V6_CG_fewer_than_P1t": {"frozen": tot["CG"]["unassoc_alerts"] < tot["P1t"]["unassoc_alerts"],
                                                     "one_procedure": tot["CG"]["unassoc_alerts"] < tot["P1t_sp"]["unassoc_alerts"]},
                            "note": "primary R1-R3 compare CG with P3, whose threshold is 7.5 dB under both procedures"}
json.dump(out, open(os.path.join(R, "posthoc", "same_procedure_baselines.json"), "w"), indent=1, default=str)
print(json.dumps({k: (v if k != "multi_network" else {b: x["V6_CG_fewer_than_P1t"] for b, x in v.items()}) for k, v in out.items()
                  if k in ("thresholds_dB", "multi_network")}, indent=1))
print("single:", {k: v["CG_fewer_than_P1t"] for k, v in out["single_network"].items()})
print("reviewed:", out["reviewed_bulletin"]["V6_CG_fewer_than_P1t"], inc)
