"""Scoring of PREREGISTRATION_BLAST.md (commit 3f77906): blast / earthquake / escalate with the criteria-governed model.
Development: NNC events before 2025-07-01; test: 2025-07-01..2026-02-28. Labels: NNC event type (agency judgement).
s_i = empirical CDF (development, pooled) of the feature oriented so that high = explosion-like (orientation by development
AUC); q_i from the window quality flags; D(x) = sum w s q / sum w q if sum w q >= 0.45 else undefined (escalate).
Thresholds: BLAST if D >= th_B, EARTHQUAKE if D <= th_E, chosen on development as the widest pair with precision >= 0.90
for each automatic class. Baseline: single best development feature, same procedure; matched-coverage comparison on test.
Output: results/blast/blast_eval.json
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(root, "results", "blast")
f = pd.read_csv(os.path.join(B, "features.csv"))
f["blast"] = (f.type == "mining explosion").astype(int)
f["hour_local"] = ((pd.to_datetime(f.time, unit="s").dt.hour + 5) % 24)
f["f3_daytime"] = f.hour_local.between(8, 17).astype(float); f["q_f3"] = 1
dev = (f.time < pd.Timestamp("2025-07-01", tz="UTC").timestamp()).to_numpy(); test = ~dev
def auc(x, y):
    m = np.isfinite(x); x, y = x[m], y[m]; r = pd.Series(x).rank().to_numpy(); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else np.nan
feats = {"f1": ("f1_spec_ratio", "q_f1"), "f2": ("f2_p_s_ratio", "q_f2"), "f3": ("f3_daytime", "q_f3")}
S, Q, info = {}, {}, {}
for k, (c, qc) in feats.items():
    x = f[c].to_numpy(dtype=float); q = (f[qc].fillna(0).to_numpy() == 1) & np.isfinite(x)
    a = auc(x[dev & q], f.blast.to_numpy()[dev & q]); sign = 1 if a >= 0.5 else -1
    ref = np.sort(sign * x[dev & q]); s = np.searchsorted(ref, sign * np.nan_to_num(x), side="right") / max(len(ref), 1)
    S[k], Q[k] = np.where(q, s, 0.0), q.astype(float)
    info[k] = {"dev_auc_raw": round(a, 3), "orientation": sign, "valid_dev": int((dev & q).sum()), "valid_test": int((test & q).sum()),
               "test_auc_oriented": round(auc(sign * x[test & q], f.blast.to_numpy()[test & q]), 3)}
def D_of(W):
    num = sum(W[k] * S[k] * Q[k] for k in W); den = sum(W[k] * Q[k] for k in W)
    return np.where(den >= 0.45, num / np.where(den > 0, den, 1), np.nan)
y = f.blast.to_numpy()
def fit(D):
    grid = np.round(np.arange(0, 1.0001, 0.01), 2); best = None
    for tB in grid:
        mb = dev & (D >= tB)
        if mb.sum() < 5 or y[mb].mean() < 0.90: continue
        for tE in grid[grid < tB]:
            me = dev & (D <= tE)
            if me.sum() < 5 or (1 - y[me]).mean() < 0.90: continue
            cov = (mb | me).sum()
            if best is None or cov > best[2]: best = (float(tB), float(tE), int(cov))
    return best
def evaluate(D, th, m):
    tB, tE = th[:2]; act = np.full(len(D), "ESCALATE", dtype=object); f_ = np.isfinite(D)
    act[f_ & (D >= tB)] = "BLAST"; act[f_ & (D <= tE)] = "EARTHQUAKE"
    auto = m & (act != "ESCALATE"); corr = auto & (((act == "BLAST") & (y == 1)) | ((act == "EARTHQUAKE") & (y == 0)))
    return act, {"n": int(m.sum()), "auto": int(auto.sum()), "escalated_share": round(1 - auto.sum() / m.sum(), 3),
                 "accuracy_auto": round(corr.sum() / max(auto.sum(), 1), 3), "blast_recall_auto": round(int(((act == "BLAST") & m & (y == 1)).sum()) / max(int((m & (y == 1)).sum()), 1), 3)}
res = {"preregistration": "PREREGISTRATION_BLAST.md, commit 3f77906", "n": int(len(f)), "dev": int(dev.sum()), "test": int(test.sum()),
       "blasts_dev": int(y[dev].sum()), "blasts_test": int(y[test].sum()), "features": info, "errors": int(f.get("err", pd.Series(dtype=str)).notna().sum())}
models = {"W (waveform only)": {"f1": 0.5, "f2": 0.5}, "WT (with time of day)": {"f1": 0.35, "f2": 0.35, "f3": 0.30}}
for nm, W in models.items():
    D = D_of(W); th = fit(D)
    if th is None: res[nm] = {"thresholds": None}; continue
    act, ev = evaluate(D, th, test); res[nm] = {"weights": W, "theta_B": th[0], "theta_E": th[1], "dev_coverage": th[2], "test": ev}
    if nm.startswith("W "): actW, DW = act, D
# baseline: best single development feature by |AUC-0.5|, matched coverage on test
bk = max(["f1", "f2"], key=lambda k: abs(info[k]["dev_auc_raw"] - 0.5))
Db = np.where(Q[bk] > 0, S[bk], np.nan)
if "theta_B" in res["W (waveform only)"]:
    na = res["W (waveform only)"]["test"]["auto"]; idx = np.flatnonzero(test & np.isfinite(Db))
    ext = idx[np.argsort(-np.abs(Db[idx] - 0.5))][:na]; pred = (Db[ext] >= 0.5).astype(int)
    res["baseline_matched_coverage"] = {"feature": bk, "auto": int(len(ext)), "accuracy_auto": round(float((pred == y[ext]).mean()), 3)}
    res["B1"] = {"W_accuracy": res["W (waveform only)"]["test"]["accuracy_auto"], "baseline_accuracy": res["baseline_matched_coverage"]["accuracy_auto"],
                 "holds": res["W (waveform only)"]["test"]["accuracy_auto"] > res["baseline_matched_coverage"]["accuracy_auto"]}
    both0 = (Q["f1"] == 0) & (Q["f2"] == 0)
    res["B2"] = {"episodes_q0_both": int(both0.sum()), "auto_decided": int((both0 & np.isin(actW, ["BLAST", "EARTHQUAKE"])).sum()),
                 "holds": bool((~np.isin(actW[both0], ["BLAST", "EARTHQUAKE"])).all())}
td = f.f3_daytime.to_numpy()[test]; res["B3_time_of_day_alone_test_accuracy"] = round(float(((td == 1) == (y[test] == 1)).mean()), 3)
json.dump(res, open(os.path.join(B, "blast_eval.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
