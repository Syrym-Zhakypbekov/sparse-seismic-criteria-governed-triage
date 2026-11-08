"""Scorer of PREREGISTRATION_BASELINES_ML_LLM_2026-11-08.md (pushed with the plan, before any training or LLM call on episodes).

Modes (run in this order):
  selfcheck  reproduce published P3 / CG / CG-D counts of every test set and AK-GT's stored CG actions (no learned model)
  ml         train LR / GB / MLP on the development period, pick thresholds by 5-fold contiguous-block CV, score M1-M6, I1-I2
  llm        Gemini triage of the fixed samples (resumable, $10 cap), then L1-L5
  latency    T1-T3
  report     merge everything into results/baselines_ml_llm/baselines_ml_llm.json
Python 3.12 (sklearn 1.9.1, pandas 3.1, numpy 2.5).
"""
import os, sys, json, glob, re, time, subprocess, urllib.request, random
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
OUT = os.path.join(R, "baselines_ml_llm"); os.makedirs(os.path.join(OUT, "llm"), exist_ok=True)
TAB = json.load(open(os.path.join(R, "prereg", "detectability_tables_dev.json")))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
WR = [0.25, 0.20, 0.15]; WSNR = 0.40; DELTA = 0.45; TH_A = 0.60; TH_D = 0.16
CG_DEV_ESC_SHARE = 392 / 1077            # results/criteria_governed/dm_summary.json, development CV
DEV_DIST = {"MK31": 24.0, "KURK": 499.6, "WUS": 1058.6}
FEATS = ["yes1", "no1", "cov1", "yes2", "no2", "cov2", "yes3", "no3", "cov3", "snr", "snr_undef"]
NBOOT, SEED = 2000, 7
BUDGET = os.environ.get("P10_ML_BUDGET") == "1"   # post hoc budget-matched variant, see deviation 1 in the ledger
SUFFIX = "_budget_posthoc" if BUDGET else ""


# ---------------------------------------------------------------- data
def load_dirs(dirs, dist_fixed=None):
    fr, cal, dist = [], [], dict(dist_fixed or {})
    for d in dirs:
        e = pd.read_csv(os.path.join(d, "episodes.csv")); fr.append(e)
        cal += pd.read_csv(os.path.join(d, "availability.csv")).day.tolist()
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    ep = pd.concat(fr, ignore_index=True); ep["day"] = ep.t_on_utc.str[:10]
    names = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    for r, k in enumerate(names, 1):
        ep[f"st{r}"] = ep[f"n_{k}"].astype(str); ep[f"cov{r}"] = ep[f"cov_{k}"].fillna(0).astype(float)
    ep["assoc"] = ep.assoc_event >= 0
    return ep, sorted(set(cal)), names, {k: dist.get(k) for k in names}


def sets():
    E = json.load(open(os.path.join(R, "extended", "extended_eval.json")))
    out = {"DEV": load_dirs([os.path.join(R, "stage1_v3")], DEV_DIST),
           "EXT-MAKZ": load_dirs([os.path.join(root, c["source"].replace("\\", "/")) for c in E["chunks"]]),
           "EXT-KURK": load_dirs(sorted(glob.glob(os.path.join(R, "kurk_ext", "outK_*")))),
           "KZ": load_dirs(sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*")))),
           "AK": load_dirs(sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))))}
    ak = out["AK"][0]
    gt = pd.read_csv(os.path.join(R, "ground_truth", "episodes_labelled.csv.gz"))
    assert len(gt) == len(ak) and gt.t_on_utc.is_unique
    ak = ak.merge(gt[["t_on_utc", "gt", "act_CG", "act_P3"]].rename(columns={"gt": "gtl"}), on="t_on_utc", how="left", validate="1:1")
    assert ak.gtl.notna().all()
    out["AK"] = (ak,) + out["AK"][1:]
    return out


def features(ep):
    X = pd.DataFrame(index=ep.index)
    for r in (1, 2, 3):
        X[f"yes{r}"] = (ep[f"st{r}"] == "YES").astype(float); X[f"no{r}"] = (ep[f"st{r}"] == "NO").astype(float)
        X[f"cov{r}"] = ep[f"cov{r}"].clip(0, 1)
    X["snr"] = ep.snr_db.clip(0, 60).fillna(0); X["snr_undef"] = ep.snr_db.isna().astype(float)
    return X[FEATS].to_numpy()


