"""Analyses requested in internal review round R5 (07.11.2026). Exploratory unless stated; the pre-registered E3 result is unchanged.
 A  E3 under a calendar-preserving moving-block bootstrap: all calendar dates of the usable chunks (546), dates without
    episodes kept with zero counts, blocks of 1/3/7/14 days drawn uniformly from [0, N-L], concatenated, trimmed to N.
 B  association-window sensitivity on the extended test: [-10,0], [-15,0] (primary), [-20,0], [-15,+5] s around
    [t_on, t_off]; associated episodes, CG and P3 dismissals, difference, day-bootstrap 95% interval, labels changed.
 C  exact development frontier: every attainable threshold pair (unique score values) for P2, P3, CG and every SNR value
    for P1t; under miss caps 5 and 7 and escalation caps 3-6 per day: minimum unassociated alerts with the achieved
    misses, escalations per day and thresholds. In-sample, no operating point is selected.
 D  undefined SNR per study period.
 E  decision ledgers with provenance: development ledger with CV fold, fold thresholds and config id; extended-test
    ledger (18,637 rows) with criterion values, quality factors, contributions, denominator, D(x), thresholds and action;
    every stored action is reconstructed from its own row.
Output: results/r5/*
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "r5"); os.makedirs(OUT, exist_ok=True)
NB = ["MK31", "KURK", "WUS"]; W = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}; FULL, DELTA = 30.0, 0.45
CONFIG = "CG-1.0 (w 0.25/0.20/0.15/0.40, SNR full 30 dB, delta 0.45, theta_A 0.60)"

def parts(ep):
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    return S, yes, no, ep.snr_db.fillna(0).to_numpy(), ep.snr_db.notna().to_numpy()

def score(S, snr, ok):
    cols = {}; num = np.zeros(len(snr)); den = np.zeros(len(snr))
    for k in NB:
        s = (S[k] == "YES").astype(float); q = np.isin(S[k], ["YES", "NO"]).astype(float)
        cols[f"s_{k}"], cols[f"q_{k}"] = s, q; num += W[k] * s * q; den += W[k] * q
    s4 = np.clip(np.where(ok, snr, 0) / FULL, 0, 1); q4 = ok.astype(float)
    cols["s_SNR"], cols["q_SNR"] = s4, q4; num += W["SNR"] * s4 * q4; den += W["SNR"] * q4
    d = den >= DELTA; D = np.where(d, num / np.where(den > 0, den, 1), np.nan)
    for k in NB + ["SNR"]:
        cols[f"contrib_{k}"] = np.where(d, W[k] * cols[f"q_{k}"] * cols[f"s_{k}"] / np.where(den > 0, den, 1), np.nan)
    return D, den, cols

def act_cg(D, thD, thA=0.60):
    a = np.full(len(D), "ESCALATE", dtype=object); f = np.isfinite(D)
    a[f & (D >= thA)] = "ALERT"; a[f & (D <= thD)] = "DISMISS"; return a

def crisp(yes, no, snr, ok, tA, tD, need_no):
    a = np.full(len(snr), "ESCALATE", dtype=object); a[yes & ok & (snr >= tA)] = "ALERT"
    d = (~yes) & ok & (snr < tD)
    if need_no: d &= no
    a[d] = "DISMISS"; return a

res = {"config": CONFIG}
# ---------- extended data
E = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
frames, cats, cal = [], [], []
for c in E["chunks"]:
    d = os.path.join(root, c["source"]); x = pd.read_csv(os.path.join(d, "episodes.csv")); x["day"] = x.t_on_utc.str[:10]; x["chunk"] = c["chunk"]
    frames.append(x); cats.append(pd.read_csv(os.path.join(d, "catalog.csv")).assign(chunk=c["chunk"]))
    cal += pd.read_csv(os.path.join(d, "availability.csv")).day.tolist()
X = pd.concat(frames, ignore_index=True); xa = (X.assoc_event >= 0).to_numpy(); xS, xy, xn, xs, xo = parts(X)
xD, xden, xcols = score(xS, xs, xo); a_cg = act_cg(xD, 0.16); a_p3 = crisp(xy, xn, xs, xo, 7.5, 7.5, False)
cal = np.array(sorted(set(cal))); res["calendar_days"] = int(len(cal)); res["dates_with_episodes"] = int(X.day.nunique())
res["dates_without_episodes"] = sorted(set(cal) - set(X.day))
# ---------- A calendar-preserving block bootstrap
di = {d: i for i, d in enumerate(cal)}; dix = X.day.map(di).to_numpy(); N = len(cal)
per_day = [np.flatnonzero((dix == i) & xa) for i in range(N)]
rng = np.random.default_rng(7); blk = {}
for L in [1, 3, 7, 14]:
    vals = []
    for _ in range(2000):
        starts = rng.integers(0, N - L + 1, size=int(np.ceil(N / L)))
        seq = np.concatenate([np.arange(s, s + L) for s in starts])[:N]
        ids = np.concatenate([per_day[i] for i in seq])
        if len(ids): vals.append(((a_cg[ids] == "DISMISS").mean() - (a_p3[ids] == "DISMISS").mean()) * 100)
    blk[f"block={L}d"] = [round(float(np.percentile(vals, 2.5)), 2), round(float(np.percentile(vals, 97.5)), 2)]
res["A_E3_calendar_block_bootstrap_ci95_pp"] = {"observed_pp": round(float(((a_cg[xa] == "DISMISS").mean() - (a_p3[xa] == "DISMISS").mean()) * 100), 2),
                                               "margin_pp": 3.0, **blk, "note": "R4 version compressed time to 529 episode dates; kept in results/r4 as executed"}
# ---------- B association windows
def associate(lo, hi):
    lab = np.full(len(X), -1)
    for ch, g in X.groupby("chunk"):
        P = cats[[c["chunk"] for c in E["chunks"]].index(ch)].p_pred.to_numpy()
        for i, (t0, t1) in zip(g.index, zip(g.t_on, g.t_off)):
            r = P - t0; okk = np.flatnonzero((r >= lo) & (r <= (t1 - t0) + hi))
            if len(okk): lab[i] = okk[np.argmin(np.abs(r[okk]))]
    return lab >= 0
days = X.day.to_numpy(); ud = np.array(sorted(set(days)))
win = {}
prim = associate(-15, 0)
for nm, (lo, hi) in {"-10..end": (-10, 0), "-15..end (primary)": (-15, 0), "-20..end": (-20, 0), "-15..end+5": (-15, 5)}.items():
    asc = associate(lo, hi); idx = {d: np.flatnonzero((days == d) & asc) for d in ud}; r2 = np.random.default_rng(7); vals = []
    for _ in range(2000):
        ids = np.concatenate([idx[d] for d in r2.choice(ud, len(ud))])
        if len(ids): vals.append(((a_cg[ids] == "DISMISS").mean() - (a_p3[ids] == "DISMISS").mean()) * 100)
    win[nm] = {"associated": int(asc.sum()), "CG_dismissed": int(((a_cg == "DISMISS") & asc).sum()), "P3_dismissed": int(((a_p3 == "DISMISS") & asc).sum()),
               "diff_pp": round(float(((a_cg[asc] == "DISMISS").mean() - (a_p3[asc] == "DISMISS").mean()) * 100), 2),
               "ci95_pp": [round(float(np.percentile(vals, 2.5)), 2), round(float(np.percentile(vals, 97.5)), 2)],
               "labels_changed_vs_primary": int((asc != prim).sum()), "matches_stored_labels": bool((prim == xa).all()) if nm.startswith("-15..end (") else None}
res["B_association_windows_extended"] = win
# ---------- C exact development frontier
ep = pd.read_csv(os.path.join(root, "results", "stage1_v3", "episodes.csv")); ep["day"] = ep.t_on_utc.str[:10]
nd = len(pd.read_csv(os.path.join(root, "results", "stage1_v3", "availability.csv")))
assoc = (ep.assoc_event >= 0).to_numpy(); S, yes, no, snr, ok = parts(ep); D, den, cols = score(S, snr, ok); n = len(ep)
rows = []
def add(pol, p1, p2, miss, alerts, esc): rows.append((pol, p1, p2, int(miss), int(alerts), int(esc), esc / nd))
f = np.isfinite(D); ud_ = np.unique(np.concatenate([[0.0], D[f], [1.0001]]))
dis_assoc = np.array([((D <= t) & f & assoc).sum() for t in ud_]); dis_all = np.array([((D <= t) & f).sum() for t in ud_])
al_un = np.array([((D >= t) & f & ~assoc).sum() for t in ud_]); al_all = np.array([((D >= t) & f).sum() for t in ud_])
for i, tD in enumerate(ud_):
    for j in range(i + 1, len(ud_)):
        add("CG", ud_[j], tD, dis_assoc[i], al_un[j], n - dis_all[i] - al_all[j])
us = np.unique(np.concatenate([[0.0], snr[ok], [99.0]]))
for need_no, pol in [(False, "P3"), (True, "P2")]:
    dm = (~yes) & ok & (no if need_no else True); am = yes & ok
    dA = np.array([((snr < t) & dm & assoc).sum() for t in us]); dN = np.array([((snr < t) & dm).sum() for t in us])
    aU = np.array([((snr >= t) & am & ~assoc).sum() for t in us]); aN = np.array([((snr >= t) & am).sum() for t in us])
    for i, tD in enumerate(us):
        for j in range(i, len(us)):
            add(pol, us[j], tD, dA[i], aU[j], n - dN[i] - aN[j])
for t in us:
    a = np.where(yes | (ok & (snr >= t)), "ALERT", "DISMISS"); add("P1t", t, t, ((a == "DISMISS") & assoc).sum(), ((a == "ALERT") & ~assoc).sum(), 0)
F = pd.DataFrame(rows, columns=["policy", "p_alert", "p_dismiss", "missed", "alert_unassoc", "escalate", "esc_per_day"])
best = []
for mcap in [5, 7]:
    for ecap in [3, 4, 5, 6]:
        for pol in ["P1t", "P3", "P2", "CG"]:
            g = F[(F.policy == pol) & (F.missed <= mcap) & (F.esc_per_day <= ecap)]
            if len(g):
                r = g.sort_values(["alert_unassoc", "missed", "esc_per_day"]).iloc[0]
                best.append({"miss_cap": mcap, "esc_cap": ecap, "policy": pol, "alert_unassoc": int(r.alert_unassoc), "missed": int(r.missed),
                             "esc_per_day": round(float(r.esc_per_day), 2), "p_alert": repr(float(r.p_alert)), "p_dismiss": repr(float(r.p_dismiss))})   # full precision: thresholds are decision boundaries
            else:
                best.append({"miss_cap": mcap, "esc_cap": ecap, "policy": pol, "alert_unassoc": None})
# replay every exported row from its own (unrounded) thresholds by recomputing the actions directly
def replay(r):
    tA, tD = float(r["p_alert"]), float(r["p_dismiss"])
    if r["policy"] == "CG": a = act_cg(D, tD, tA)
    elif r["policy"] == "P1t": a = np.where(yes | (ok & (snr >= tA)), "ALERT", "DISMISS").astype(object)
    else: a = crisp(yes, no, snr, ok, tA, tD, r["policy"] == "P2")
    return int(((a == "DISMISS") & assoc).sum()), int(((a == "ALERT") & ~assoc).sum()), round(float((a == "ESCALATE").sum()) / nd, 2)
bad = [r for r in best if r["alert_unassoc"] is not None and replay(r) != (r["missed"], r["alert_unassoc"], r["esc_per_day"])]
res["C_frontier_replay_mismatches"] = len(bad); assert not bad, bad[:2]
pd.DataFrame(best).to_csv(os.path.join(OUT, "frontier_exact_best.csv"), index=False)
res["C_frontier_exact"] = {"configurations": F.policy.value_counts().to_dict(), "best": best}
# ---------- D undefined SNR per period
ho = pd.read_csv(os.path.join(root, "results", "heldout", "episodes.csv"))
hoa = (ho.assoc_event >= 0)
res["D_undefined_snr"] = {"development": {"episodes": int(len(ep)), "nan_snr": int(ep.snr_db.isna().sum()), "nan_snr_associated": int((ep.snr_db.isna() & (ep.assoc_event >= 0)).sum())},
                          "heldout": {"episodes": int(len(ho)), "nan_snr": int(ho.snr_db.isna().sum()), "nan_snr_associated": int((ho.snr_db.isna() & hoa).sum())},
                          "extended": {"episodes": int(len(X)), "nan_snr": int(X.snr_db.isna().sum()), "nan_snr_associated": int((X.snr_db.isna() & xa).sum()),
                                       "CG_actions_on_nan": pd.Series(a_cg[X.snr_db.isna().to_numpy()]).value_counts().to_dict()}}
# ---------- E ledgers with provenance
dd = np.array(sorted(ep.day.unique())); blocks = np.array_split(dd, 5); fold = ep.day.map({d: i for i, b in enumerate(blocks) for d in b}).to_numpy()
cv = json.load(open(os.path.join(root, "results", "criteria_governed", "cg_evaluation.json"))) if os.path.exists(os.path.join(root, "results", "criteria_governed", "cg_evaluation.json")) else None
thd_f = [0.21, 0.16, 0.16, 0.16, 0.16]
L = pd.DataFrame({"t_on_utc": ep.t_on_utc, "fold": fold, "theta_D": [thd_f[k] for k in fold], "theta_A": 0.60, "delta": DELTA, "config": CONFIG,
                  "assoc": assoc, **{k: v for k, v in cols.items()}, "den": den, "D": D})
L["action"] = [act_cg(np.array([d]), t)[0] for d, t in zip(D, L.theta_D)]
old = pd.read_csv(os.path.join(root, "results", "criteria_governed", "dm_ledger_dev.csv"))
res["E_ledgers"] = {"development_rows": int(len(L)), "development_actions_equal_stored": int((L.action.to_numpy() == old.action.to_numpy()).sum()),
                    "development_max_abs_D_diff": float(np.nanmax(np.abs(L.D.to_numpy() - old.D.to_numpy())))}
L.to_csv(os.path.join(OUT, "ledger_development_with_folds.csv"), index=False)
XL = pd.DataFrame({"t_on_utc": X.t_on_utc, "chunk": X.chunk, "theta_D": 0.16, "theta_A": 0.60, "delta": DELTA, "config": CONFIG, "assoc_primary": xa,
                   **{k: v for k, v in xcols.items()}, "den": xden, "D": xD, "action": a_cg})
rec = act_cg(XL.D.to_numpy(), 0.16); ssum = XL[[f"contrib_{k}" for k in NB + ["SNR"]]].sum(axis=1, min_count=1).to_numpy()
res["E_ledgers"].update({"extended_rows": int(len(XL)), "extended_actions_reconstructed_from_row": int((rec == XL.action.to_numpy()).sum()),
                         "extended_max_abs_sum_contrib_minus_D": float(np.nanmax(np.abs(ssum - XL.D.to_numpy())))})
XL.to_csv(os.path.join(OUT, "ledger_extended.csv.gz"), index=False, compression="gzip")
json.dump(res, open(os.path.join(OUT, "r5_analyses.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps({k: v for k, v in res.items() if k not in ("dates_without_episodes",)}, indent=1, default=str)[:6000])
