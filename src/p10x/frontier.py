"""P10X-01 and P10X-02 (registry v4-P10, 9063f88): equal-budget held-out comparison of CG with the two-threshold
abstaining rule (P3-2t) and with its availability-aware version (P3-2t-av). Output: results/p10x/frontier.json and
results/registry/P10X-01.json, P10X-02.json (verdicts; Holm is applied later in holm.py)."""
import os, sys, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

rows, nets, pkl_sha = load_reviewed()
dev = [k for k in nets if k in BATCH_A]; held = [k for k in nets if k in BATCH_B]
assert len(dev) == 7 and len(held) == 26 and not set(dev) & set(held), (dev, len(held))

CS = [0.25, 0.5, 0.75, 1.0]
TDS = np.round(np.arange(0.08, 0.2401, 0.02), 2); TAS = np.round(np.arange(0.45, 0.9001, 0.05), 2)
CG_GRID = [(c, td, ta) for c in CS for td in TDS for ta in TAS]
P3_GRID = [(td, ta) for td in np.arange(5.0, 12.01, 0.5) for ta in np.arange(td, 20.01, 0.5)]
assert len(CG_GRID) == 360 and len(P3_GRID) == 360

F = {}
for k in nets:
    r = rows[k]; S = r["S"]; snr = np.asarray(r["snr"], float); ok = np.asarray(r["ok"], bool)
    F[k] = {"D": {c: cg_score(S, snr, ok, c) for c in CS}, "yes": anyyes(S), "miss": anymissing(S), "snr": snr, "ok": ok,
            "assoc": np.asarray(r["assoc"], bool), "n": len(snr)}
    # self-checks against the frozen actions
    assert (act_from_D(F[k]["D"][1.0], THETA_D, THETA_A) == to_int(r["act"]["CG"])).all(), k
    assert (act_from_D(F[k]["D"][0.5], THETA_D, THETA_A) == to_int(r["act"]["CG_c05"])).all(), k
    assert (p3_2t(F[k]["yes"], snr, ok, 7.5, 7.5) == to_int(r["act"]["P3"])).all(), k


def acts(fam, p, k):
    f = F[k]
    if fam == "CG": return act_from_D(f["D"][p[0]], p[1], p[2])
    return p3_2t(f["yes"], f["snr"], f["ok"], p[0], p[1], f["miss"] if fam == "P3-2t-av" else None)


def dev_metrics(fam, p, ks, mask=None):
    Da = Au = E = n = A = 0
    for k in ks:
        a = acts(fam, p, k); s = F[k]["assoc"]
        if mask is not None: a, s = a[mask[k]], s[mask[k]]
        Da += int(((a == -1) & s).sum()); A += int(s.sum()); Au += int(((a == 1) & ~s).sum()); E += int((a == 0).sum()); n += len(a)
    return {"dism_share": Da / max(A, 1), "esc_share": E / n, "ua_per_ep": Au / n, "Da": Da, "Au": Au, "E": E, "n": n, "assoc": A}


GRIDS = {"CG": CG_GRID, "P3-2t": P3_GRID, "P3-2t-av": P3_GRID}


def select(tab, m, e):
    relax = 0.0
    while True:
        okp = [(p, x) for p, x in tab if x["dism_share"] <= m and x["esc_share"] <= e + relax]
        if okp: break
        relax += 0.10
        if e + relax > 1.0001:   # dismissal constraint infeasible at any escalation cap: NOT covered by the registered rule
            okp = tab; relax = None; break      # fallback (unregistered): min unassociated alerts over the whole grid; flagged
    p, x = min(okp, key=lambda t: (t[1]["ua_per_ep"], t[1]["esc_share"], t[1]["Da"]))
    return p, x, (None if relax is None else round(relax, 2))


def select_cost(tab, rm, re_):
    return min(tab, key=lambda t: rm * t[1]["Da"] + t[1]["Au"] + re_ * t[1]["E"])


def evaluate(selected, ks, mask=None):
    """selected: {fam: params}; returns DayTable full + boots and contrasts CG vs others."""
    A = {fam: {} for fam in selected}
    rr = {}
    for k in ks:
        r = rows[k]
        if mask is None: rr[k] = r
        else: rr[k] = {"days": np.asarray(r["days"])[mask[k]], "assoc": np.asarray(r["assoc"], bool)[mask[k]]}
        for fam, p in selected.items():
            a = acts(fam, p, k); A[fam][k] = a if mask is None else a[mask[k]]
    T = DayTable(rr, ks, A); full = T.full(); B = T.boot()
    return {f"CG_vs_{fam}": contrast(full, B, "CG", fam) for fam in selected if fam != "CG"}


