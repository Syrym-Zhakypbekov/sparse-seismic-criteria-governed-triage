"""Addendum 3 of PLAN_PAPER1_HARMONISED_2026-11-09.md: rule (4) applied to each criteria-governed variant on its own development
actions, and the six frozen test sets replayed at the per-variant theta_D (X - P3-2t 8.0/10.0 dB, published day bootstrap).
Output: results/paper1/pervariant_theta.json."""
import os, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(HERE, "paper1_harmonised.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(HERE, "paper1_harmonised.py")}
exec(src[:src.index("# ---------- development")], ns)
load, published_boot, R, TAB, BINS, LAB = ns["load"], ns["published_boot"], ns["R"], ns["TAB"], ns["BINS"], ns["LAB"]


def scores(ep, dist, tref):
    NBR = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9)); W = dict(zip(NBR, [0.25, 0.20, 0.15]))
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NBR}; yes = np.zeros(len(ep), bool)
    for k in NBR: yes |= S[k] == "YES"
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    def D(qno):
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NBR:
            q = np.isin(S[k], ["YES", "NO"]).astype(float); q = np.where(S[k] == "NO", qno(k), q); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += 0.40 * np.clip(snr / 30, 0, 1) * ok; den += 0.40 * ok
        return np.where(den >= 0.45, num / np.where(den > 0, den, 1), np.nan)
    Ds = {"CG": D(lambda k: 1.0), "CG c=0.5": D(lambda k: 0.5),
          "CG-D": D(lambda k: np.array([TAB[tref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]))}
    p3 = np.full(len(ep), "E", dtype=object); p3[yes & ok & (snr >= 10.0)] = "A"; p3[(~yes) & ok & (snr < 8.0)] = "D"
    return Ds, p3, assoc, ep.day.to_numpy()


def act(Dv, td):
    a = np.full(len(Dv), "E", dtype=object); f = ~np.isnan(Dv); a[f & (Dv >= 0.60)] = "A"; a[f & (Dv <= td)] = "D"; return a


dev, dav, _ = load([os.path.join(R, "stage1_v3")]); Ds0, _, assoc0, _ = scores(dev, {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}, "MAKZ")
theta = {}
for v, Dv in Ds0.items():
    best = None
    for t in np.round(np.arange(0, 0.5901, 0.01), 2):
        if ((act(Dv, t) != "D") & assoc0).sum() / assoc0.sum() >= 0.95: best = float(t)
    theta[v] = best
res = {"plan": "addendum 3", "theta_D_rule4_per_variant": theta,
       "dev": {v: {"dismissed_assoc": int(((act(Dv, theta[v]) == "D") & assoc0).sum()), "escalations": int((act(Dv, theta[v]) == "E").sum()),
                   "dismissed_assoc_at_0.16": int(((act(Dv, 0.16) == "D") & assoc0).sum())} for v, Dv in Ds0.items()}, "sets": {}}
print(res["theta_D_rule4_per_variant"], res["dev"])
E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
        "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
        "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}
for name, (dirs, tref) in SETS.items():
    ep, av, dist = load(dirs); Ds, p3, assoc, days = scores(ep, dist, tref); r = {}
    for v, Dv in Ds.items():
        a = act(Dv, theta[v]); r[v] = published_boot(days, assoc, a, p3)
        r[v]["dismissed"] = int(((a == "D") & assoc).sum()); r[v]["esc_per_day"] = round(float((a == "E").sum()) / av.day.nunique(), 2)
    r["P3-2t dismissed"] = int(((p3 == "D") & assoc).sum()); res["sets"][name] = r; print(name, r)
json.dump(res, open(os.path.join(R, "paper1", "pervariant_theta.json"), "w", encoding="utf-8"), indent=1)