# ---------------------------------------------------------------- frozen policies
def policies(ep, names):
    st = [ep[f"st{r}"].to_numpy() for r in (1, 2, 3)]
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    yes = (st[0] == "YES") | (st[1] == "YES") | (st[2] == "YES")
    p3 = np.full(len(ep), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"
    out = {"P3": p3}
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    variants = [("CG", False)] + ([("CG-D", True)] if all(k in TAB["MAKZ"] for k in names) else [])
    for name, det in variants:
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for r, k in enumerate(names):
            q = np.isin(st[r], ["YES", "NO"]).astype(float)
            if det:
                p = np.array([TAB["MAKZ"][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]); q = np.where(st[r] == "NO", p, q)
            num += WR[r] * (st[r] == "YES") * q; den += WR[r] * q
        num += WSNR * np.clip(snr / 30, 0, 1) * ok; den += WSNR * ok
        dd = den >= DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= TH_A)] = "ALERT"; a[dd & (D <= TH_D)] = "DISMISS"; out[name] = a
    return out


def cg_scalar(s1, s2, s3, snr):
    """CG for one episode in plain Python (latency benchmark); s* in {'YES','NO','MISSING'}, snr float or None."""
    num = den = 0.0
    for s, w in ((s1, 0.25), (s2, 0.20), (s3, 0.15)):
        if s == "YES": num += w; den += w
        elif s == "NO": den += w
    if snr is not None:
        x = snr / 30.0; x = 0.0 if x < 0 else (1.0 if x > 1 else x); num += 0.40 * x; den += 0.40
    if den < 0.45: return "ESCALATE"
    D = num / den
    return "ALERT" if D >= 0.60 else ("DISMISS" if D <= 0.16 else "ESCALATE")


def cg_score(st, snr):
    """CG's D(x) (nan if undefined) for monotonicity checks; st list of 3 arrays."""
    num = np.zeros(len(snr)); den = np.zeros(len(snr)); ok = ~np.isnan(snr); s = np.nan_to_num(snr)
    for r in range(3):
        q = np.isin(st[r], ["YES", "NO"]).astype(float); num += WR[r] * (st[r] == "YES") * q; den += WR[r] * q
    num += WSNR * np.clip(s / 30, 0, 1) * ok; den += WSNR * ok
    return np.where(den > 0, num / np.where(den > 0, den, 1), 0.0)


def summ(a, ep, ndays):
    assoc = ep.assoc.to_numpy()
    return {"missed": int(((a == "DISMISS") & assoc).sum()), "assoc": int(assoc.sum()),
            "dismissed_share_pct": round(float((a[assoc] == "DISMISS").mean() * 100), 3),
            "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()), "esc_per_day": round(float((a == "ESCALATE").sum()) / ndays, 2),
            "dismiss": int((a == "DISMISS").sum()), "alert": int((a == "ALERT").sum()), "escalate": int((a == "ESCALATE").sum())}


# ---------------------------------------------------------------- bootstrap
def day_index(ep):
    days = ep.day.to_numpy(); ud = np.array(sorted(set(days))); di = {d: i for i, d in enumerate(ud)}
    return ud, np.array([di[d] for d in days])


def boot_dismiss(a, b, mask, ep, margin=3.0, ratio=1.5):
    """paired day bootstrap over episode dates: (a-b) dismissed share among `mask`, and (a+0.5)/(b+0.5) count ratio"""
    ud, dix = day_index(ep); n = len(ud)
    da = np.bincount(dix[mask & (a == "DISMISS")], minlength=n).astype(float)
    db = np.bincount(dix[mask & (b == "DISMISS")], minlength=n).astype(float)
    nm = np.bincount(dix[mask], minlength=n).astype(float)
    obs = (da.sum() - db.sum()) / nm.sum() * 100; robs = (da.sum() + 0.5) / (db.sum() + 0.5)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, n, size=(NBOOT, n))
    # same draws as rng.choice(ud, len(ud)) in earlier scorers? earlier scorers drew from days WITH masked episodes;
    # here all days with any episode are drawn (days without masked episodes contribute zero); both reported in the plan's spirit.
    A, B, N = da[idx].sum(1), db[idx].sum(1), nm[idx].sum(1)
    v = (A - B) / np.where(N > 0, N, 1) * 100; vr = (A + 0.5) / (B + 0.5)
    ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
    cr = [round(float(np.percentile(vr, 2.5)), 3), round(float(np.percentile(vr, 97.5)), 3)]
    p = float(((v >= margin).sum() + 1) / (NBOOT + 1)); pr = float(((vr >= ratio).sum() + 1) / (NBOOT + 1))
    return {"diff_pp": round(float(obs), 2), "ci95_pp": ci, "holds_margin": ci[1] <= margin, "p_one_sided": p,
            "ratio": round(float(robs), 3), "ratio_ci95": cr, "holds_ratio": cr[1] <= ratio, "p_ratio_one_sided": pr,
            "count_a": int(da.sum()), "count_b": int(db.sum()), "n": int(nm.sum())}


def boot_count(a, b, mask, ep, act="ALERT"):
    ud, dix = day_index(ep); n = len(ud)
    ca = np.bincount(dix[mask & (a == act)], minlength=n).astype(float); cb = np.bincount(dix[mask & (b == act)], minlength=n).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, n, size=(NBOOT, n)); v = ca[idx].sum(1) - cb[idx].sum(1)
    ci = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return {"diff": int(ca.sum() - cb.sum()), "ci95": ci, "holds": ci[1] < 0, "p_one_sided": float(((v >= 0).sum() + 1) / (NBOOT + 1))}


