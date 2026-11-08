"""Post-hoc gap analyses G1-G3 of PLAN_GAP2_2026-11-08.md (plan pushed before computing).

G1 forward-in-time re-tuning on early windows; G2 low-chance subset; G3 E2/K2 re-scored with G.WUS set to MISSING.
Inputs: results/posthoc/_collect_reviewed.pkl (analysis/posthoc_collect.py), results/v2_reviewed/v2_eval_reviewed.json,
analysis/extended_eval.py and analysis/kurk_extended.py (executed in memory with G.WUS masked; their own output files are not
written). Nothing in pipeline/ is used or changed. Outputs: results/gap2/*.json.
"""
import os, sys, json, importlib.util, io, contextlib
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "results", "gap2"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, here)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


v2 = _load("v2_gap2", os.path.join(here, "v2_networks.py"))
sw = _load("sw_gap2", os.path.join(here, "sens_weights.py"))
from posthoc_collect import collect

FZ = dict(w=0.40, g=1, delta=0.45, ta=0.60, td=0.16)
POLS = ["CG", "CG-D", "CG_c05"]
T_TARGET = 3.0
EARLY_DAYS = 30


def p3(rows_k, t):
    S = rows_k["S"][:3]; snr = rows_k["snr"]; ok = rows_k["ok"]; n = len(snr)
    yes = np.zeros(n, bool)
    for s in S: yes |= s == "YES"
    a = np.full(n, "E", dtype=object); a[yes & ok & (snr >= t)] = "A"; a[(~yes) & ok & (snr < t)] = "D"
    return a


def boot(nets, A, B, mask):
    d = {k: (nets[k]["days"][mask[k]], nets[k]["assoc"][mask[k]], {"X": A[k][mask[k]], "P3": B[k][mask[k]]}) for k in nets}
    d = {k: v for k, v in d.items() if len(v[0])}
    cb = v2.cluster_boot(d, "X", "P3")
    return {x: cb[x] for x in ["pooled_diff_pp", "pooled_ci95_pp", "pooled_noninferior", "ratio", "ratio_ci95", "ratio_criterion_holds"]}


def tally(nets, A, mask):
    o = dict(assoc=0, assoc_D=0, unassoc_A=0, A=0, E=0, D=0, n=0)
    for k in nets:
        m = mask[k]; a = A[k][m]; s = nets[k]["assoc"][m]
        o["assoc"] += int(s.sum()); o["assoc_D"] += int(((a == "D") & s).sum()); o["unassoc_A"] += int(((a == "A") & ~s).sum())
        for x in "AED": o[x] += int((a == x).sum())
        o["n"] += len(a)
    o["assoc_D_share_pct"] = round(100 * o["assoc_D"] / max(o["assoc"], 1), 3)
    o["alert_precision"] = round((o["A"] - o["unassoc_A"]) / max(o["A"], 1), 4)
    return o


def g1(rows, nets):
    early, test = {}, {}
    for k in nets:
        d = np.asarray(nets[k]["days"]); ud = np.array(sorted(set(d)))
        cut = set(ud[:EARLY_DAYS]); e = np.array([x in cut for x in d])
        early[k] = e; test[k] = ~e
    # P3 threshold
    tgrid = np.arange(5.0, 12.0001, 0.25); best_t = None
    for t in tgrid:
        A = {k: p3(rows[k], t) for k in nets}
        if tally(nets, A, early)["assoc_D_share_pct"] <= T_TARGET: best_t = float(t)
    P3r = {k: p3(rows[k], best_t) for k in nets}
    p3_prec = tally(nets, P3r, early)["alert_precision"]
    tuned = {"P3": {"t_db": best_t, "early": tally(nets, P3r, early)}}
    Ar = {}
    for pol in POLS:
        td_best = None
        for td in np.arange(0.04, 0.40001, 0.01):
            A = {k: sw.actions(nets[k], pol, FZ["w"], FZ["g"], FZ["delta"], FZ["ta"], round(float(td), 2)) for k in nets}
            if tally(nets, A, early)["assoc_D_share_pct"] <= T_TARGET: td_best = round(float(td), 2)
        ta_best = None
        for ta in np.arange(max(0.40, td_best + 0.01), 0.90001, 0.01):
            A = {k: sw.actions(nets[k], pol, FZ["w"], FZ["g"], FZ["delta"], round(float(ta), 2), td_best) for k in nets}
            if tally(nets, A, early)["alert_precision"] >= p3_prec: ta_best = round(float(ta), 2); break
        if ta_best is None: ta_best = 0.90
        Ar[pol] = {k: sw.actions(nets[k], pol, FZ["w"], FZ["g"], FZ["delta"], ta_best, td_best) for k in nets}
        tuned[pol] = {"theta_D": td_best, "theta_A": ta_best, "early": tally(nets, Ar[pol], early)}
    P3f = {k: nets[k]["act"]["P3"] for k in nets}
    res = {"target_early_assoc_dismissed_pct": T_TARGET, "early_days": EARLY_DAYS, "tuned": tuned,
           "test_P3_retuned": tally(nets, P3r, test), "test_P3_frozen": tally(nets, P3f, test), "retuned": {}, "frozen_on_test_days": {}}
    for pol in POLS:
        res["retuned"][pol] = dict(boot(nets, Ar[pol], P3r, test), test=tally(nets, Ar[pol], test))
        Af = {k: nets[k]["act"][pol] for k in nets}
        res["frozen_on_test_days"][pol] = dict(boot(nets, Af, P3f, test), test=tally(nets, Af, test))
    dd = {p: res["retuned"][p]["test"]["assoc_D"] for p in POLS}
    res["ordering_retuned_test"] = {"assoc_dismissed": dd, "c1_ge_CGD_ge_c05_or_c1_ge_both": dd["CG"] >= dd["CG-D"] and dd["CG"] >= dd["CG_c05"]}
    return res


