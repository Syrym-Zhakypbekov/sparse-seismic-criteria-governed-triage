"""PLAN_REVIEW3_2026-11-08.md (pushed 23c1cd8 before computing), post hoc, descriptive.

1. detprob_schorlemmer: Schorlemmer & Woessner (2008) style detection probability P(site confirms | M, distance) fitted on
   batch-A catalogue-associated episodes, compared on batch B with the context-dependent c_j(x), the CG-D table and 0.5.
2. costopt_thresholds: Chow / Fumera cost-optimal dismiss/alert SNR thresholds per neighbour-state pattern (nYES, nNO,
   nMISSING), fitted on batch A (reviewed labels), evaluated on batch B against the frozen rules.
3. draelos_screen: Draelos et al. (2012) style false-event screen from batch-A cell association rates.
Outputs: results/review3/*.json. Laptop only.
"""
import os, sys, json, glob, math, importlib.util
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from scipy.stats import pearsonr, spearmanr

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); sys.path.insert(0, here)
R = os.path.join(root, "results"); OUT = os.path.join(R, "review3")
from posthoc_collect import collect, _load
v2 = _load("v2r3", os.path.join(here, "v2_networks.py"))
cc = _load("ccr3", os.path.join(here, "context_c.py"))
SEED = 7
A_NETS = [c["network"] for c in json.load(open(os.path.join(R, "v2", "networks.json")))["networks"]]
B_NETS = [c["network"] for c in json.load(open(os.path.join(R, "v2", "networks_batchB.json")))["networks"]]
CFG = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}


