"""Evaluation of the criteria-governed model (CG, code/08) against P1, P1t, P2, P3 for the manuscript.
- development: per regime (all / normal / outage), 5-block contiguous CV for every tuned threshold
- paired day bootstrap (2000, seed 7) of CG minus each baseline: missed associated, unassociated automatic ALERTs
- held-out (exploratory for CG and P3): frozen thresholds = median of the development CV folds
- sensitivity of CG to its fixed design parameters (weights, delta, SNR_FULL, theta_A): grid, development period
Output: results/dissertation_model/cg_evaluation.json
"""
import os, json, itertools, importlib.util
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("dm", os.path.join(root, "code", "08_dissertation_model.py"))
OUT = os.path.join(root, "results", "criteria_governed")

def load(path, av_path=None):
    ep = pd.read_csv(path); ep["day"] = ep.t_on_utc.str[:10]
    if "regime" not in ep.columns:
        av = pd.read_csv(av_path).set_index("day"); mk = [c for c in av.columns if c.startswith("MK31")][0]
        ep["regime"] = ep.day.map(lambda d: "normal" if av.loc[d, mk] >= 0.9 else ("outage" if av.loc[d, mk] < 0.1 else "partial"))
    return ep

def parts(ep):
    yes = ep[[f"n_{k}" for k in ["MK31", "KURK", "WUS"]]].eq("YES").any(axis=1).to_numpy()
    no = ep[[f"n_{k}" for k in ["MK31", "KURK", "WUS"]]].eq("NO").any(axis=1).to_numpy()
    ok = ep.snr_db.notna().to_numpy(); snr = ep.snr_db.fillna(0).to_numpy()
    return yes, no, ok, snr

def make_pols(ep, P):
    yes, no, ok, snr = parts(ep)
    def P1(t): return np.where(yes, "ALERT", "DISMISS").astype(object)
    def P1t(t): return np.where(yes | (ok & (snr >= t)), "ALERT", "DISMISS").astype(object)
    def P2(t):
        a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"; a[(~yes) & no & ok & (snr < t)] = "DISMISS"; return a
    def P3(t):
        a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"; a[(~yes) & ok & (snr < t)] = "DISMISS"; return a
    S, Q, den, D, defined, weff = model_p(ep, P)
    def CG(t):
        assert t < P["THETA_A"], "theta_D must be < theta_A"
        a = np.full(len(ep), "ESCALATE", dtype=object); a[defined & (D >= P["THETA_A"])] = "ALERT"; a[defined & (D <= t)] = "DISMISS"; return a
    return {"P1": (P1, None), "P1t": (P1t, np.arange(0, 30.5, 0.5)), "P2": (P2, np.arange(0, 30.5, 0.5)),
            "P3": (P3, np.arange(0, 30.5, 0.5)), "CG": (CG, np.round(np.arange(0, P["THETA_A"] - 0.005, 0.01), 2))}   # theta_D < theta_A of this configuration, strictly

def model_p(ep, P):
    W = P["W"]; S = {}; Q = {}
    for k in ["MK31", "KURK", "WUS"]:
        st = ep[f"n_{k}"].astype(str).to_numpy(); S[k] = (st == "YES").astype(float); Q[k] = np.isin(st, ["YES", "NO"]).astype(float)
    S["SNR"] = np.clip(ep.snr_db.fillna(0).to_numpy() / P["SNR_FULL"], 0, 1); Q["SNR"] = ep.snr_db.notna().to_numpy().astype(float)
    den = sum(W[k] * Q[k] for k in W); num = sum(W[k] * S[k] * Q[k] for k in W)
    defined = den >= P["DELTA"]; D = np.where(defined, num / np.where(den > 0, den, 1), np.nan)
    return S, Q, den, D, defined, None

def pick(f, cands, assoc, rows):
    best = float(cands[0]); m = assoc & rows; ok_any = False
    for t in cands:
        if (f(t)[m] != "DISMISS").mean() >= 0.95: best = float(t); ok_any = True
    if not ok_any: INFEASIBLE.append(float(cands[0]))
    return best
INFEASIBLE = []

def cv(ep, P):
    assoc = (ep.assoc_event >= 0).to_numpy(); pols = make_pols(ep, P)
    days = np.array(sorted(ep.day.unique())); blocks = np.array_split(days, 5)
    blk = ep.day.map({d: i for i, b in enumerate(blocks) for d in b}).to_numpy()
    acts, th = {}, {}
    for n, (f, c) in pols.items():
        a = np.empty(len(ep), dtype=object); th[n] = []
        for k in range(5):
            t = 0.0 if c is None else pick(f, c, assoc, blk != k); th[n].append(t); a[blk == k] = f(t)[blk == k]
        acts[n] = a
    return acts, th, assoc