def boot_share(a, b, mask, ep, act):
    ud, dix = day_index(ep); n = len(ud)
    ca = np.bincount(dix[mask & (a == act)], minlength=n).astype(float); cb = np.bincount(dix[mask & (b == act)], minlength=n).astype(float)
    nm = np.bincount(dix[mask], minlength=n).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, n, size=(NBOOT, n)); N = nm[idx].sum(1)
    v = (ca[idx].sum(1) - cb[idx].sum(1)) / np.where(N > 0, N, 1) * 100
    return {"diff_pp": round(float((ca.sum() - cb.sum()) / nm.sum() * 100), 2),
            "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
            "share_a_pct": round(float(ca.sum() / nm.sum() * 100), 2), "share_b_pct": round(float(cb.sum() / nm.sum() * 100), 2), "n": int(nm.sum())}


def holm(ps):
    order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0.0
    for i, j in enumerate(order): run = max(run, min(1.0, (m - i) * ps[j])); adj[j] = run
    return adj.tolist()


# ---------------------------------------------------------------- self-check
PUBLISHED = {"EXT-MAKZ": {"P3": (38, 6350), "CG": (98, 2870)}, "EXT-KURK": {"P3": (49, 7444), "CG": (228, 3511)},
             "KZ": {"P3": (17, 5541), "CG": (102, 2442), "CG-D": (36, 3037)}, "AK": {"P3": (3, 3671), "CG": (33, 520), "CG-D": (5, 768)}}


def selfcheck(S):
    rep = {}
    for name, pub in PUBLISHED.items():
        ep, cal, names, dist = S[name]; P = policies(ep, names); rep[name] = {"episodes": len(ep), "days": len(cal), "neighbours": dist}
        for pol, (miss, ua) in pub.items():
            s = summ(P[pol], ep, len(cal)); rep[name][pol] = {"missed": s["missed"], "alert_unassoc": s["alert_unassoc"]}
            assert (s["missed"], s["alert_unassoc"]) == (miss, ua), (name, pol, s, miss, ua)
    ak, _, names, _ = S["AK"]; P = policies(ak, names)
    assert (P["CG"] == ak.act_CG.to_numpy()).all() and (P["P3"] == ak.act_P3.to_numpy()).all()
    rep["AK-GT"] = {"stored_actions_identical": True, "CONFIRMED": int((ak.gtl == "CONFIRMED").sum()), "REJECTED": int((ak.gtl == "REJECTED").sum())}
    return rep


# ---------------------------------------------------------------- learned models
def make_models():
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    return {"LR": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
            "GB": lambda: GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=7),
            "MLP": lambda: make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32, 16), alpha=1e-3, max_iter=3000, random_state=7))}


def act_from_p(p, tD, tA):
    a = np.full(len(p), "ESCALATE", dtype=object); a[p <= tD] = "DISMISS"; a[p >= tA] = "ALERT"; return a


def thresholds(p, y):
    grid = np.round(np.arange(0, 1.0005, 0.001), 3)
    tD = max([t for t in grid if (p[y] > t).mean() >= 0.95], default=0.0)
    tA = None
    if BUDGET:   # POST HOC variant (deviation 1): largest theta_A whose escalation share stays within CG's budget
        ok = [t for t in grid[grid > tD] if ((p > tD) & (p < t)).mean() <= CG_DEV_ESC_SHARE]
        return float(tD), (float(max(ok)) if ok else 1.0)
    for t in grid[grid > tD]:   # as pre-registered (wording error: satisfied just above theta_D)
        if ((p > tD) & (p < t)).mean() <= CG_DEV_ESC_SHARE: tA = float(t); break
    return float(tD), (tA if tA is not None else 1.0)