def jdump(o, name):
    os.makedirs(OUT, exist_ok=True)
    json.dump(o, open(os.path.join(OUT, name), "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))


def km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def ece(p, y, nb=10):
    b = np.clip((p * nb).astype(int), 0, nb - 1); e = 0.0
    for i in range(nb):
        m = b == i
        if m.any(): e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


# ------------------------------------------------------------------ 1. detection probability
def event_cols(net):
    """Episodes of a network (catalogue labels) with magnitude and epicentre of the associated catalogue row, in the order
    of context_c.load_v2 (chunks concatenated in sorted order, then a stable sort by t_on)."""
    dirs = sorted(glob.glob(os.path.join(R, "v2", "runs", net, "out_*"))); parts = []
    for d in dirs:
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); cat = pd.read_csv(os.path.join(d, "catalog.csv"))
        i = ep.assoc_event.to_numpy(); ok = (i >= 0) & (i < len(cat)); j = np.where(ok, i, 0)
        ep["ev_mag"] = np.where(ok, cat.mag.to_numpy(float)[j], np.nan)
        ep["ev_lat"] = np.where(ok, cat.lat.to_numpy(float)[j], np.nan); ep["ev_lon"] = np.where(ok, cat.lon.to_numpy(float)[j], np.nan)
        parts.append(ep[["t_on", "ev_mag", "ev_lat", "ev_lon"]])
    return pd.concat(parts, ignore_index=True).sort_values("t_on", kind="stable").reset_index(drop=True)


def pairs_with_event(d, ev, ctxp=None):
    assoc = (d["ep"].assoc_event >= 0).to_numpy(); rows = []
    assert np.allclose(d["ep"].t_on.to_numpy(), ev.t_on.to_numpy()), d["net"]
    for r, f in enumerate(d["F"]):
        mem = CFG[d["net"]]["sites"][r]["members"]
        dist = np.min([km(ev.ev_lat.to_numpy(), ev.ev_lon.to_numpy(), m["lat"], m["lon"]) for m in mem], axis=0)
        m = assoc & np.isin(f.state, ["YES", "NO"]) & np.isfinite(ev.ev_mag.to_numpy()) & np.isfinite(dist)
        rows.append(pd.DataFrame({"net": d["net"], "rank": r, "y": (f.state[m] == "YES").astype(int),
                                  "mag": ev.ev_mag.to_numpy()[m], "logd": np.log10(np.maximum(dist[m], 1.0)),
                                  "p_tab": cc.tab_p(f, r)[m], "p_ctx": (ctxp[r][m] if ctxp is not None else np.nan)}))
    return pd.concat(rows, ignore_index=True)


MBINS = [-9, 2, 3, 4, 5, 99]; DBINS = [0, 100, 300, 1000, 3000, 1e9]


def detprob():
    # context model, refitted exactly as analysis/context_c.py main()
    train_ctx = [cc.load_local("IU_dev")] + [x for x in (cc.load_v2(n, CFG[n]) for n in cc.TRAIN_V2) if x is not None]
    X, y = [], []
    for d in train_ctx:
        a = (d["ep"].assoc_event >= 0).to_numpy()
        for f in d["F"]:
            m = a & np.isin(f.state, ["YES", "NO"]); X.append(f[cc.FEATS].to_numpy()[m]); y.append((f.state[m] == "YES").astype(int))
    X = np.vstack(X); y = np.concatenate(y); mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    ctx = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - mu) / sd, y)
    pctx = lambda F: [np.clip(ctx.predict_proba((f[cc.FEATS].to_numpy() - mu) / sd)[:, 1], *cc.CLIP) for f in F]
    # Schorlemmer-style estimators on batch-A catalogue pairs (same networks as context_c TRAIN_V2)
    tr = []
    for n in cc.TRAIN_V2:
        d = cc.load_v2(n, CFG[n])
        if d is not None: tr.append(pairs_with_event(d, event_cols(n)))
    T = pd.concat(tr, ignore_index=True)
    def design(P): return np.column_stack([P.mag, P.logd, P["rank"] == 1, P["rank"] == 2]).astype(float)
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(design(T), T.y)
    T["mb"] = pd.cut(T.mag, MBINS, labels=False); T["db"] = pd.cut(10 ** T.logd, DBINS, labels=False)
    tab = T.groupby(["mb", "db"]).y.agg(["mean", "count"])
    catB = json.load(open(os.path.join(R, "v2", "v2_eval_batchB.json")))["networks"]
    te = []
    for n in B_NETS:
        if not catB.get(n, {}).get("included_in_pooled"): continue
        d = cc.load_v2(n, CFG[n])
        if d is None: continue
        te.append(pairs_with_event(d, event_cols(n), pctx(d["F"])))
    P = pd.concat(te, ignore_index=True)
    P["p_pd_lr"] = lr.predict_proba(design(P))[:, 1]
    mb = pd.cut(P.mag, MBINS, labels=False); db = pd.cut(10 ** P.logd, DBINS, labels=False)
    pb = []
    for i, (a, b) in enumerate(zip(mb, db)):
        k = (a, b)
        pb.append(tab.loc[k, "mean"] if k in tab.index and tab.loc[k, "count"] >= 20 else P.p_pd_lr.iloc[i])
    P["p_pd_bin"] = np.array(pb, float); P["c05"] = 0.5; yv = P.y.to_numpy()
    est = ("p_pd_lr", "p_pd_bin", "p_ctx", "p_tab", "c05")
    res = {"plan": "PLAN_REVIEW3_2026-11-08.md (23c1cd8)", "machine": "laptop",
           "training": {"networks": cc.TRAIN_V2, "pairs": int(len(T)), "confirm_rate": round(float(T.y.mean()), 4),
                        "logistic_coef": dict(zip(["mag", "log10_dist_km", "rank2", "rank3"], [round(float(c), 4) for c in lr.coef_[0]])),
                        "intercept": round(float(lr.intercept_[0]), 4)},
           "test": {"networks": sorted(P.net.unique().tolist()), "pairs": int(len(P)), "confirm_rate": round(float(yv.mean()), 4)},
           "brier": {k: round(float(((P[k] - yv) ** 2).mean()), 4) for k in est},
           "ece": {k: round(ece(P[k].to_numpy(float), yv), 4) for k in est if k != "c05"},
           "agreement_with_ctx": {}}
    for k in ("p_pd_lr", "p_pd_bin", "p_tab"):
        res["agreement_with_ctx"][k] = {"pearson": round(float(pearsonr(P[k], P.p_ctx)[0]), 3),
                                        "spearman": round(float(spearmanr(P[k], P.p_ctx)[0]), 3),
                                        "mean_abs_diff": round(float((P[k] - P.p_ctx).abs().mean()), 3)}
    bins = np.linspace(0, 1, 11); rel = {}
    for k in ("p_pd_lr", "p_ctx", "p_tab"):
        b = np.clip(np.digitize(P[k], bins) - 1, 0, 9)
        rel[k] = [{"lo": round(float(bins[i]), 1), "n": int((b == i).sum()), "mean_pred": round(float(P[k][b == i].mean()), 3),
                   "obs": round(float(yv[b == i].mean()), 3)} for i in range(10) if (b == i).sum() >= 20]
    res["reliability"] = rel
    # by magnitude: does c_j(x) track detection probability across magnitudes?
    res["by_magnitude_bin"] = [{"mag_bin": f"{MBINS[i]}..{MBINS[i + 1]}", "n": int((mb == i).sum()), "obs": round(float(yv[mb == i].mean()), 3),
                                "p_pd_lr": round(float(P.p_pd_lr[mb == i].mean()), 3), "p_ctx": round(float(P.p_ctx[mb == i].mean()), 3),
                                "p_tab": round(float(P.p_tab[mb == i].mean()), 3)} for i in range(5) if (mb == i).sum() >= 20]
    jdump(res, "detprob_schorlemmer.json"); plot_rel(P); return res


