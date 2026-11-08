"""Exploratory control requested by review R8-M01 (07.11.2026, after the pre-registered 2024 test was scored):
replace the development confirmation-rate table by a constant quality factor c for every valid NO (c = 1 is CG,
c = 0 ignores NO), keep weights, delta, thresholds; 2024 data, both references. Reports dismissed associated,
unassociated alerts, escalations per day, CG-x - P3 dismissed share with day-bootstrap CI; also the frozen CG-D.
Labelled exploratory: chosen after the result. Output: results/y2024/discount_sweep.json
"""
import os, json, glob, re, numpy as np, pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); Y = os.path.join(root, "results", "y2024")
T = json.load(open(os.path.join(root, "results", "prereg", "detectability_tables_dev.json")))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
out = {}
for ref in ["MAKZ", "KURK"]:
    fr, dist = [], {}
    for d in sorted(glob.glob(os.path.join(Y, f"out24_{ref}_*"))):
        e = pd.read_csv(os.path.join(d, "episodes.csv")); e["day"] = e.t_on_utc.str[:10]; fr.append(e)
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read(), re.M)})
    ep = pd.concat(fr, ignore_index=True); NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}; yes = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"
    p3 = np.full(len(ep), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    days = ep.day.to_numpy(); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    def run(qno):
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float)
            q = np.where(S[k] == "NO", qno(k), q); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.6)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"
        rng = np.random.default_rng(7); v = []
        for _ in range(2000):
            ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
            v.append(((a[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
        return {"missed": int(((a == "DISMISS") & assoc).sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
                "esc_per_day": round(float((a == "ESCALATE").sum()) / 366, 2),
                "diff_vs_P3_pp": round(float(((a[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100), 2),
                "ci95": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]}
    r = {f"c={c}": run(lambda k, c=c: np.full(len(ep), c)) for c in [1.0, 0.9, 0.75, 0.5, 0.25, 0.0]}
    r["CG-D table"] = run(lambda k: np.array([T[ref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]))
    r["P3"] = {"missed": int(((p3 == "DISMISS") & assoc).sum()), "alert_unassoc": int(((p3 == "ALERT") & ~assoc).sum()), "esc_per_day": round(float((p3 == "ESCALATE").sum()) / 366, 2)}
    out[ref] = r
json.dump(out, open(os.path.join(Y, "discount_sweep.json"), "w"), indent=1)
for ref, r in out.items():
    print(ref)
    for k, v in r.items(): print("  ", k.ljust(11), v)