def run_ml(S):
    import warnings; warnings.filterwarnings("ignore")
    dev, _, _, _ = S["DEV"]; X = features(dev); y = dev.assoc.to_numpy()
    days = np.array(sorted(dev.day.unique())); blocks = np.array_split(days, 5)
    blk = dev.day.map({d: i for i, b in enumerate(blocks) for d in b}).to_numpy()
    M = make_models(); fitted, info = {}, {}
    for name, mk in M.items():
        oof = np.zeros(len(dev))
        for k in range(5):
            m = mk().fit(X[blk != k], y[blk != k]); oof[blk == k] = m.predict_proba(X[blk == k])[:, 1]
        tD, tA = thresholds(oof, y); a = act_from_p(oof, tD, tA)
        fitted[name] = mk().fit(X, y)
        info[name] = {"theta_D": tD, "theta_A": tA, "dev_oof": summ(a, dev, len(days)),
                      "dev_oof_escalation_share": round(float((a == "ESCALATE").mean()), 4), "cg_dev_escalation_share": round(CG_DEV_ESC_SHARE, 4)}
        if name == "LR":
            lr = fitted[name][-1]; info[name]["coefficients_standardised"] = dict(zip(FEATS, np.round(lr.coef_[0], 4).tolist()))
    res = {"training": info, "sets": {}}
    raw = {"M1": [], "M2a": [], "M2r": [], "M3": [], "M5a": []}
    acts_all = {}
    for sname in ["EXT-MAKZ", "EXT-KURK", "KZ", "AK"]:
        ep, cal, names, dist = S[sname]; nd = len(cal); P = policies(ep, names); Xs = features(ep); assoc = ep.assoc.to_numpy()
        allmiss = (ep.st1 == "MISSING").to_numpy() & (ep.st2 == "MISSING").to_numpy() & (ep.st3 == "MISSING").to_numpy()
        r = {"episodes": len(ep), "days": nd, "neighbours_km": dist, "policies": {k: summ(v, ep, nd) for k, v in P.items()}, "models": {}}
        for name, m in fitted.items():
            p = m.predict_proba(Xs)[:, 1]; a = act_from_p(p, info[name]["theta_D"], info[name]["theta_A"]); acts_all[(sname, name)] = a
            cell = {"summary": summ(a, ep, nd),
                    "M1_vs_P3": boot_dismiss(a, P["P3"], assoc, ep),
                    "M2_CG_vs_m": boot_dismiss(P["CG"], a, assoc, ep),
                    "M3_unassoc_alerts_CG_minus_m": boot_count(P["CG"], a, ~assoc, ep),
                    "M4_escalations": {"CG_per_day": round(float((P["CG"] == "ESCALATE").sum()) / nd, 2), "m_per_day": round(float((a == "ESCALATE").sum()) / nd, 2)},
                    "M6_all_missing": {"episodes": int(allmiss.sum()), "CG_escalated": int((P["CG"][allmiss] == "ESCALATE").sum()),
                                       "m_automatic": int(np.isin(a[allmiss], ["ALERT", "DISMISS"]).sum()),
                                       "m_dismissed_assoc": int(((a == "DISMISS") & allmiss & assoc).sum()), "exercised": bool(allmiss.any())}}
            if sname == "AK":
                conf = (ep.gtl == "CONFIRMED").to_numpy(); rej = (ep.gtl == "REJECTED").to_numpy()
                cell["M5a_confirmed_dismissed_CG_minus_m"] = boot_dismiss(P["CG"], a, conf, ep)
                b = boot_share(P["CG"], a, rej, ep, "ALERT"); b["holds"] = b["ci95_pp"][1] < 0; cell["M5b_rejected_alert_CG_minus_m"] = b
                raw["M5a"].append(cell["M5a_confirmed_dismissed_CG_minus_m"]["p_one_sided"])
            raw["M1"].append(cell["M1_vs_P3"]["p_one_sided"]); raw["M2a"].append(cell["M2_CG_vs_m"]["p_one_sided"])
            raw["M2r"].append(cell["M2_CG_vs_m"]["p_ratio_one_sided"]); raw["M3"].append(cell["M3_unassoc_alerts_CG_minus_m"]["p_one_sided"])
            r["models"][name] = cell
        res["sets"][sname] = r
    # Holm per hypothesis across the 12 cells
    cells = [(s, n) for s in ["EXT-MAKZ", "EXT-KURK", "KZ", "AK"] for n in fitted]
    for h, key, sub in [("M1", "M1_vs_P3", "p_one_sided"), ("M2a", "M2_CG_vs_m", "p_one_sided"), ("M2r", "M2_CG_vs_m", "p_ratio_one_sided"),
                        ("M3", "M3_unassoc_alerts_CG_minus_m", "p_one_sided")]:
        adj = holm(np.array(raw[h]))
        for (s, n), q in zip(cells, adj): res["sets"][s]["models"][n].setdefault("holm", {})[h] = round(q, 4)
    if raw["M5a"]:
        for n, q in zip(fitted, holm(np.array(raw["M5a"]))): res["sets"]["AK"]["models"][n].setdefault("holm", {})["M5a"] = round(q, 4)
    tally = {}
    for h, f in [("M1", lambda c: c["M1_vs_P3"]["holds_margin"]), ("M2a", lambda c: c["M2_CG_vs_m"]["holds_margin"]),
                 ("M2r", lambda c: c["M2_CG_vs_m"]["holds_ratio"]), ("M3", lambda c: c["M3_unassoc_alerts_CG_minus_m"]["holds"])]:
        tally[h] = f"{sum(f(res['sets'][s]['models'][n]) for s, n in cells)}/{len(cells)}"
    tally["M5a"] = f"{sum(res['sets']['AK']['models'][n]['M5a_confirmed_dismissed_CG_minus_m']['holds_margin'] for n in fitted)}/3"
    tally["M5b"] = f"{sum(res['sets']['AK']['models'][n]['M5b_rejected_alert_CG_minus_m']['holds'] for n in fitted)}/3"
    res["tally"] = tally
    # I2 monotonicity on all test episodes
    mono = {k: {"NO_to_YES": 0, "MISSING_to_YES": 0, "SNR_plus5dB": 0, "trials": {"NO_to_YES": 0, "MISSING_to_YES": 0, "SNR_plus5dB": 0}} for k in ["CG"] + list(fitted)}
    for sname in ["EXT-MAKZ", "EXT-KURK", "KZ", "AK"]:
        ep = S[sname][0]; base_st = [ep[f"st{r}"].to_numpy() for r in (1, 2, 3)]; snr = ep.snr_db.to_numpy(dtype=float)
        X0 = features(ep); p0 = {n: m.predict_proba(X0)[:, 1] for n, m in fitted.items()}; d0 = cg_score(base_st, snr)
        for r in (1, 2, 3):
            for frm, lab in [("NO", "NO_to_YES"), ("MISSING", "MISSING_to_YES")]:
                sel = base_st[r - 1] == frm
                if not sel.any(): continue
                ep2 = ep.loc[sel].copy(); ep2[f"st{r}"] = "YES"; ep2[f"cov{r}"] = 1.0
                X1 = features(ep2); st2 = [ep2[f"st{k}"].to_numpy() for k in (1, 2, 3)]
                d1 = cg_score(st2, ep2.snr_db.to_numpy(dtype=float)); mono["CG"][lab] += int((d1 < d0[sel] - 1e-12).sum()); mono["CG"]["trials"][lab] += int(sel.sum())
                for n, m in fitted.items():
                    mono[n][lab] += int((m.predict_proba(X1)[:, 1] < p0[n][sel] - 1e-12).sum()); mono[n]["trials"][lab] += int(sel.sum())
        sel = ~np.isnan(snr); ep2 = ep.loc[sel].copy(); ep2["snr_db"] = ep2.snr_db + 5
        X1 = features(ep2); d1 = cg_score([ep2[f"st{k}"].to_numpy() for k in (1, 2, 3)], ep2.snr_db.to_numpy(dtype=float))
        mono["CG"]["SNR_plus5dB"] += int((d1 < d0[sel] - 1e-12).sum()); mono["CG"]["trials"]["SNR_plus5dB"] += int(sel.sum())
        for n, m in fitted.items():
            mono[n]["SNR_plus5dB"] += int((m.predict_proba(X1)[:, 1] < p0[n][sel] - 1e-12).sum()); mono[n]["trials"]["SNR_plus5dB"] += int(sel.sum())
    res["I2_monotonicity_violations"] = mono
    res["I1_exact_decomposition"] = {"CG": "yes: D(x) = sum of w_i^eff s_i over named criteria, weights fixed before data (Statement 2.2, max error 2.2e-16 in dm_summary.json)",
                                     "LR": "additive only in the logit, coefficients learned from 141 associated episodes; thresholds on a probability scale",
                                     "GB": "no exact decomposition (200 trees)", "MLP": "no exact decomposition (two hidden layers)"}
    json.dump(res, open(os.path.join(OUT, f"ml_eval{SUFFIX}.json"), "w"), indent=1, default=float)
    import pickle; pickle.dump(fitted, open(os.path.join(OUT, f"ml_models{SUFFIX}.pkl"), "wb"))
    json.dump({n: info[n] for n in info}, open(os.path.join(OUT, f"ml_thresholds{SUFFIX}.json"), "w"), indent=1, default=float)
    return res