def plot_rel(P):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 5)); bins = np.linspace(0, 1, 11)
    for k, lab, mk in (("p_pd_lr", "detection probability P(M, d)", "^"), ("p_ctx", "context c_j(x)", "o"), ("p_tab", "CG-D table", "s")):
        b = np.clip(np.digitize(P[k], bins) - 1, 0, 9); xs, ys = [], []
        for i in range(10):
            m = b == i
            if m.sum() >= 20: xs.append(P[k][m].mean()); ys.append(P.y[m].mean())
        ax.plot(xs, ys, marker=mk, label=lab)
    ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("predicted confirmation probability"); ax.set_ylabel("observed confirmation rate")
    ax.set_title("Batch B, catalogue-associated episodes", fontsize=9); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "detprob_reliability.png"), dpi=200); plt.close(fig)


# ------------------------------------------------------------------ shared reviewed rows
def reviewed_rows():
    rows = collect("reviewed"); out = {}
    for k, v in rows.items():
        if not v.get("included"): continue
        S = [np.asarray(s, object) for s in v["S"][:3]]; act = v2.policies(S, v["snr"], v["ok"])
        for p in ("P3", "CG", "CG-D", "CG_c05", "P1"): assert (act[p] == v["act"][p]).all(), (k, p)
        act["P3_2t"] = p3_2t(S, v["snr"], v["ok"], 8.0, 13.5)
        out[k] = dict(v, S=S, act=act)
    return out


def p3_2t(S, snr, ok, td, ta):
    y = np.zeros(len(snr), bool)
    for s in S: y |= s == "YES"
    a = np.full(len(snr), "E", dtype=object); a[y & ok & (snr >= ta)] = "A"; a[(~y) & ok & (snr < td)] = "D"; return a


def counts_pattern(S):
    ny = sum((s == "YES").astype(int) for s in S); nn = sum((s == "NO").astype(int) for s in S)
    return np.array([f"{a}{b}{3 - a - b}" for a, b in zip(ny, nn)], object)


# ------------------------------------------------------------------ 2. cost-optimal thresholds
GRID = np.arange(0, 30.01, 0.5); KS = (30, 60, 120, 240); C_E, C_A = 2.0, 1.0


