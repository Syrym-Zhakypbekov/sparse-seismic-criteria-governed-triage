"""Scorer of PLAN_DETPROB_BASELINE_2026-11-08.md (pushed b45af84 before fitting or scoring).

Detection-probability likelihood baseline with a reject band, in the spirit of Cohen et al. [42] and NET-VISA:
  L(x) = logit P0(event | SNR) + sum_YES log(Pd/Pf) + sum_NO log((1-Pd)/(1-Pf)),  MISSING -> 0,
dismiss if L <= t_D, alert if L >= t_A, escalate otherwise. Pd, Pf, P0 are logistic regressions fitted on the context-c
training data only (IU.MAKZ development + batch-A AU AV C1 IV KR OH, catalogue association). Compared head to head with
P1t, P3, CG (c = 1, 0.5, CG-D, context c_j(x)) on the reviewed-bulletin networks: T1 = 26 batch-B (out of sample),
ALL33 = all 33 (6 training networks inside, stated). Output: results/detprob/detprob.json.
"""
import os, json, math, importlib.util
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
R = os.path.join(root, "results"); OUT = os.path.join(R, "detprob")


def _mod(name, fn):
    s = importlib.util.spec_from_file_location(name, os.path.join(here, fn)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


cc = _mod("cc", "context_c.py"); v2 = cc.v2
CLIPP = (0.01, 0.99)
SITE_F = ["snr", "snr_ok", "logd"]


def ref_x(d):
    return np.column_stack([np.where(d["ok"], np.clip(d["snr"], 0, 40) / 40, 0.0), d["ok"].astype(float)])


class Std:
    """Standardised logistic regression (fit on training only)."""
    def __init__(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0); self.sd[self.sd == 0] = 1
        self.lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - self.mu) / self.sd, y)
    def p(self, X): return np.clip(self.lr.predict_proba((X - self.mu) / self.sd)[:, 1], *CLIPP)
    def coef(self, names): return dict(zip(names, [round(float(c), 4) for c in self.lr.coef_[0]])) | {"intercept": round(float(self.lr.intercept_[0]), 4)}


def fit_models(train):
    Xd, yd, Xf, yf, X0, y0 = [], [], [], [], [], []
    Xc, yc = [], []
    for d in train:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        X0.append(ref_x(d)); y0.append(assoc.astype(int))
        for f in d["F"]:
            valid = np.isin(f.state, ["YES", "NO"]); yes = (f.state == "YES").astype(int)
            Xd.append(f[SITE_F].to_numpy()[valid & assoc]); yd.append(yes[valid & assoc])
            Xf.append(f[SITE_F].to_numpy()[valid & ~assoc]); yf.append(yes[valid & ~assoc])
            m = assoc & valid; Xc.append(f[cc.FEATS].to_numpy()[m]); yc.append(yes[m])
    Pd = Std(np.vstack(Xd), np.concatenate(yd)); Pf = Std(np.vstack(Xf), np.concatenate(yf)); P0 = Std(np.vstack(X0), np.concatenate(y0))
    # context-c model, identical to analysis/context_c.py (same features, standardisation, solver)
    X = np.vstack(Xc); y = np.concatenate(yc); mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - mu) / sd, y)

    class Ctx:
        def predict_proba(self, Z): return lr.predict_proba((Z - mu) / sd)
    info = {"pairs_Pd": int(sum(len(a) for a in yd)), "pairs_Pf": int(sum(len(a) for a in yf)), "episodes_P0": int(sum(len(a) for a in y0)),
            "Pd_rate": round(float(np.concatenate(yd).mean()), 4), "Pf_rate": round(float(np.concatenate(yf).mean()), 4),
            "P0_rate": round(float(np.concatenate(y0).mean()), 4),
            "coef_Pd": Pd.coef(SITE_F), "coef_Pf": Pf.coef(SITE_F), "coef_P0": P0.coef(["snr", "snr_ok"])}
    return Pd, Pf, P0, Ctx(), info


def llr(d, Pd, Pf, P0):
    p0 = P0.p(ref_x(d)); L = np.log(p0 / (1 - p0))
    for f in d["F"]:
        X = f[SITE_F].to_numpy(); pd_, pf = Pd.p(X), Pf.p(X); s = f.state
        L = L + np.where(s == "YES", np.log(pd_ / pf), 0.0) + np.where(s == "NO", np.log((1 - pd_) / (1 - pf)), 0.0)
    return L


def act3(L, tD, tA):
    a = np.full(len(L), "E", dtype=object); a[L >= tA] = "A"; a[L <= tD] = "D"; return a


def shares_to_thresholds(L, fD, fA):
    tD = float(np.quantile(L, fD)) if fD > 0 else -np.inf
    tA = float(np.quantile(L, 1 - fA)) if fA > 0 else np.inf
    if tD >= tA: tD = np.nextafter(tA, -np.inf)
    return tD, tA


def all_actions(d, Pd, Pf, P0, ctx, thr_T):
    act, _, chk = cc.actions(d, ctx)
    L = llr(d, Pd, Pf, P0); act["LLR-T"] = act3(L, *thr_T)
    return act, L, chk


POL = ["P1t", "P3", "CG", "CG_c05", "CG-D", "CG-ctx", "LLR-T", "LLR-M"]