# ---------------------------------------------------------------- LLM
MODEL, PROJECT, LOC = "gemini-3.8-flash", os.environ.get("GCP_PROJECT", ""), "global"
PRICE_IN, PRICE_OUT, CAP = 0.75e-6, 3.75e-6, 10.0
GCLOUD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
STATE = {"YES": "triggered in its expected arrival window (YES)", "NO": "recorded data but did not trigger (NO)", "MISSING": "had no usable data (MISSING)"}
PROMPT = """You triage automatic seismic triggers (STA/LTA detections) at one reference seismic station.
Three neighbour stations are checked for each trigger. Neighbour distances from the reference, nearest first: {dists}.
For each trigger you see the signal-to-noise ratio (SNR) at the reference and, for each neighbour, whether it
triggered in its expected arrival window (YES), recorded data without a trigger (NO) or had no usable data (MISSING),
with the share of its window covered by data.

Choose one action:
- ALERT: forward automatically as a real seismic event.
- DISMISS: discard automatically as not a real seismic event.
- ESCALATE: send to a human analyst.
Dismissing a real earthquake is the costliest error: at most about 5% of real events may be dismissed.
Escalate when the evidence is missing or conflicting. Unnecessary alerts and escalations also have a cost.

Trigger:
- Reference SNR: {snr}
{nb}

Answer only with JSON: {{"action": "ALERT" | "DISMISS" | "ESCALATE", "reason": "<= 30 words", "criteria_used": ["..."]}}"""


