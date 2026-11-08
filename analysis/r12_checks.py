"""Checks requested by review R12 (07.11.2026), all post hoc, no tuning:
A. Circular calendar-block bootstrap (10,000 resamples, seed 7; blocks of 1, 7, 14, 28 days; every calendar day of the
   test kept, days without associated episodes contribute zero) for every primary non-inferiority contrast:
   E3 (CG-P3, extended IU.MAKZ), K3 (CG-P3, extended II.KURK), D1 (CG-D-P3, 2024 both references),
   N3 (CG-P3, KZ) and N5 (CG-D-P3, KZ). Reported: point estimate and 95% interval per block length.
B. KZ constant-c control (c = 0.5): dismissed associated, unassociated alerts, escalations per day, excess vs P3.
C. KZ availability cross-tabulation: days on which the reference and neighbours were simultaneously without data,
   and the number of catalogue events with a predicted P arrival on those days (coverage diagnostic only).
Output: results/posthoc/r12_checks.json
"""
import os, json, glob, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
_t = [os.path.join(R, "prereg", "detectability_tables_dev.json"), os.path.join(R, "detectability_tables_dev.json")]
TAB = json.load(open(next(f for f in _t if os.path.exists(f))))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]


def load(dirs):
    fr, av, dist = [], [], {}
    for d in dirs:
        e = pd.read_csv(os.path.join(d, "episodes.csv")); e["day"] = e.t_on_utc.str[:10]; fr.append(e)
        av.append(pd.read_csv(os.path.join(d, "availability.csv")))
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    return pd.concat(fr, ignore_index=True), pd.concat(av).drop_duplicates("day").sort_values("day"), dist


def policies(ep, dist, ref, c=None):
    NB = sorted([k[2:] for k in ep.columns if k.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15]))
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    p3 = np.full(len(ep), "E", dtype=object); p3[yes & ok & (snr >= 7.5)] = "A"; p3[(~yes) & ok & (snr < 7.5)] = "D"
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    out = {"P3": p3}
    for name in ["CG", "CG-D", "CG(c=0.5)"]:
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float)
            if name == "CG-D":
                q = np.where(S[k] == "NO", np.array([TAB[ref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]), q)
            if name == "CG(c=0.5)": q = np.where(S[k] == "NO", 0.5, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += 0.40 * np.clip(snr / 30, 0, 1) * ok; den += 0.40 * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "E", dtype=object); a[dd & (D >= 0.6)] = "A"; a[dd & (D <= 0.16)] = "D"; out[name] = a
    return out


def block_boot(ep, cal, a, b, assoc, blocks=(1, 7, 14, 28), n=10000, seed=7):
    cal = list(cal); di = {d: i for i, d in enumerate(cal)}; N = len(cal)
    dix = ep.day.map(di).to_numpy()
    na = np.bincount(dix[assoc], minlength=N).astype(float)
    da = np.bincount(dix[assoc & (a == "D")], minlength=N).astype(float)
    db = np.bincount(dix[assoc & (b == "D")], minlength=N).astype(float)
    point = (da.sum() - db.sum()) / na.sum() * 100
    res = {"point_pp": round(float(point), 2)}
    for L in blocks:
        rng = np.random.default_rng(seed); k = int(np.ceil(N / L)); v = np.empty(n)
        starts = rng.integers(0, N, size=(n, k))
        idx = ((starts[:, :, None] + np.arange(L)[None, None, :]) % N).reshape(n, -1)[:, :N]
        v = (da[idx].sum(1) - db[idx].sum(1)) / na[idx].sum(1) * 100
        res[f"block_{L}d"] = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
    return res


E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"E3": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ", "CG"),
        "K3": (sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK", "CG"),
        "D1 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ", "CG-D"),
        "D1 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK", "CG-D"),
        "N3": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ", "CG"),
        "N5": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ", "CG-D")}
out = {"status": "post hoc checks after review R12", "A_block_bootstrap": {}}
cache = {}
for name, (dirs, ref, pol) in SETS.items():
    key = tuple(dirs)
    if key not in cache:
        ep, av, dist = load(dirs); cache[key] = (ep, av, dist, policies(ep, dist, ref))
    ep, av, dist, P = cache[key]
    assoc = (ep.assoc_event >= 0).to_numpy()
    out["A_block_bootstrap"][name] = {"contrast": f"{pol} - P3", "calendar_days": int(len(av)), **block_boot(ep, av.day, P[pol], P["P3"], assoc)}

ep, av, dist, P = cache[tuple(SETS["N3"][0])]
assoc = (ep.assoc_event >= 0).to_numpy(); nd = len(av)
def summ(a): return {"dismissed_assoc": int(((a == "D") & assoc).sum()), "unassoc_alerts": int(((a == "A") & ~assoc).sum()),
                     "esc_per_day": round(float((a == "E").sum()) / nd, 2),
                     "excess_vs_P3_pp": round(float(((a[assoc] == "D").mean() - (P["P3"][assoc] == "D").mean()) * 100), 2)}
out["B_KZ_constant_c"] = {k: summ(P[k]) for k in ["P3", "CG", "CG-D", "CG(c=0.5)"]}
out["B_KZ_constant_c"]["CG(c=0.5)"]["block_bootstrap"] = block_boot(ep, av.day, P["CG(c=0.5)"], P["P3"], assoc)

cols = [c for c in av.columns if c.endswith("_valid_share")]
low = av[(av[cols] < 0.1).sum(axis=1) >= 2]
cats = pd.concat([pd.read_csv(os.path.join(d, "catalog.csv")) for d in SETS["N3"][0] if os.path.exists(os.path.join(d, "catalog.csv"))], ignore_index=True)
cats["day"] = pd.to_datetime(cats.p_pred, unit="s").dt.strftime("%Y-%m-%d")
out["C_KZ_simultaneous_gaps"] = [{"day": r.day, **{c.split("_")[0]: float(r[c]) for c in cols},
                                  "catalogue_P_arrivals": int((cats.day == r.day).sum()),
                                  "episodes": int((ep.day == r.day).sum())} for _, r in low.iterrows()]
os.makedirs(os.path.join(R, "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(R, "posthoc", "r12_checks.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