def run_split(train, test, mask_tr=None, mask_te=None, label=""):
    tabs = {fam: [(p, dev_metrics(fam, p, train, mask_tr)) for p in GRIDS[fam]] for fam in GRIDS}
    res = {"train_networks": train if mask_tr is None else "all 33, first half of days", "test_networks": test if mask_te is None else "all 33, second half of days",
           "rules": {}}
    rules = [("m0.03_e0.40 (primary)", "con", (0.03, 0.40))] + [(f"m{m}_e{e}", "con", (m, e)) for m in (0.03, 0.05) for e in (0.30, 0.40, 0.50) if (m, e) != (0.03, 0.40)] + [("cost rm50_re0.25", "cost", (50, 0.25))]
    if label: rules = rules[:1]
    for name, kind, par in rules:
        sel = {}; info = {}
        for fam, tab in tabs.items():
            if kind == "con": p, x, relax = select(tab, *par)
            else: (p, x), relax = select_cost(tab, *par), 0.0
            sel[fam] = p; info[fam] = {"params": [float(v) for v in p], "dev": x, "escalation_cap_relaxed_by": relax,
                         "dismissal_constraint_infeasible_on_dev": relax is None}
        res["rules"][name] = {"selected": info, "heldout": evaluate(sel, test, mask_te)}
        print(label, name, {f: info[f]["params"] for f in info}, flush=True)
    return res


out = {"registry": "plan/HYPOTHESIS_REGISTRY_V4_P10.md @ 9063f88", "pickle_sha256": pkl_sha,
       "dev_networks": dev, "heldout_networks": held,
       "grids": {"CG": "c {0.25,0.5,0.75,1.0} x theta_D 0.08..0.24/0.02 x theta_A 0.45..0.90/0.05 (360)",
                 "P3-2t": "t_D 5..12/0.5, t_A t_D..20/0.5 (360)", "P3-2t-av": "same as P3-2t; never dismiss with any site MISSING"},
       "bootstrap": "two-stage paired cluster (networks, then days with episodes), 2000, seed 7; per-network-day = per day with episodes"}
out["batch_split"] = run_split(dev, held)
# temporal split (secondary): first half of each network's days with episodes -> second half
mtr, mte = {}, {}
for k in nets:
    d = np.asarray(rows[k]["days"]); ud = np.unique(d); cut = ud[len(ud) // 2]
    mtr[k] = d < cut; mte[k] = d >= cut
out["temporal_split"] = run_split(nets, nets, mtr, mte, label="temporal")
dump(os.path.join(OUT, "frontier.json"), out)

prim = out["batch_split"]["rules"]["m0.03_e0.40 (primary)"]
alt = out["batch_split"]["rules"]["m0.05_e0.4"]; tmp = out["temporal_split"]["rules"]["m0.03_e0.40 (primary)"]
def summ(rule, fam):
    c = rule["heldout"][f"CG_vs_{fam}"]
    comps = [(c["dism_pp"]["est"], c["dism_pp"]["ci"][1], 3.0), (c["esc_ratio"]["est"], c["esc_ratio"]["ci"][1], 1.10)]
    return {"dism_pp": c["dism_pp"], "esc_ratio": c["esc_ratio"], "ua_per_nd": c["ua_per_nd"], "esc_per_nd": c["esc_per_nd"],
            "p": max(c["p_dism_ge_margin"], c["p_escratio_ge_max"]), "verdict_rule_applied": verdict(comps),
            "selected": {f: rule["selected"][f] for f in ("CG", fam)}}
for rid, fam in (("P10X-01", "P3-2t"), ("P10X-02", "P3-2t-av")):
    c = prim["heldout"][f"CG_vs_{fam}"]
    infeasible = any(prim["selected"][f]["dismissal_constraint_infeasible_on_dev"] for f in ("CG", fam))
    comps = [(c["dism_pp"]["est"], c["dism_pp"]["ci"][1], 3.0), (c["esc_ratio"]["est"], c["esc_ratio"]["ci"][1], 1.10)]
    dump(os.path.join(REG, f"{rid}.json"), {
        "family": "F-P10X", "id": rid, "chain": "A",
        "data": "33 reviewed-bulletin networks; tuned on 7 batch-A, evaluated on 26 batch-B (P10 a97d376)",
        "metric": f"CG - {fam}: dismissed share of reviewed-associated (pp) and escalation ratio CG/{fam}, held out, equal 360-setting budget",
        "est": c["dism_pp"]["est"], "ci": c["dism_pp"]["ci"],
        "esc_ratio": c["esc_ratio"], "unassoc_alerts_per_network_day_diff": c["ua_per_nd"], "esc_per_network_day_diff": c["esc_per_nd"],
        "p": max(c["p_dism_ge_margin"], c["p_escratio_ge_max"]), "p_components": [c["p_dism_ge_margin"], c["p_escratio_ge_max"]],
        "verdict_unadjusted": ("inconclusive" if infeasible else verdict(comps)), "verdict": None,
        "primary_rule_applicable": not infeasible,
        "registered_primary_as_computed_with_unregistered_fallback": {"verdict_rule_applied": verdict(comps)},
        "deviation_D_P10X_1_m5_e40_batch_split": summ(alt, fam), "secondary_temporal_split_primary_constraint": summ(tmp, fam),
        "selected": {f: prim["selected"][f] for f in ("CG", fam)}, "levels": c["levels"],
        "note": ("PRIMARY RULE NOT APPLICABLE: on the 7 dev networks no " + fam + " setting met dismissed share <= 3% at any escalation cap (registered rule silent on this) -> verdict inconclusive; see deviation D-P10X-1 (m 5%/e 40%, registered secondary, chosen after all outputs were printed) and the temporal split. " if infeasible else "") + "Selection on dev: min unassociated alerts s.t. dism<=3%, esc<=40%. Margins 3 pp and ratio 1.10. Final verdict after Holm (holm.py). Secondaries in results/p10x/frontier.json."})
    print(rid, comps, verdict(comps))