def prompt_for(row, dist):
    dd = ", ".join(f"neighbour {i} {d:.0f} km" for i, d in enumerate(dist, 1))
    snr = "undefined" if pd.isna(row.snr_db) else f"{row.snr_db:.1f} dB"
    nb = "\n".join(f"- Neighbour {r} ({dist[r-1]:.0f} km): {STATE[row[f'st{r}']]}, window coverage {row[f'cov{r}']:.2f}" for r in (1, 2, 3))
    return PROMPT.format(dists=dd, snr=snr, nb=nb)


def llm_samples(S):
    rng = np.random.default_rng(SEED)
    ak, _, _, dak = S["AK"]; ex, _, _, dex = S["EXT-MAKZ"]
    rej = np.flatnonzero((ak.gtl == "REJECTED").to_numpy()); conf = np.flatnonzero((ak.gtl == "CONFIRMED").to_numpy())
    a_ids = list(rej) + list(rng.choice(conf, 486, replace=False))
    asc = np.flatnonzero(ex.assoc.to_numpy()); una = np.flatnonzero(~ex.assoc.to_numpy())
    e_ids = list(rng.choice(asc, 300, replace=False)) + list(rng.choice(una, 300, replace=False))
    items = [("AK-GT", int(i)) for i in a_ids] + [("EXT-MAKZ", int(i)) for i in e_ids]
    rng.shuffle(items)
    return items, {"AK-GT": list(dak.values()), "EXT-MAKZ": list(dex.values())}


_tok = {"v": None, "t": 0.0}
def token():
    if time.time() - _tok["t"] > 1500:
        _tok["v"] = subprocess.run([GCLOUD, "auth", "print-access-token"], capture_output=True, text=True).stdout.strip(); _tok["t"] = time.time()
    return _tok["v"]


def call(text):
    url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOC}/publishers/google/models/{MODEL}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "thinkingConfig": {"thinkingLevel": "low"}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    t0 = time.perf_counter(); r = json.loads(urllib.request.urlopen(req, timeout=120).read()); dt = time.perf_counter() - t0
    parts = r["candidates"][0].get("content", {}).get("parts", [])
    txt = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return txt, r.get("usageMetadata", {}), r.get("modelVersion"), r["candidates"][0].get("finishReason"), dt


def parse(txt):
    try:
        j = json.loads(txt); a = str(j.get("action", "")).upper().strip()
        return (a if a in ("ALERT", "DISMISS", "ESCALATE") else None), j
    except Exception:
        m = re.search(r'"action"\s*:\s*"(ALERT|DISMISS|ESCALATE)"', txt or "")
        return (m.group(1) if m else None), None


def cost_of(u):
    out = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    return u.get("promptTokenCount", 0) * PRICE_IN + out * PRICE_OUT


def run_llm(S):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    items, dist = llm_samples(S)
    fa = os.path.join(OUT, "llm", "calls.jsonl")
    done = {}; spent = 0.0
    if os.path.exists(fa):
        for l in open(fa, encoding="utf-8"):
            j = json.loads(l); spent += j.get("cost_usd", 0.0)
            if "response" in j: done[(j["pass"], j["set"], j["idx"])] = j   # failed (HTTP error) calls are retried on resume
    lock = threading.Lock(); state = {"spent": spent, "stopped": False}
    fo = open(fa, "a", encoding="utf-8")

    def work(job):
        ps, sname, i = job
        if (ps, sname, i) in done: return
        with lock:
            if state["spent"] >= CAP: state["stopped"] = True; return
        ep = S["AK" if sname == "AK-GT" else sname][0]; row = ep.iloc[i]; text = prompt_for(row, dist[sname])
        rec = {"pass": ps, "set": sname, "idx": i, "t_on_utc": row.t_on_utc, "model": MODEL, "prompt": text}
        for attempt in range(4):
            try:
                txt, u, ver, fin, dt = call(text)
                act, j = parse(txt)
                rec.update({"response": txt, "action": act, "parsed": j, "usage": u, "model_version": ver, "finish": fin,
                            "latency_s": round(dt, 4), "cost_usd": cost_of(u), "attempts": attempt + 1}); break
            except Exception as e:
                rec["error"] = type(e).__name__ + ": " + str(e)[:200]
                if "401" in str(e):
                    with lock: _tok["t"] = 0.0          # expired access token: fetch a new one (run 1 lost 38 calls to 401)
                time.sleep(3 * (attempt + 1))
        with lock:
            state["spent"] += rec.get("cost_usd", 0.0); fo.write(json.dumps(rec) + "\n"); fo.flush()

    jobs1 = [(1, s, i) for s, i in items]
    with ThreadPoolExecutor(6) as ex: list(ex.map(work, jobs1))
    jobs2 = [(2, s, i) for s, i in items[:100]]
    with ThreadPoolExecutor(6) as ex: list(ex.map(work, jobs2))
    fo.close()
    json.dump({"items": items, "stopped_by_cap": state["stopped"], "spent_usd": state["spent"]}, open(os.path.join(OUT, "llm", "sample.json"), "w"))
    return score_llm(S)