def summary(data, nd_days):
    out = {}
    for k in POL:
        dm = ua = es = al = ea = n = asc = 0
        for net, (days, assoc, act) in data.items():
            a = act[k]; dm += int(((a == "D") & assoc).sum()); ua += int(((a == "A") & ~assoc).sum())
            es += int((a == "E").sum()); al += int((a == "A").sum()); ea += int(((a == "E") & assoc).sum()); n += len(a); asc += int(assoc.sum())
        out[k] = {"episodes": n, "reviewed_associated": asc, "dismissed_assoc": dm, "dismissed_assoc_pct": round(100 * dm / max(asc, 1), 3),
                  "unassoc_alerts": ua, "alerts": al, "escalations": es, "analyst_items_alert_plus_escalation": al + es,
                  "queue_precision_pct": round(100 * ea / max(es, 1), 3), "alert_precision_pct": round(100 * (al - ua) / max(al, 1), 3),
                  "escalations_per_network_day": round(es / max(nd_days, 1), 2)}
    return out


def score(name, ds, Pd, Pf, P0, ctx, thr_T):
    data, Ls, chk, ref = {}, {}, {}, {}
    nd = 0
    for d in ds:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        act, L, c = all_actions(d, Pd, Pf, P0, ctx, thr_T); chk[d["net"]] = c
        data[d["net"]] = (d["ep"].day.to_numpy(), assoc, act); Ls[d["net"]] = L; nd += len(d["av"])
        ref[d["net"]] = {k: int(((act[k] == "D") & assoc).sum()) for k in ("CG_c05", "CG-D", "CG-ctx")}
    # LLR-M: equal budget with CG c = 0.5 on this set (pooled escalations and alerts), descriptive
    allL = np.concatenate([Ls[k] for k in data]); allc = np.concatenate([data[k][2]["CG_c05"] for k in data])
    tM = shares_to_thresholds(allL, float((allc == "D").mean()), float((allc == "A").mean()))
    for k in data: data[k][2]["LLR-M"] = act3(Ls[k], *tM)
    res = {"set": name, "networks": sorted(data), "n_networks": len(data), "selfcheck_c05_CGD_all_ok": all(all(v.values()) for v in chk.values()),
           "thresholds_LLR_T": [round(x, 4) for x in thr_T], "thresholds_LLR_M": [round(x, 4) for x in tM],
           "per_network_dismissed_assoc_refs": ref, "summary": summary(data, nd)}
    for a in ("LLR-T", "LLR-M"):
        for b in ("P3", "CG_c05", "CG-D", "CG-ctx", "P1t"):
            res[f"{a}_minus_{b}"] = v2.cluster_boot(data, a, b)
    for a, b in (("CG_c05", "P3"), ("CG-ctx", "P3")):
        res[f"ref_{a}_minus_{b}"] = v2.cluster_boot(data, a, b)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    C = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}
    train = [cc.load_local("IU_dev")] + [x for x in (cc.load_v2(n, C[n]) for n in cc.TRAIN_V2) if x is not None]
    Pd, Pf, P0, ctx, info = fit_models(train)
    # LLR-T thresholds: training dismiss / alert shares of CG c = 0.5
    Ltr = np.concatenate([llr(d, Pd, Pf, P0) for d in train])
    ctr = np.concatenate([v2.policies(d["S"], d["snr"], d["ok"])["CG_c05"] for d in train])
    fD, fA = float((ctr == "D").mean()), float((ctr == "A").mean())
    thr_T = shares_to_thresholds(Ltr, fD, fA)
    info.update({"train_sets": [d["net"] for d in train], "train_CGc05_dismiss_share": round(fD, 4), "train_CGc05_alert_share": round(fA, 4),
                 "thresholds_LLR_T": [round(x, 4) for x in thr_T]})
    print(json.dumps(info, indent=1), flush=True)
    rev = json.load(open(os.path.join(R, "v2_reviewed", "v2_eval_reviewed.json")))["networks"]
    inc = sorted(n for n, v in rev.items() if v.get("included_in_pooled"))
    ds = {}
    for n in inc:
        x = cc.load_v2(n, C[n], reviewed=True)
        if x is not None: ds[n] = x
        print("loaded", n, flush=True)
    out = {"plan": "PLAN_DETPROB_BASELINE_2026-11-08.md (b45af84)", "training": info}
    out["T1_batchB_reviewed"] = score("T1", [ds[n] for n in inc if rev[n].get("batch") == "B" and n in ds], Pd, Pf, P0, ctx, thr_T)
    print("T1 done", flush=True)
    out["ALL33_reviewed"] = score("ALL33", [ds[n] for n in inc if n in ds], Pd, Pf, P0, ctx, thr_T)
    # self-check against results/context_c (T1 per network dismissed counts of CG_c05, CG-D, CG-ctx)
    cj = json.load(open(os.path.join(R, "context_c", "context_c.json")))["T1_reviewed_batchB"]["H4_decision_mix_per_network"]
    mism = {n: (v, {k: cj[n][k]["dismissed_assoc"] for k in v}) for n, v in out["T1_batchB_reviewed"]["per_network_dismissed_assoc_refs"].items()
            if n in cj and any(cj[n][k]["dismissed_assoc"] != v[k] for k in v)}
    out["selfcheck_vs_context_c_T1"] = {"networks_compared": sum(1 for n in out["T1_batchB_reviewed"]["per_network_dismissed_assoc_refs"] if n in cj),
                                        "mismatches": mism}
    json.dump(out, open(os.path.join(OUT, "detprob.json"), "w"), indent=1, default=str)
    for s in ("T1_batchB_reviewed", "ALL33_reviewed"):
        print(s, json.dumps(out[s]["summary"], indent=0))
        for k, v in out[s].items():
            if "_minus_" in k: print(k, v["pooled_diff_pp"], v["pooled_ci95_pp"], v["ratio"], v["ratio_ci95"])
    print("selfcheck", out["selfcheck_vs_context_c_T1"]["networks_compared"], len(mism))


if __name__ == "__main__":
    main()