def ep_cost(a, assoc, k, F=0.0):
    return np.where(a == "E", C_E, np.where(a == "A", C_A + np.where(assoc, 0.0, F), np.where(assoc, k, 0.0)))


def fit_pattern(snr, assoc, k, F=0.0):
    """Best (tD, tA) for episodes with defined SNR: dismiss below tD, alert at/above tA, escalate between."""
    best = (np.inf, None)
    for i, td in enumerate(GRID):
        D = snr < td; dc = k * (assoc & D).sum()
        for ta in GRID[i:]:
            A = snr >= ta; E = ~D & ~A
            c = dc + C_A * A.sum() + F * (A & ~assoc).sum() + C_E * E.sum()
            if c < best[0]: best = (c, (float(td), float(ta)))
    return best[1]


def apply_opt(rule, S, snr, ok):
    pat = counts_pattern(S); a = np.full(len(snr), "E", dtype=object)
    for p, r in rule.items():
        m = pat == p
        if r["undef"] is not None: a[m & ~ok] = r["undef"]
        if r["t"] is not None:
            td, ta = r["t"]; mm = m & ok
            a[mm & (snr < td)] = "D"; a[mm & (snr >= ta)] = "A"
    return a


def frozen_thresholds():
    """SNR at which each frozen rule dismisses (below) / alerts (at or above), per rank-specific state combination."""
    import itertools
    g = np.arange(0, 40.01, 0.1); out = {}
    for combo in itertools.product(["YES", "NO", "MISSING"], repeat=3):
        S = [np.array([c] * len(g), object) for c in combo]; act = v2.policies(S, g, np.ones(len(g), bool))
        rec = {}
        for p in ("CG", "CG_c05", "CG-D", "P3"):
            a = act[p]; d = g[a == "D"]; al = g[a == "A"]
            rec[p] = {"dismiss_below": round(float(d.max() + 0.1), 1) if len(d) else None, "alert_from": round(float(al.min()), 1) if len(al) else None}
        out["/".join(c[0] for c in combo)] = rec
    return out


