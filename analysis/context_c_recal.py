"""Recalibration of c_j(x), PLAN_CONTEXT_RECAL_2026-11-08.md (plan pushed before computing).
Frozen model of analysis/context_c.py; calibrators (Platt, isotonic) fitted on leave-one-training-set-out predictions of the
training set only; metrics and H1/H2 on T1 (26 batch-B networks, reviewed labels). Output: results/context_c/recal.json.
"""
import os, sys, json, importlib.util
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
spec = importlib.util.spec_from_file_location("ctxc", os.path.join(here, "context_c.py")); cc = importlib.util.module_from_spec(spec)
sys.modules["ctxc"] = cc; spec.loader.exec_module(cc)
v2 = cc.v2; R = cc.R; FEATS = cc.FEATS; CLIP = cc.CLIP
NB, SEED = 2000, 7
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))


def fit_lr(X, y):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - mu) / sd, y)
    return lambda Z: lr.predict_proba((Z - mu) / sd)[:, 1]


def cal_line(p, y):
    m = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000).fit(logit(p).reshape(-1, 1), y)
    return float(m.intercept_[0]), float(m.coef_[0][0])


def ece_murphy(p, y):
    b = np.clip(np.digitize(p, np.linspace(0, 1, 11)) - 1, 0, 9); n = len(p); ybar = y.mean()
    ece = rel = res = 0.0
    for i in range(10):
        m = b == i
        if m.any():
            w = m.sum() / n; ece += w * abs(p[m].mean() - y[m].mean()); rel += w * (p[m].mean() - y[m].mean()) ** 2; res += w * (y[m].mean() - ybar) ** 2
    return ece, rel, res, ybar * (1 - ybar)


def metrics(P, cols):
    out = {}
    for k in cols:
        p = P[k].to_numpy(); y = P.y.to_numpy(); a, s = cal_line(p, y); e, rl, rs, u = ece_murphy(p, y)
        out[k] = dict(brier=round(float(((p - y) ** 2).mean()), 4), mean_pred=round(float(p.mean()), 4), cal_intercept=round(a, 3),
                      cal_slope=round(s, 3), ece=round(e, 4), murphy_reliability=round(rl, 4), murphy_resolution=round(rs, 4), uncertainty=round(u, 4))
    # bootstrap intervals (networks, then days)
    nets = sorted(P.net.unique()); g = {k: {d: x.index.to_numpy() for d, x in P[P.net == k].groupby("day")} for k in nets}
    rng = np.random.default_rng(SEED); bs = {k: [] for k in cols}
    for _ in range(NB):
        ids = []
        for k in rng.choice(nets, len(nets)):
            days = list(g[k]); ids += [g[k][d] for d in rng.choice(days, len(days))]
        X = P.loc[np.concatenate(ids)]
        for k in cols:
            p = X[k].to_numpy(); y = X.y.to_numpy(); a, s = cal_line(p, y)
            bs[k].append((a, s, ((p - y) ** 2).mean() - ((X.p_ctx.to_numpy() - y) ** 2).mean()))
    for k in cols:
        v = np.array(bs[k]); q = lambda c: [round(float(np.percentile(v[:, c], 2.5)), 3), round(float(np.percentile(v[:, c], 97.5)), 3)]
        out[k].update(cal_intercept_ci95=q(0), cal_slope_ci95=q(1), brier_minus_frozen_ci95=q(2),
                      calibrated=bool(q(0)[0] <= 0 <= q(0)[1] and q(1)[0] <= 1 <= q(1)[1]))
    return out


