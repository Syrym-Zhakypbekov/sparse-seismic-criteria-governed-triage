"""Post hoc (08.11.2026, internal review): consistency of baseline thresholds.

The frozen comparisons mixed two procedures: P3 (7.5 dB) and CG (theta_D 0.16) are medians of the five contiguous-block
development folds, while P1t (8.0 dB) and P2 (10.5 dB) are full-development (in-sample) values. This script derives every
SNR threshold by ONE documented procedure — the largest tau on the 0.5 dB grid 0..30 dB with which at least 95% of
associated development episodes are not dismissed (the rule of equation (4), applied to each SNR rule) — in two variants:
  A) full development set (in-sample), B) median of the five contiguous-block folds (training folds of each split).
It then re-scores every test set with P1t, P2, P3 at the frozen, A and B thresholds (CG and CG-D unchanged) and reports
dismissed associated alarms, unassociated alerts, escalations per day and the CG−P3 / CG-D−P3 day-bootstrap contrasts
(2000 resamples, seed 7, days with episodes), so the reader sees how each conclusion depends on the baseline threshold.
Also checks whether P2 and P3 ever differ at a common threshold .
Output: results/posthoc/threshold_consistency.json
"""
import os, json, glob
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
src = open(os.path.join(root, "analysis", "r12_checks.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(root, "analysis", "r12_checks.py")}
exec(compile(src[:src.index("E = os.path.join(R, \"extended\")")], "r12_helpers", "exec"), ns)
load, policies = ns["load"], ns["policies"]
GRID = np.round(np.arange(0, 30.01, 0.5), 2)


def feats(ep, dist):
    NB = sorted([k[2:] for k in ep.columns if k.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB:
        yes |= S[k] == "YES"; no |= S[k] == "NO"
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    return yes, no, snr, ok


def act(name, tau, yes, no, snr, ok):
    a = np.full(len(yes), "E", dtype=object)
    if name == "P1t":
        a[:] = "D"; a[yes | (ok & (snr >= tau))] = "A"; return a
    a[yes & ok & (snr >= tau)] = "A"
    d = (~yes) & ok & (snr < tau)
    if name == "P2": d &= no
    a[d] = "D"; return a


def fit(name, yes, no, snr, ok, assoc):
    best = None
    for t in GRID:
        a = act(name, t, yes, no, snr, ok)
        if ((a != "D") & assoc).sum() / max(assoc.sum(), 1) >= 0.95: best = float(t)
    return best


# development thresholds
dev = pd.read_csv(os.path.join(R, "stage1_v3", "episodes.csv")); dev["day"] = dev.t_on_utc.str[:10]
dist_dev = {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}
yd, nd, sd, od = feats(dev, dist_dev); ad = (dev.assoc_event >= 0).to_numpy()
days = sorted(dev.day.unique()); blocks = np.array_split(np.array(days), 5)
thr = {"frozen": {"P1t": 8.0, "P2": 10.5, "P3": 7.5}, "A_full_development": {}, "B_cv_median": {}, "B_folds": {}}
for name in ["P1t", "P2", "P3"]:
    thr["A_full_development"][name] = fit(name, yd, nd, sd, od, ad)
    fv = []
    for b in blocks:
        m = ~dev.day.isin(set(b)).to_numpy()
        fv.append(fit(name, yd[m], nd[m], sd[m], od[m], ad[m]))
    thr["B_folds"][name] = fv; thr["B_cv_median"][name] = float(np.median(fv))

E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
        "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
        "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}


def boot(ep, a, b, assoc, n=2000, seed=7):
    dd = ep.day.to_numpy(); ud = np.unique(dd[assoc]); idx = {d: i for i, d in enumerate(ud)}
    di = np.array([idx.get(x, -1) for x in dd]); m = assoc & (di >= 0)
    na = np.bincount(di[m], minlength=len(ud)).astype(float)
    da = np.bincount(di[m & (a == "D")], minlength=len(ud)).astype(float)
    db = np.bincount(di[m & (b == "D")], minlength=len(ud)).astype(float)
    rng = np.random.default_rng(seed); v = np.empty(n)
    for i in range(n):
        s = rng.integers(0, len(ud), len(ud)); v[i] = (da[s].sum() - db[s].sum()) / na[s].sum() * 100
    return round(float((da.sum() - db.sum()) / na.sum() * 100), 2), [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]


out = {"status": "post hoc after the internal review (08.11.2026); pre-specified results unchanged", "thresholds_dB": thr, "tests": {}}
for tname, (dirs, ref) in SETS.items():
    ep, av, dist = load(dirs); P = policies(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy(); ndays = ep.day.nunique()
    y, n_, s, o = feats(ep, dist); res = {"episodes": int(len(ep)), "associated": int(assoc.sum())}
    summ = lambda a: {"dismissed_assoc": int(((a == "D") & assoc).sum()), "unassoc_alerts": int(((a == "A") & ~assoc).sum()),
                      "esc_per_day": round(float((a == "E").sum()) / max(len(av), 1), 2)}
    for v in ["frozen", "A_full_development", "B_cv_median"]:
        row = {}
        for name in ["P1t", "P2", "P3"]:
            row[name] = summ(act(name, thr[v][name], y, n_, s, o))
        p3 = act("P3", thr[v]["P3"], y, n_, s, o)
        row["CG_minus_P3"] = boot(ep, P["CG"], p3, assoc); row["CGD_minus_P3"] = boot(ep, P["CG-D"], p3, assoc)
        res[v] = row
    res["CG"] = summ(P["CG"]); res["CG-D"] = summ(P["CG-D"])
    diff = {str(t): int((act("P2", t, y, n_, s, o) != act("P3", t, y, n_, s, o)).sum()) for t in [7.5, 8.0, 10.5]}
    res["P2_vs_P3_decisions_differing_at_common_tau"] = diff
    out["tests"][tname] = res
    print(tname, "done")
os.makedirs(os.path.join(R, "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(R, "posthoc", "threshold_consistency.json"), "w"), indent=1)
print(json.dumps(out["thresholds_dB"], indent=1))
for t, r in out["tests"].items():
    print(t, {v: (r[v]["P3"]["dismissed_assoc"], r[v]["CG_minus_P3"], r[v]["CGD_minus_P3"]) for v in ["frozen", "A_full_development", "B_cv_median"]}, "P2!=P3:", r["P2_vs_P3_decisions_differing_at_common_tau"])
