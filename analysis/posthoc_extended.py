"""POST HOC (specified 07.11.2026 after E3, K3 and D1 were known; requested by the framing review):
score CG-D (frozen development tables, results/detectability_tables_dev.json) and the constant-discount family
(c in 1, 0.75, 0.5, 0.25, 0) on the January 2025 - June 2026 periods in which E3 and K3 failed, at both references.
Unlike the 2024 test, these periods contain 24 IM.MK31 outage days, so the outage behaviour of the discounted
variants is measured here for the first time. Nothing is tuned: weights, delta, thetas and tables are frozen.

Chunks: IU.MAKZ = results/extended/vm_2025/out_* (09-01 replaced by vm_2025_rerun/outA_2025-09-01) + kaggle_2026h1,
the same set as code/11_extended_eval.py; II.KURK = results/extended/kurk_ext/outK_*.
Output: results/posthoc/extended_discount.json
"""
import os, json, glob, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = os.path.join(root, "results", "extended")
_t = [os.path.join(root, "results", "prereg", "detectability_tables_dev.json"), os.path.join(root, "results", "detectability_tables_dev.json")]
TAB = json.load(open(next(f for f in _t if os.path.exists(f))))  # repository or hub layout
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]


def chunk_dirs(ref):
    if ref == "KURK":
        return sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(root, "results", "kurk_ext", "outK_*")))
    rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
    ds = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))]
    return ds + [os.path.join(E, "kaggle_2026h1")]


def load(ref):
    frames, cal, dist = [], [], {}
    for d in chunk_dirs(ref):
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv"))
        ep["day"] = ep.t_on_utc.str[:10]; mk = av.set_index("day")["MK31_valid_share"]
        ep["regime"] = ep.day.map(lambda x: "normal" if mk.get(x, 0) >= 0.9 else ("outage" if mk.get(x, 0) < 0.1 else "partial"))
        frames.append(ep); cal += av.day.tolist()
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    ep = pd.concat(frames, ignore_index=True)
    cal = sorted(set(cal))
    return ep, cal, dist


def score(ref):
    ep, cal, dist = load(ref)
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    assert len(NB) == 3 and all(k in dist for k in NB), (ref, NB, dist)
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"
    p3 = np.full(len(ep), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"
    p1 = np.where(yes, "ALERT", "DISMISS").astype(object)
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    days = ep.day.to_numpy(); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    reg = ep.regime.to_numpy(); out_m = reg == "outage"; n_out = len(set(days[out_m])) if out_m.any() else 0
    nd = len(cal)

    def decide(qno):
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float); q = np.where(S[k] == "NO", qno(k), q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"
        return a

    def summ(a):
        rng = np.random.default_rng(7); v = []
        for _ in range(2000):
            ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
            v.append(((a[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
        return {"missed": int(((a == "DISMISS") & assoc).sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
                "esc_per_day": round(float((a == "ESCALATE").sum()) / nd, 2),
                "missed_outage": int(((a == "DISMISS") & assoc & out_m).sum()),
                "diff_vs_P3_pp": round(float(((a[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100), 2),
                "ci95": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]}

    r = {"reference": ref, "calendar_days": nd, "episodes": int(len(ep)), "assoc": int(assoc.sum()),
         "outage_days_with_episodes": n_out, "assoc_outage": int((assoc & out_m).sum()),
         "neighbours_km": {k: dist[k] for k in NB}}
    r["P3"] = {"missed": int(((p3 == "DISMISS") & assoc).sum()), "alert_unassoc": int(((p3 == "ALERT") & ~assoc).sum()),
               "esc_per_day": round(float((p3 == "ESCALATE").sum()) / nd, 2), "missed_outage": int(((p3 == "DISMISS") & assoc & out_m).sum())}
    r["P1_missed_outage"] = int(((p1 == "DISMISS") & assoc & out_m).sum())
    for c in [1.0, 0.75, 0.5, 0.25, 0.0]:
        r[f"c={c}"] = summ(decide(lambda k, c=c: np.full(len(ep), c)))
    r["CG-D table"] = summ(decide(lambda k: np.array([TAB[ref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b])))
    return r


if __name__ == "__main__":
    out = {"status": "post hoc, specified after E3/K3/D1 were known; frozen parameters; not a confirmatory test"}
    for ref in ["MAKZ", "KURK"]:
        out[ref] = score(ref)
    os.makedirs(os.path.join(root, "results", "posthoc"), exist_ok=True)
    json.dump(out, open(os.path.join(root, "results", "posthoc", "extended_discount.json"), "w"), indent=1)
    for ref in ["MAKZ", "KURK"]:
        r = out[ref]; print(ref, {k: r[k] for k in ["calendar_days", "episodes", "assoc", "assoc_outage"]}, "P1 outage", r["P1_missed_outage"])
        for k in ["P3", "c=1.0", "c=0.75", "c=0.5", "c=0.25", "c=0.0", "CG-D table"]: print("  ", k.ljust(11), r[k])