def main():
    C = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}
    batchB = [c["network"] for c in json.load(open(os.path.join(R, "v2", "networks_batchB.json")))["networks"]]
    train = [cc.load_local("IU_dev")] + [x for x in (cc.load_v2(n, C[n]) for n in cc.TRAIN_V2) if x is not None]
    X, y, src = [], [], []
    for d in train:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        for f in d["F"]:
            m = assoc & np.isin(f.state, ["YES", "NO"]); X.append(f[FEATS].to_numpy()[m]); y.append((f.state[m] == "YES").astype(int)); src += [d["net"]] * int(m.sum())
    X = np.vstack(X); y = np.concatenate(y); src = np.array(src)
    full = fit_lr(X, y)
    oof = np.zeros(len(y))
    for s in np.unique(src):
        m = src == s; oof[m] = fit_lr(X[~m], y[~m])(X[m])
    platt = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000).fit(logit(oof).reshape(-1, 1), y)
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip", increasing=True).fit(oof, y)
    f_platt = lambda Z: platt.predict_proba(logit(full(Z)).reshape(-1, 1))[:, 1]
    f_iso = lambda Z: iso.predict(full(Z))
    a_oof, s_oof = cal_line(oof, y)
    out = {"plan": "PLAN_CONTEXT_RECAL_2026-11-08.md", "training": {"pairs": int(len(y)), "confirm_rate": round(float(y.mean()), 4),
           "oof_cal_intercept": round(a_oof, 3), "oof_cal_slope": round(s_oof, 3),
           "platt": {"a": round(float(platt.intercept_[0]), 4), "b": round(float(platt.coef_[0][0]), 4)}}}
    rev = json.load(open(os.path.join(R, "v2_reviewed", "v2_eval_reviewed.json")))["networks"]
    t1 = [x for x in (cc.load_v2(n, C[n], reviewed=True) for n in batchB if n in rev and rev[n].get("batch") == "B") if x is not None]
    data, P = {}, []
    for d in t1:
        if not rev[d["net"]].get("included_in_pooled", False): continue
        assoc = (d["ep"].assoc_event >= 0).to_numpy(); S, F, snr, ok = d["S"], d["F"], d["snr"], d["ok"]
        act = v2.policies(S, snr, ok)
        q = {"p_ctx": [np.clip(full(F[r][FEATS].to_numpy()), *CLIP) for r in range(len(S))],
             "p_platt": [np.clip(f_platt(F[r][FEATS].to_numpy()), *CLIP) for r in range(len(S))],
             "p_iso": [np.clip(f_iso(F[r][FEATS].to_numpy()), *CLIP) for r in range(len(S))]}
        act["CG-ctx"] = cc.cg_with_q(S, q["p_ctx"], snr, ok); act["CG-platt"] = cc.cg_with_q(S, q["p_platt"], snr, ok)
        act["CG-iso"] = cc.cg_with_q(S, q["p_iso"], snr, ok)
        data[d["net"]] = (d["ep"].day.to_numpy(), assoc, act)
        for r, f in enumerate(F):
            m = assoc & np.isin(f.state, ["YES", "NO"])
            P.append(pd.DataFrame({"net": d["net"], "day": d["ep"].day.to_numpy()[m], "y": (f.state[m] == "YES").astype(int),
                                   "p_ctx": q["p_ctx"][r][m], "p_platt": q["p_platt"][r][m], "p_iso": q["p_iso"][r][m],
                                   "p_tab": cc.tab_p(f, r)[m], "c05": 0.5}))
    P = pd.concat(P, ignore_index=True)
    out["T1_networks"] = len(data); out["T1_pairs"] = int(len(P))
    out["T1_calibration"] = metrics(P, ["p_ctx", "p_platt", "p_iso", "p_tab"])
    out["T1_calibration"]["c05"] = dict(brier=round(float(((0.5 - P.y) ** 2).mean()), 4))
    tal = {}
    for k in ("CG-ctx", "CG-platt", "CG-iso", "CG_c05", "P3"):
        tal[k] = dict(dismissed_assoc=int(sum(((v[2][k] == "D") & v[1]).sum() for v in data.values())),
                      escalations=int(sum((v[2][k] == "E").sum() for v in data.values())),
                      unassoc_alerts=int(sum(((v[2][k] == "A") & ~v[1]).sum() for v in data.values())))
    out["T1_counts"] = tal
    keep = ["pooled_diff_pp", "pooled_ci95_pp", "pooled_noninferior", "ratio", "ratio_ci95", "ratio_criterion_holds"]
    for k in ("CG-ctx", "CG-platt", "CG-iso"):
        out[f"H1_{k}_minus_P3"] = {x: v2.cluster_boot(data, k, "P3")[x] for x in keep}
        out[f"H2_{k}_minus_CGc05"] = {x: v2.cluster_boot(data, k, "CG_c05")[x] for x in keep}
    json.dump(out, open(os.path.join(R, "context_c", "recal.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