def costopt(rows, F=0.0, ks=KS, fname="costopt_thresholds.json", extra=None):
    trn = {k: v for k, v in rows.items() if k in A_NETS}; tst = {k: v for k, v in rows.items() if k in B_NETS}
    days_t = sum(v["calendar_days"] for v in tst.values())
    res = {"plan": "PLAN_REVIEW3_2026-11-08.md (23c1cd8)", "machine": "laptop", "cost_minutes": {"escalation": C_E, "alert": C_A},
           "training_networks": sorted(trn), "test_networks": len(tst), "test_network_days": days_t, "by_k": {}}
    pats = sorted({p for v in trn.values() for p in counts_pattern(v["S"])} | {p for v in tst.values() for p in counts_pattern(v["S"])})
    cat = lambda D, f: np.concatenate([f(v) for v in D.values()])
    TP = cat(trn, lambda v: counts_pattern(v["S"])); TS = cat(trn, lambda v: v["snr"]); TO = cat(trn, lambda v: v["ok"]); TA = cat(trn, lambda v: v["assoc"])
    fz = frozen_thresholds(); res["frozen_thresholds_by_state_combo"] = fz
    if extra: res.update(extra)
    res["false_alert_cost_minutes"] = F
    for k in ks:
        rule = {}
        for p in pats:
            m = TP == p; r = {"n_train": int(m.sum()), "undef": None, "t": None}
            if (m & TO).sum() >= 30: r["t"] = fit_pattern(TS[m & TO], TA[m & TO], k, F)
            mu = m & ~TO
            if mu.sum():
                costs = {"D": k * TA[mu].sum(), "E": C_E * mu.sum(), "A": C_A * mu.sum() + F * (~TA[mu]).sum()}; r["undef"] = min(costs, key=costs.get)
            rule[p] = r
        pol = ("OPT", "CG", "CG_c05", "CG-D", "P3", "P3_2t", "P1t")
        tot = {p: 0.0 for p in pol}; dis = {p: 0 for p in pol}; perday = {}
        for n, v in tst.items():
            act = dict(v["act"]); act["OPT"] = apply_opt(rule, v["S"], v["snr"], v["ok"])
            for p in pol:
                c = ep_cost(act[p], v["assoc"], k, F); tot[p] += c.sum(); dis[p] += int(((act[p] == "D") & v["assoc"]).sum())
            dd = pd.Series(ep_cost(act["CG_c05"], v["assoc"], k, F) - ep_cost(act["OPT"], v["assoc"], k, F)).groupby(v["days"]).sum()
            perday[n] = np.concatenate([dd.to_numpy(), np.zeros(max(v["calendar_days"] - len(dd), 0))])
        rng = np.random.default_rng(SEED); names = sorted(perday); bs = []
        for _ in range(1000):
            num = den = 0.0
            for n in rng.choice(names, len(names)):
                x = perday[n]; s = rng.choice(x, len(x)); num += s.sum(); den += len(x)
            bs.append(num / den)
        res["by_k"][str(k)] = {"rule": {p: {"t_D_t_A": r["t"], "undefined_snr_action": r["undef"], "n_train": r["n_train"]} for p, r in rule.items()},
                               "test_cost_per_network_day": {p: round(tot[p] / days_t, 2) for p in pol},
                               "test_dismissed_reviewed_associated": dis,
                               "CG_c05_minus_OPT_per_network_day": {"diff": round((tot["CG_c05"] - tot["OPT"]) / days_t, 2),
                                                                    "ci95": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]},
                               "excess_over_OPT_pct": {p: round(100 * (tot[p] / tot["OPT"] - 1), 1) for p in pol}}
        # distance of frozen dismissal thresholds from the optimum, for patterns with trained thresholds
        dist = {}
        for p, r in rule.items():
            if r["t"] is None: continue
            combos = [c for c in fz if f"{c.count('Y')}{c.count('N')}{c.count('M')}" == p]
            dist[p] = {"opt_t_D": r["t"][0], "opt_t_A": r["t"][1],
                       **{q: {"t_D_range": sorted({fz[c][q]["dismiss_below"] for c in combos if fz[c][q]["dismiss_below"] is not None}),
                              "t_A_range": sorted({fz[c][q]["alert_from"] for c in combos if fz[c][q]["alert_from"] is not None})}
                          for q in ("CG", "CG_c05", "CG-D", "P3")}}
        res["by_k"][str(k)]["thresholds_vs_frozen"] = dist
    jdump(res, fname); return res


# ------------------------------------------------------------------ 3. Draelos-style screen
SBINS = [-1e9, 5, 10, 15, 20, 1e9]


def cells(v):
    st = np.array(["/".join(x[0] for x in t) for t in zip(*v["S"])], object)
    b = np.where(v["ok"], pd.cut(v["snr"], SBINS, labels=False).astype(float), -1)
    return np.array([f"{s}|{int(x)}" for s, x in zip(st, b)], object)


def screen_actions(v, low, high):
    c = cells(v); yes = np.zeros(len(c), bool)
    for s in v["S"]: yes |= s == "YES"
    a = np.full(len(c), "E", dtype=object)
    a[np.isin(c, list(low))] = "D"; a[np.isin(c, list(high)) & yes] = "A"; return a