def summ(a, assoc, days):
    nd = len(set(days)); n_as = int(assoc.sum())
    return {"assoc": n_as, "missed": int(((a == "DISMISS") & assoc).sum()),
            "alert": int((a == "ALERT").sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
            "escalate": int((a == "ESCALATE").sum()), "esc_per_day": round(float((a == "ESCALATE").sum()) / max(nd, 1), 2),
            "dismiss": int((a == "DISMISS").sum()), "automation_share": round(float((a != "ESCALATE").mean()), 3),
            "assoc_escalated": int(((a == "ESCALATE") & assoc).sum())}

def paired(acts, assoc, days, A, B, n=2000, seed=7):
    rng = np.random.default_rng(seed); u = np.array(sorted(set(days))); idx = {d: np.where(days == d)[0] for d in u}
    def st(a, ids): return np.array([((a[ids] == "DISMISS") & assoc[ids]).sum(), ((a[ids] == "ALERT") & ~assoc[ids]).sum()])
    out = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(u, len(u))]); out.append(st(acts[A], ids) - st(acts[B], ids))
    out = np.array(out); obs = st(acts[A], np.arange(len(days))) - st(acts[B], np.arange(len(days)))
    return {"missed_diff": int(obs[0]), "missed_ci95": [float(np.percentile(out[:, 0], 2.5)), float(np.percentile(out[:, 0], 97.5))],
            "unassoc_alert_diff": int(obs[1]), "unassoc_alert_ci95": [float(np.percentile(out[:, 1], 2.5)), float(np.percentile(out[:, 1], 97.5))]}

BASE = {"W": {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}, "DELTA": 0.45, "SNR_FULL": 30.0, "THETA_A": 0.60}
dev = load(os.path.join(root, "results", "stage1_v3", "episodes.csv"), os.path.join(root, "results", "stage1_v3", "availability.csv"))
acts, th, assoc = cv(dev, BASE); days = dev.day.to_numpy(); reg = dev.regime.to_numpy()
res = {"params": BASE, "cv_thresholds": th, "development": {}, "paired_development": {}}
for n, a in acts.items():
    res["development"][n] = {r: summ(a[(reg == r) if r != "all" else slice(None)], assoc[(reg == r) if r != "all" else slice(None)],
                                     days[(reg == r) if r != "all" else slice(None)]) for r in ["all", "normal", "outage"]}
for B in ["P1", "P1t", "P2", "P3"]:
    res["paired_development"][f"CG-{B}"] = paired(acts, assoc, days, "CG", B)

ho = load(os.path.join(root, "results", "heldout", "episodes_policies.csv"))
hp = make_pols(ho, BASE); ha = (ho.assoc_event >= 0).to_numpy(); hacts = {}
for n, (f, c) in hp.items():
    t = 0.0 if c is None else float(np.median(th[n])); hacts[n] = f(t)
res["heldout"] = {n: dict(summ(a, ha, ho.day.to_numpy()), threshold=(None if hp[n][1] is None else float(np.median(th[n]))))
                  for n, a in hacts.items()}
res["heldout_note"] = "P1, P1t, P2 frozen in PREREGISTRATION.md (P1t 8.0 dB, P2 10.5 dB there); here thresholds = median of contiguous-block CV folds; CG and P3 exploratory"
res["SUPERSEDED"] = "The held-out section of this file uses fold-median thresholds and 36 episode dates; it is superseded for Table 6 by results/heldout + code/11-style frozen scoring (P1t 8.0, P2 10.5, P3 7.5, CG 0.16/0.60, 37 calendar days). Development sections (Tables 4, 5, Section 4.3) are authoritative."
res["infeasible_folds"] = INFEASIBLE
res["paired_heldout"] = {f"CG-{B}": paired(hacts, ha, ho.day.to_numpy(), "CG", B) for B in ["P1", "P1t", "P2", "P3"]}

# sensitivity of CG to its fixed design parameters
grid = []
for wsnr, delta, full, ta in itertools.product([0.30, 0.35, 0.40], [None], [20.0, 30.0, 40.0], [0.5, 0.6, 0.7]):
    rest = 1 - wsnr; W = {"MK31": rest * 0.25 / 0.6, "KURK": rest * 0.20 / 0.6, "WUS": rest * 0.15 / 0.6, "SNR": wsnr}
    for d in [wsnr + 0.05, wsnr + 0.15]:
        P = {"W": W, "DELTA": d, "SNR_FULL": full, "THETA_A": ta}
        a, _, s_assoc = cv(dev, P); s = summ(a["CG"], s_assoc, days)
        grid.append({"w_snr": wsnr, "delta": round(d, 2), "snr_full": full, "theta_A": ta, **{k: s[k] for k in ["missed", "alert_unassoc", "esc_per_day"]}})
g = pd.DataFrame(grid)
res["sensitivity"] = {"configs": len(g), "missed_range": [int(g.missed.min()), int(g.missed.max())],
                      "alert_unassoc_range": [int(g.alert_unassoc.min()), int(g.alert_unassoc.max())],
                      "esc_per_day_range": [float(g.esc_per_day.min()), float(g.esc_per_day.max())],
                      "share_configs_fewer_unassoc_alerts_than_P3": round(float((g.alert_unassoc < res["development"]["P3"]["all"]["alert_unassoc"]).mean()), 3),
                      "share_configs_missed_le_P1t": round(float((g.missed <= res["development"]["P1t"]["all"]["missed"]).mean()), 3)}
g.to_csv(os.path.join(OUT, "cg_sensitivity.csv"), index=False)
json.dump(res, open(os.path.join(OUT, "cg_evaluation.json"), "w"), indent=1)
for n in acts:
    for r in ["all", "normal", "outage"]:
        s = res["development"][n][r]; print(f"{n:4s} {r:6s} missed {s['missed']:2d}/{s['assoc']:3d} alertU {s['alert_unassoc']:4d} esc/d {s['esc_per_day']:5.2f} auto {s['automation_share']}")
print("thresholds", th)
for k, v in res["paired_development"].items(): print("dev", k, v)
for n, s in res["heldout"].items(): print("HO", n, s)
for k, v in res["paired_heldout"].items(): print("HO", k, v)
print("sensitivity", res["sensitivity"])
