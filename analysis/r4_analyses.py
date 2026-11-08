"""Analyses requested in internal review round R4 (07.11.2026).
 A  matched-budget frontier with symmetric flexibility: P3 and P2 get separate alert and dismissal SNR thresholds
    (tau_A >= tau_D), CG gets (theta_D, theta_A); P1t one threshold. Grid limits and winning parameters reported.
 B  common-threshold P2 vs P3 (tau 6..14 dB) and a 2x2 factorial for CG: evidence gate on/off x data-quality factor on/off;
    binary-SNR variant at several thresholds.
 C  masking: full paired transition tables (all and associated) for every policy and mask -> masking_transitions.csv
 D  time-shift control: distribution of matches over the 22 shifts.
 E  extended test E3 under moving-block day bootstrap with block lengths 1, 3, 7, 14 days (sensitivity, not the
    pre-registered analysis).
 F  full action x association x detector-score cross-tabs for EQTransformer and PhaseNet, development and held-out.
Output: results/r4/*.json, *.csv
"""
import os, json, glob, importlib.util
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "r4"); os.makedirs(OUT, exist_ok=True)
NB = ["MK31", "KURK", "WUS"]; W0 = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}

def load(per):
    ep = pd.read_csv(os.path.join(root, "results", per, "episodes.csv")); ep["day"] = ep.t_on_utc.str[:10]
    av = pd.read_csv(os.path.join(root, "results", per, "availability.csv")).set_index("day")
    mk = [c for c in av.columns if c.startswith("MK31")][0]
    ep["regime"] = ep.day.map(lambda d: "normal" if av.loc[d, mk] >= 0.9 else ("outage" if av.loc[d, mk] < 0.1 else "partial"))
    return ep, len(av)

def parts(ep, mask=()):
    S = {k: ep[f"n_{k}"].astype(str).to_numpy().copy() for k in NB}
    for k in mask: S[k][:] = "MISSING"
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    return S, yes, no, ep.snr_db.fillna(0).to_numpy(), ep.snr_db.notna().to_numpy()

def crisp(yes, no, snr, ok, tA, tD, need_no):
    a = np.full(len(snr), "ESCALATE", dtype=object)
    a[yes & ok & (snr >= tA)] = "ALERT"
    d = (~yes) & ok & (snr < tD)
    if need_no: d &= no
    a[d] = "DISMISS"; return a