def g2(nets):
    ev = json.load(open(os.path.join(root, "results", "v2_reviewed", "v2_eval_reviewed.json")))["networks"]
    share = {k: round(ev[k]["chance_control"]["chance_associated_mean"] / max(ev[k]["associated"], 1), 4) for k in nets}
    low = sorted(k for k in nets if share[k] <= 0.30); high = sorted(k for k in nets if share[k] > 0.30)
    out = {"threshold": 0.30, "chance_share": share, "low": low, "high": high, "results": {}}
    P3 = {k: nets[k]["act"]["P3"] for k in nets}
    for name, keep in [("low_chance", low), ("high_chance", high), ("all", sorted(nets))]:
        sub = {k: nets[k] for k in keep}; mask = {k: np.ones(len(nets[k]["days"]), bool) for k in keep}
        out["results"][name] = {pol: dict(boot(sub, {k: nets[k]["act"][pol] for k in keep}, {k: P3[k] for k in keep}, mask),
                                          test=tally(sub, {k: nets[k]["act"][pol] for k in keep}, mask)) for pol in POLS}
        out["results"][name]["P3"] = tally(sub, {k: P3[k] for k in keep}, mask)
        out["results"][name]["networks"] = len(keep)
    return out


def run_masked(script, marker, outfile_expr):
    src = open(os.path.join(here, script), encoding="utf-8").read()
    assert marker in src, (script, marker)
    src = src.replace(marker, marker + '\nif "WUS" in S: S["WUS"] = np.full(len(S["WUS"]), "MISSING", dtype=object)', 1)
    src = src.replace(outfile_expr, 'os.devnull')
    g = {"__file__": os.path.join(here, script), "__name__": "masked"}
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, script, "exec"), g)
    return g["res"]


def g3():
    e = run_masked("extended_eval.py", 'S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}', 'os.path.join(E, "extended_eval.json")')
    k = run_masked("kurk_extended.py", 'S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}', 'os.path.join(B, "kurk_ext_eval.json")')
    e0 = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
    k0 = json.load(open(os.path.join(root, "results", "kurk_ext", "kurk_ext_eval.json")))
    pick = lambda r, a: {p: {x: r[a][p][x] for x in ["missed", "alert_unassoc", "escalate"]} for p in ["P1", "P1t", "P3", "CG"]}
    return {"E_MAKZ": {"published": {"E2": e0["E2"], "E3": e0["E3"], "all": pick(e0, "all_usable")},
                       "wus_missing": {"E2": e["E2"], "E3": e["E3"], "all": pick(e, "all_usable")}},
            "K_KURK": {"published": {"K2": k0["K2"], "K3": k0["K3"], "all": pick(k0, "all")},
                       "wus_missing": {"K2": k["K2"], "K3": k["K3"], "all": pick(k, "all")}}}


def main():
    rows = collect("reviewed"); nets = sw.prep(rows); assert len(nets) == 33
    rows = {k: rows[k] for k in nets}
    # reproduction: frozen P3 rebuilt here equals stored P3
    mism = sum(int((p3(rows[k], 7.5) != nets[k]["act"]["P3"]).sum()) for k in nets); assert mism == 0, mism
    r1 = g1(rows, nets); json.dump(dict(plan="PLAN_GAP2_2026-11-08.md", **r1), open(os.path.join(OUT, "forward_retune.json"), "w"), indent=1)
    print("G1", json.dumps({p: (r1["retuned"][p]["pooled_diff_pp"], r1["retuned"][p]["pooled_ci95_pp"]) for p in POLS}), r1["tuned"]["P3"]["t_db"])
    r2 = g2(nets); json.dump(dict(plan="PLAN_GAP2_2026-11-08.md", **r2), open(os.path.join(OUT, "low_chance.json"), "w"), indent=1)
    print("G2", len(r2["low"]), len(r2["high"]))
    r3 = g3(); json.dump(dict(plan="PLAN_GAP2_2026-11-08.md", **r3), open(os.path.join(OUT, "wus_removed.json"), "w"), indent=1)
    print("G3 done")


if __name__ == "__main__":
    main()