def boot_ep_share(a, b, act, n=NBOOT):
    rng = np.random.default_rng(SEED); N = len(a); idx = rng.integers(0, N, size=(n, N))
    va = (a[idx] == act).mean(1); vb = (b[idx] == act).mean(1); v = (va - vb) * 100
    return {"share_a_pct": round(float((a == act).mean() * 100), 2), "share_b_pct": round(float((b == act).mean() * 100), 2),
            "diff_pp": round(float(((a == act).mean() - (b == act).mean()) * 100), 2),
            "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)], "n": int(N)}


def kappa(a, b):
    labs = ["ALERT", "DISMISS", "ESCALATE"]; po = (a == b).mean()
    pe = sum((a == l).mean() * (b == l).mean() for l in labs)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def score_llm(S):
    items, _ = llm_samples(S)
    recs = [json.loads(l) for l in open(os.path.join(OUT, "llm", "calls.jsonl"), encoding="utf-8")]
    p1 = {(r["set"], r["idx"]): r for r in recs if r["pass"] == 1 and "response" in r}; p2 = {(r["set"], r["idx"]): r for r in recs if r["pass"] == 2 and "response" in r}
    res = {"model": MODEL, "calls_made": len(recs), "http_failed_records_retried": sum(1 for r in recs if "response" not in r), "calls_planned": len(items) + 100,
           "cost_usd": round(sum(r.get("cost_usd", 0) for r in recs), 4),
           "tokens": {k: int(sum(r.get("usage", {}).get(k, 0) for r in recs)) for k in ["promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount"]},
           "errors_http": sum(1 for r in recs if "action" not in r and "error" in r),
           "model_versions": sorted({str(r.get("model_version")) for r in recs})}
    lat = np.array([r["latency_s"] for r in recs if "latency_s" in r])
    res["latency_s"] = {"median": round(float(np.median(lat)), 3), "p95": round(float(np.percentile(lat, 95)), 3), "mean": round(float(lat.mean()), 3), "n": int(len(lat))}
    res["cost_per_call_usd"] = round(res["cost_usd"] / max(len(recs), 1), 6); res["cost_per_10000_episodes_usd"] = round(res["cost_usd"] / max(len(recs), 1) * 10000, 2)
    valid = [r for r in p1.values() if r.get("action")]
    res["L1_format"] = {"answers": len(p1), "valid": len(valid), "invalid_or_refused": len(p1) - len(valid),
                        "valid_share_pct": round(len(valid) / max(len(p1), 1) * 100, 2), "holds": len(valid) / max(len(p1), 1) >= 0.99,
                        "finish_reasons": pd.Series([r.get("finish") for r in p1.values()]).value_counts().to_dict()}
    tab = {}
    for sname, pos_lab, neg_lab in [("AK-GT", "CONFIRMED", "REJECTED"), ("EXT-MAKZ", True, False)]:
        ep, _, names, _ = S["AK" if sname == "AK-GT" else sname]; P = policies(ep, names)
        ids = [i for s, i in items if s == sname and (s, i) in p1]
        llm = np.array([p1[(sname, i)].get("action") or "ESCALATE" for i in ids], dtype=object); cg = P["CG"][ids]; p3 = P["P3"][ids]
        cls = (ep.gtl.to_numpy()[ids] if sname == "AK-GT" else ep.assoc.to_numpy()[ids])
        pos = cls == pos_lab; neg = cls == neg_lab
        L2 = boot_ep_share(cg[pos], llm[pos], "DISMISS"); L2["holds"] = L2["ci95_pp"][1] <= 3.0
        L3 = boot_ep_share(cg[neg], llm[neg], "ALERT"); L3["holds"] = L3["ci95_pp"][1] < 0
        conf = pd.crosstab(pd.Series(llm, name="LLM"), pd.Series(cg, name="CG")).to_dict()
        def dist_(a, m): return {k: int(v) for k, v in pd.Series(a[m]).value_counts().items()}
        tab[sname] = {"n": len(ids), "positives": int(pos.sum()), "negatives": int(neg.sum()),
                      "L2_CG_minus_LLM_dismissed_among_positives": L2, "L3_CG_minus_LLM_alert_among_negatives": L3,
                      "actions_positives": {"LLM": dist_(llm, pos), "CG": dist_(cg, pos), "P3": dist_(p3, pos)},
                      "actions_negatives": {"LLM": dist_(llm, neg), "CG": dist_(cg, neg), "P3": dist_(p3, neg)},
                      "L5_agreement_pct": round(float((llm == cg).mean() * 100), 2), "L5_kappa": round(kappa(llm, cg), 3),
                      "confusion_LLM_rows_CG_cols": conf}
    res["sets"] = tab
    rep = [(p1[k].get("action"), p2[k].get("action")) for k in p2 if k in p1]
    same = sum(1 for a, b in rep if a is not None and a == b)
    res["L4_repeatability"] = {"pairs": len(rep), "same_action": same, "share_pct": round(same / max(len(rep), 1) * 100, 2), "holds": same / max(len(rep), 1) >= 0.95}
    json.dump(res, open(os.path.join(OUT, "llm_eval.json"), "w"), indent=1, default=str)
    return res


# ---------------------------------------------------------------- latency
def run_latency(S):
    import pickle, platform
    fitted = pickle.load(open(os.path.join(OUT, "ml_models.pkl"), "rb"))
    ep, cal, names, _ = S["EXT-MAKZ"]; X = features(ep)
    rng = np.random.default_rng(SEED); ids = rng.choice(len(ep), 1000, replace=False)
    rows = [(ep.st1.iat[i], ep.st2.iat[i], ep.st3.iat[i], None if pd.isna(ep.snr_db.iat[i]) else float(ep.snr_db.iat[i])) for i in ids]
    P = policies(ep, names)
    assert all(cg_scalar(*r) == P["CG"][i] for r, i in zip(rows, ids))
    def per_call(f, args_list, rep=5):
        ts = []
        for _ in range(rep):
            for a in args_list:
                t0 = time.perf_counter_ns(); f(*a); ts.append(time.perf_counter_ns() - t0)
        ts = np.array(ts) / 1e3
        return {"median_us": round(float(np.median(ts)), 3), "p95_us": round(float(np.percentile(ts, 95)), 3), "calls": int(len(ts))}
    out = {"machine": {"platform": platform.platform(), "processor": platform.processor(), "python": platform.python_version(),
                       "threads_env": {k: os.environ.get(k) for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]}},
           "single_episode": {"CG_python_scalar": per_call(cg_scalar, rows)}}
    for n, m in fitted.items():
        out["single_episode"][n] = per_call(lambda x: m.predict_proba(x), [(X[i:i + 1],) for i in ids], rep=1)
    t0 = time.perf_counter();
    for _ in range(5): policies(ep, names)
    tb = (time.perf_counter() - t0) / 5
    out["batch"] = {"episodes": int(len(ep)), "CG_vectorised_s": round(tb, 4), "CG_episodes_per_s": round(len(ep) / tb)}
    for n, m in fitted.items():
        t0 = time.perf_counter(); m.predict_proba(X); tb = time.perf_counter() - t0
        out["batch"][f"{n}_s"] = round(tb, 4); out["batch"][f"{n}_episodes_per_s"] = round(len(ep) / tb)
    lf = os.path.join(OUT, "llm_eval.json")
    if os.path.exists(lf):
        L = json.load(open(lf)); med = L["latency_s"]["median"] * 1e6; cg = out["single_episode"]["CG_python_scalar"]["median_us"]
        out["LLM_median_us"] = med; out["LLM_over_CG_ratio"] = round(med / cg)
        out["T2"] = {"holds": med >= 1000 * cg}
    out["T1"] = {"CG_median_us": out["single_episode"]["CG_python_scalar"]["median_us"], "holds": out["single_episode"]["CG_python_scalar"]["median_us"] < 1000}
    json.dump(out, open(os.path.join(OUT, "latency.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "selfcheck"
    S = sets()
    if mode == "selfcheck":
        r = selfcheck(S); json.dump(r, open(os.path.join(OUT, "selfcheck.json"), "w"), indent=1); print(json.dumps(r, indent=1))
    elif mode == "ml":
        selfcheck(S); r = run_ml(S); print(json.dumps({"training": r["training"], "tally": r["tally"]}, indent=1, default=float))
    elif mode == "llm":
        r = run_llm(S); print(json.dumps({k: v for k, v in r.items() if k != "sets"}, indent=1, default=str))
    elif mode == "llmscore":
        r = score_llm(S); print(json.dumps(r, indent=1, default=str))
    elif mode == "latency":
        print(json.dumps(run_latency(S), indent=1))
    elif mode == "report":
        out = {"preregistration": "PREREGISTRATION_BASELINES_ML_LLM_2026-11-08.md", "scorer": "analysis/baselines_ml_llm.py"}
        for k in ["selfcheck", "ml_eval", "ml_eval_budget_posthoc", "llm_eval", "latency"]:
            f = os.path.join(OUT, k + ".json")
            if os.path.exists(f): out[k] = json.load(open(f))
        json.dump(out, open(os.path.join(OUT, "baselines_ml_llm.json"), "w"), indent=1); print("written")