def cg(S, snr, ok, thD=0.16, thA=0.60, delta=0.45, use_q=True, snr_bin=None, W=W0):
    num = np.zeros(len(snr)); den = np.zeros(len(snr))
    for k in NB:
        s = (S[k] == "YES").astype(float); q = np.isin(S[k], ["YES", "NO"]).astype(float) if use_q else np.ones(len(snr))
        num += W[k] * s * q; den += W[k] * q
    s4 = (ok & (snr >= snr_bin)).astype(float) if snr_bin is not None else np.clip(np.where(ok, snr, 0) / 30.0, 0, 1)
    num += W["SNR"] * s4 * ok; den += W["SNR"] * ok
    d = den >= delta; D = np.where(d, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(len(snr), "ESCALATE", dtype=object); a[d & (D >= thA)] = "ALERT"; a[d & (D <= thD)] = "DISMISS"; return a

def summ(a, assoc, nd):
    return {"missed": int(((a == "DISMISS") & assoc).sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
            "escalate": int((a == "ESCALATE").sum()), "esc_per_day": round(float((a == "ESCALATE").sum()) / nd, 2)}

ep, nd = load("stage1_v3"); assoc = (ep.assoc_event >= 0).to_numpy(); S, yes, no, snr, ok = parts(ep)
res = {}
# A frontier, symmetric flexibility
taus = np.arange(0, 30.5, 1.0); rows = []
for tA in taus:
    for tD in taus:
        if tD > tA: continue
        for n, need in [("P3", False), ("P2", True)]:
            rows.append({"policy": n, "p1": tA, "p2": tD, **summ(crisp(yes, no, snr, ok, tA, tD, need), assoc, nd)})
for t in np.arange(0, 30.5, 0.5):
    a = np.where(yes | (ok & (snr >= t)), "ALERT", "DISMISS").astype(object); rows.append({"policy": "P1t", "p1": t, "p2": t, **summ(a, assoc, nd)})
for thD in np.round(np.arange(0, 0.61, 0.02), 2):
    for thA in np.round(np.arange(0.30, 1.001, 0.05), 2):
        if thA <= thD: continue
        rows.append({"policy": "CG", "p1": thA, "p2": thD, **summ(cg(S, snr, ok, thD=thD, thA=thA), assoc, nd)})
F = pd.DataFrame(rows); F.to_csv(os.path.join(OUT, "frontier_symmetric.csv"), index=False)
best = {}
for mx in [5, 7]:
    for b in [0.0, 2.0, 3.0, 4.0, 5.0, 6.0]:
        cell = {}
        for n in ["P1t", "P3", "P2", "CG"]:
            g = F[(F.policy == n) & (F.missed <= mx) & (F.esc_per_day <= b)]
            if g.empty: cell[n] = None
            else:
                r = g.sort_values(["alert_unassoc", "esc_per_day"]).iloc[0]
                cell[n] = {"alert_unassoc": int(r.alert_unassoc), "esc_per_day": float(r.esc_per_day), "missed": int(r.missed), "param_alert": float(r.p1), "param_dismiss": float(r.p2)}
        best[f"missed<={mx}, esc/day<={b}"] = cell
res["A_frontier"] = {"grid": {"P3/P2 tau_A, tau_D": "0..30 dB step 1, tau_D <= tau_A", "P1t tau": "0..30 dB step 0.5",
                              "CG theta_D": "0..0.60 step 0.02", "CG theta_A": "0.30..1.00 step 0.05"}, "best": best}
# B common threshold P2 vs P3; factorial; binary SNR
res["B_common_tau"] = {f"tau={t}": {"P3": summ(crisp(yes, no, snr, ok, t, t, False), assoc, nd), "P2": summ(crisp(yes, no, snr, ok, t, t, True), assoc, nd)} for t in [6, 7.5, 8, 10, 10.5, 12, 14]}
reg = ep.regime.to_numpy()
fact = {}
for gate in [True, False]:
    for q in [True, False]:
        a = cg(S, snr, ok, delta=0.45 if gate else 0.0, use_q=q)
        fact[f"gate={'on' if gate else 'off'}, quality_factor={'on' if q else 'off'}"] = {**summ(a, assoc, nd), "outage_missed": int(((a == "DISMISS") & assoc & (reg == "outage")).sum())}
res["B_factorial_gate_x_quality"] = fact
res["B_binary_snr"] = {f"{t} dB": summ(cg(S, snr, ok, snr_bin=t), assoc, nd) for t in [6, 8, 10, 12, 15, 20]}
# C masking transitions
trs = []
nm = reg == "normal"
for mask in [(), ("MK31",), ("KURK",), tuple(NB)]:
    Sm, ym, nm_, _, _ = parts(ep, mask)
    for n in ["P1", "P1t", "P3", "P2", "CG"]:
        base_S, by, bn = S, yes, no
        def act(Sx, yx, nx):
            if n == "P1": return np.where(yx, "ALERT", "DISMISS").astype(object)
            if n == "P1t": return np.where(yx | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)
            if n == "P3": return crisp(yx, nx, snr, ok, 7.5, 7.5, False)
            if n == "P2": return crisp(yx, nx, snr, ok, 10.5, 10.5, True)
            return cg(Sx, snr, ok)
        a0 = act(S, yes, no)[nm]; a1 = act(Sm, ym, nm_)[nm]; asc = assoc[nm]
        for f in ["ALERT", "ESCALATE", "DISMISS"]:
            for t in ["ALERT", "ESCALATE", "DISMISS"]:
                trs.append({"mask": "+".join(mask) or "none", "policy": n, "from": f, "to": t,
                            "all": int(((a0 == f) & (a1 == t)).sum()), "associated": int(((a0 == f) & (a1 == t) & asc).sum())})
pd.DataFrame(trs).to_csv(os.path.join(OUT, "masking_transitions.csv"), index=False)
T = pd.DataFrame(trs); ch = T[(T["from"] != T["to"])].groupby(["mask", "policy"])[["all", "associated"]].sum()
res["C_masking_changed_actions"] = {f"{m}|{p}": {"changed": int(r["all"]), "changed_associated": int(r["associated"])} for (m, p), r in ch.iterrows()}
newd = T[(T["to"] == "DISMISS") & (T["from"] != "DISMISS")].groupby(["mask", "policy"])["associated"].sum()
res["C_masking_new_associated_dismissals"] = {f"{m}|{p}": int(v) for (m, p), v in newd.items()}
# D shift distribution
r3 = json.load(open(os.path.join(root, "results", "r3", "r3_analyses.json")))["E_association"]
ps = np.array(r3["per_shift"]); res["D_shift_distribution"] = {"n_shifts": len(ps), "min": int(ps.min()), "median": float(np.median(ps)), "max": int(ps.max()),
                                                              "mean": round(float(ps.mean()), 2), "ratio_to_real_percent": round(float(ps.mean()) / r3["associated_episodes_real"] * 100, 2)}
# E block bootstrap for E3
E = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
frames = []
for c in E["chunks"]:
    d = os.path.join(root, c["source"]); x = pd.read_csv(os.path.join(d, "episodes.csv")); x["day"] = x.t_on_utc.str[:10]; frames.append(x)
X = pd.concat(frames, ignore_index=True); xa = (X.assoc_event >= 0).to_numpy(); xS, xy, xn, xs, xo = parts(X)
a_cg = cg(xS, xs, xo); a_p3 = crisp(xy, xn, xs, xo, 7.5, 7.5, False)
days = np.array(sorted(X.day.unique())); di = {d: i for i, d in enumerate(days)}; dix = X.day.map(di).to_numpy()
per_day = [(np.flatnonzero((dix == i) & xa)) for i in range(len(days))]
rng = np.random.default_rng(7); blk = {}
for L in [1, 3, 7, 14]:
    vals = []
    for _ in range(2000):
        starts = rng.integers(0, len(days) - L + 1, size=int(np.ceil(len(days) / L)))
        ids = np.concatenate([per_day[s + j] for s in starts for j in range(L)])[: None]
        if len(ids): vals.append(((a_cg[ids] == "DISMISS").mean() - (a_p3[ids] == "DISMISS").mean()) * 100)
    blk[f"block={L}d"] = [round(float(np.percentile(vals, 2.5)), 2), round(float(np.percentile(vals, 97.5)), 2)]
res["E_E3_block_bootstrap_ci95_pp"] = {"observed_pp": round(float(((a_cg[xa] == "DISMISS").mean() - (a_p3[xa] == "DISMISS").mean()) * 100), 2), **blk}
# F full cross-tabs EQT / PhaseNet
eq = pd.read_csv(os.path.join(root, "results", "eqt", "eqt_episodes.csv")); pn = pd.read_csv(os.path.join(root, "results", "phasenet", "phasenet_episodes.csv"))
xt = []
for tag, led in [("dev", "dm_ledger_dev.csv"), ("heldout", "dm_ledger_heldout.csv")]:
    Lg = pd.read_csv(os.path.join(root, "results", "criteria_governed", led))
    Lg["eqt_det_ge_0.5"] = eq[eq.set == tag].det.values >= 0.5; Lg["phasenet_P_ge_0.3"] = pn[pn.set == tag].p.values >= 0.3
    g = Lg.groupby(["assoc", "action"]).agg(n=("action", "size"), eqt=("eqt_det_ge_0.5", "sum"), phasenet=("phasenet_P_ge_0.3", "sum")).reset_index()
    g.insert(0, "period", tag); xt.append(g)
XT = pd.concat(xt); XT.to_csv(os.path.join(OUT, "detector_crosstabs.csv"), index=False)
res["F_detector_crosstabs"] = XT.to_dict("records")
json.dump(res, open(os.path.join(OUT, "r4_analyses.json"), "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k not in ("F_detector_crosstabs", "C_masking_changed_actions")}, indent=1, default=float)[:7000])
print("masking changed:", res["C_masking_changed_actions"])
