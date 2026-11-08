"""Scoring of PREREGISTRATION_DETECTABILITY_2024.md (repository commit 3853469). Written before any 2024 result was read.
For each reference (MAKZ, KURK): 2024 chunks results/y2024/out24_<REF>_*; frozen P1, P1t 8.0, P2 10.5, P3 7.5, CG, and CG-D
(NO enters with q = detection probability of that neighbour in the reference-SNR bin, tables results/prereg/detectability_tables_dev.json).
D1 non-inferiority CG-D vs P3 (upper 95 % paired day-bootstrap bound <= 3 pp, episode dates, 2000, seed 7; calendar version as sensitivity)
D2 CG-D unassociated alerts < P3;  D3 outage days (MK31 valid < 10 %) CG-D dismissed associated < P1;  D4 CG-D dismissed associated < CG.
Output: results/y2024/cgd_2024_eval.json
"""
import os, json, glob, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Y = os.path.join(root, "results", "y2024")
TAB = json.load(open(os.path.join(root, "results", "prereg", "detectability_tables_dev.json")))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]

def evaluate(ref, base=None, prefix=None, table_ref=None):
    base = base or Y; prefix = prefix or f"out24_{ref}_"; table_ref = table_ref or ref
    frames, cal, info, dist = [], [], [], {}
    for d in sorted(glob.glob(os.path.join(base, prefix + "*"))):
        s = json.load(open(os.path.join(d, "summary.json"))); log = open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read()
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv"))
        ep["day"] = ep.t_on_utc.str[:10]; mk = av.set_index("day")["MK31_valid_share"]
        ep["regime"] = ep.day.map(lambda x: "normal" if mk.get(x, 0) >= 0.9 else ("outage" if mk.get(x, 0) < 0.1 else "partial"))
        frames.append(ep); cal += av.day.tolist()
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
        info.append({"chunk": os.path.basename(d), "days": len(av), "episodes": len(ep), "catalog_failures": s.get("catalog_failures", []),
                     "outage_days": int((av.MK31_valid_share < 0.1).sum())})
    ep = pd.concat(frames, ignore_index=True)
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)}
    for n, t in [("P3", 7.5), ("P2", 10.5)]:
        a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"
        d_ = (~yes) & ok & (snr < t); d_ = d_ & no if n == "P2" else d_; a[d_] = "DISMISS"; act[n] = a
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    for name, detect in [("CG", False), ("CG-D", True)]:
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float)
            if detect:
                p = np.array([TAB[table_ref][k].get(bb, {"p": 0.5})["p"] if bb in LAB else 0.5 for bb in b])
                q = np.where(S[k] == "NO", p, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"; act[name] = a
    reg = ep.regime.to_numpy(); days = ep.day.to_numpy(); cal = np.array(sorted(set(cal))); nd = len(cal); nout = sum(i["outage_days"] for i in info)
    def summ(a, m, n):
        return {"episodes": int(m.sum()), "assoc": int((assoc & m).sum()), "missed": int(((a == "DISMISS") & assoc & m).sum()),
                "alert_unassoc": int(((a == "ALERT") & ~assoc & m).sum()), "esc_per_day": round(float(((a == "ESCALATE") & m).sum()) / max(n, 1), 2)}
    allm = np.ones(len(ep), bool)
    res = {"reference": ref, "chunks": info, "calendar_days": int(nd), "outage_days": int(nout), "neighbours_km": {k: dist.get(k) for k in NB},
           "all": {n: summ(a, allm, nd) for n, a in act.items()}, "outage": {n: summ(a, reg == "outage", nout) for n, a in act.items()}}
    cgd, p3 = act["CG-D"], act["P3"]
    obs = ((cgd[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100
    rng = np.random.default_rng(7); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}; v = []
    for _ in range(2000):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((cgd[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
    di = {d: i for i, d in enumerate(cal)}; dix = ep.day.map(di).to_numpy(); per = [np.flatnonzero((dix == i) & assoc) for i in range(nd)]
    r2 = np.random.default_rng(7); v2 = []
    for _ in range(2000):
        ids = np.concatenate([per[i] for i in r2.integers(0, nd, nd)])
        if len(ids): v2.append(((cgd[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
    ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
    a_ = res["all"]; o = res["outage"]
    res["D1"] = {"diff_pp": round(float(obs), 2), "ci95_pp": ci, "holds": ci[1] <= 3.0,
                 "calendar_ci95_pp": [round(float(np.percentile(v2, 2.5)), 2), round(float(np.percentile(v2, 97.5)), 2)]}
    res["D2"] = {"CG-D": a_["CG-D"]["alert_unassoc"], "P3": a_["P3"]["alert_unassoc"], "holds": a_["CG-D"]["alert_unassoc"] < a_["P3"]["alert_unassoc"]}
    res["D3"] = {"CG-D": o["CG-D"]["missed"], "P1": o["P1"]["missed"], "assoc": o["CG-D"]["assoc"],
                 "holds": (o["CG-D"]["missed"] < o["P1"]["missed"]) if o["CG-D"]["assoc"] > 0 else None}
    res["D4"] = {"CG-D": a_["CG-D"]["missed"], "CG": a_["CG"]["missed"], "holds": a_["CG-D"]["missed"] < a_["CG"]["missed"]}
    cg_ = act["CG"]; r3 = np.random.default_rng(7); v3 = []
    for _ in range(2000):
        ids = np.concatenate([idx[d] for d in r3.choice(ud, len(ud))])
        if len(ids): v3.append(((cg_[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
    ci3 = [round(float(np.percentile(v3, 2.5)), 2), round(float(np.percentile(v3, 97.5)), 2)]
    res["NI_CG"] = {"diff_pp": round(float(((cg_[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100), 2), "ci95_pp": ci3, "holds": ci3[1] <= 3.0}
    am = np.ones(len(ep), bool)
    for k in NB: am &= S[k] == "MISSING"
    res["ALLMISSING"] = {"episodes": int(am.sum()), "CG_escalated": int((cg_[am] == "ESCALATE").sum()), "holds": bool((cg_[am] == "ESCALATE").all()) if am.any() else None}
    return res

if __name__ != "__main__": raise SystemExit
out = {"preregistration": "PREREGISTRATION_DETECTABILITY_2024.md, commit 3853469"}
for ref in ["MAKZ", "KURK"]:
    if glob.glob(os.path.join(Y, f"out24_{ref}_*")): out[ref] = evaluate(ref)
json.dump(out, open(os.path.join(Y, "cgd_2024_eval.json"), "w"), indent=1, default=str)
for ref in ["MAKZ", "KURK"]:
    if ref in out:
        r = out[ref]; print(ref, r["calendar_days"], "days", {k: r[k] for k in ["D1", "D2", "D3", "D4"]})
        for n in ["P1", "P1t", "P3", "P2", "CG", "CG-D"]: print("  ", n, r["all"][n])