def draelos(rows):
    trn = {k: v for k, v in rows.items() if k in A_NETS}; tst = {k: v for k, v in rows.items() if k in B_NETS}
    tc = np.concatenate([cells(v) for v in trn.values()]); ta = np.concatenate([v["assoc"] for v in trn.values()])
    st = pd.DataFrame({"c": tc, "a": ta}).groupby("c").a.agg(["mean", "count"])
    esc_c05 = sum(int((v["act"]["CG_c05"] == "E").sum()) for v in trn.values())
    grid = []
    for rl in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05):
        for rh in (0.05, 0.1, 0.2, 0.3, 0.5):
            if rh <= rl: continue
            low = set(st.index[(st["mean"] <= rl) & (st["count"] >= 30)]); high = set(st.index[st["mean"] >= rh])
            E = D = 0
            for v in trn.values():
                a = screen_actions(v, low, high); E += int((a == "E").sum()); D += int(((a == "D") & v["assoc"]).sum())
            grid.append({"r_lo": rl, "r_hi": rh, "train_escalations": E, "train_dismissed_assoc": D})
    ok = [g for g in grid if abs(g["train_escalations"] - esc_c05) <= 0.10 * esc_c05]
    choice = min(ok, key=lambda g: g["train_dismissed_assoc"]) if ok else min(grid, key=lambda g: abs(g["train_escalations"] - esc_c05))
    low = set(st.index[(st["mean"] <= choice["r_lo"]) & (st["count"] >= 30)]); high = set(st.index[st["mean"] >= choice["r_hi"]])
    data = {}; tot = {}
    for n, v in tst.items():
        act = {p: v["act"][p] for p in ("CG_c05", "CG-D", "P3", "P3_2t")}; act["SCREEN"] = screen_actions(v, low, high)
        data[n] = (v["days"], v["assoc"], act)
        for p, a in act.items():
            t = tot.setdefault(p, {"dismissed_reviewed_associated": 0, "unassociated_alerts": 0, "escalations": 0})
            t["dismissed_reviewed_associated"] += int(((a == "D") & v["assoc"]).sum()); t["unassociated_alerts"] += int(((a == "A") & ~v["assoc"]).sum())
            t["escalations"] += int((a == "E").sum())
    res = {"plan": "PLAN_REVIEW3_2026-11-08.md (23c1cd8)", "machine": "laptop", "training_networks": sorted(trn),
           "training_cells": int(len(st)), "training_CG_c05_escalations": esc_c05, "grid": grid, "chosen": choice,
           "within_10pct_budget": bool(ok), "dismiss_cells": sorted(low), "alert_cells_with_yes": len(high),
           "test_networks": len(tst), "test_totals": tot,
           "SCREEN_minus_CG_c05": v2.cluster_boot(data, "SCREEN", "CG_c05"),
           "SCREEN_minus_P3": v2.cluster_boot(data, "SCREEN", "P3"),
           "CG_c05_minus_P3_same_test": v2.cluster_boot(data, "CG_c05", "P3")}
    jdump(res, "draelos_screen.json"); return res


if __name__ == "__main__":
    which = sys.argv[1:] or ["detprob", "costopt", "draelos"]
    rows = reviewed_rows() if ({"costopt", "draelos", "costopt_fa"} & set(which)) else None
    if "detprob" in which:
        r = detprob(); print("DETPROB", json.dumps({k: r[k] for k in ("training", "test", "brier", "ece", "agreement_with_ctx", "by_magnitude_bin")}, indent=1))
    if "costopt" in which:
        r = costopt(rows)
        for k, v in r["by_k"].items(): print("COST k=", k, v["test_cost_per_network_day"], v["excess_over_OPT_pct"], v["CG_c05_minus_OPT_per_network_day"], v["test_dismissed_reviewed_associated"])
    if "costopt_fa" in which:
        ex = {"status": "EXPLORATORY, not in the plan: adds a cost F for an automatic alert without a reviewed event (k = 60)"}
        for F in (5.0, 15.0, 30.0):
            r = costopt(rows, F=F, ks=(60,), fname=f"costopt_falsealert_F{int(F)}.json", extra=ex)
            v = r["by_k"]["60"]; print("FA F=", F, v["test_cost_per_network_day"], v["excess_over_OPT_pct"], v["test_dismissed_reviewed_associated"])
    if "draelos" in which:
        r = draelos(rows); print("SCREEN", json.dumps({k: r[k] for k in ("chosen", "within_10pct_budget", "test_totals", "SCREEN_minus_CG_c05", "SCREEN_minus_P3")}, indent=1))
