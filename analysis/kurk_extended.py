"""Scoring of PREREGISTRATION_KURK_EXTENDED.md (repository commit a53686d): II.KURK as reference, 2025-01-01..2026-06-30,
six three-month chunks processed on the Google Cloud VM (results/extended/kurk_ext/outK_*). Frozen detector and policies.
K1 outage days (MK31 valid < 10 %): CG dismisses fewer associated alarms than P1
K2 whole period: CG forwards fewer unassociated alerts than P3 and than P1t
K3 non-inferiority: upper bound of the 95 % paired day-bootstrap interval of (CG - P3 dismissed-associated share) <= 3 pp
   (primary: resampling of episode dates as in code/11; sensitivity: calendar-preserving, all days kept)
K4 every episode with all neighbours MISSING is escalated by CG
Output: results/extended/kurk_ext/kurk_ext_eval.json
"""
import os, json, glob, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(root, "results", "kurk_ext")
frames, cal, info = [], [], []
for d in sorted(glob.glob(os.path.join(B, "outK_*"))):
    s = json.load(open(os.path.join(d, "summary.json"))); log = open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read()
    ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv"))
    ep["day"] = ep.t_on_utc.str[:10]; mk = av.set_index("day")["MK31_valid_share"]
    ep["regime"] = ep.day.map(lambda x: "normal" if mk.get(x, 0) >= 0.9 else ("outage" if mk.get(x, 0) < 0.1 else "partial"))
    frames.append(ep); cal += av.day.tolist()
    dist = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)}
    info.append({"chunk": os.path.basename(d), "days": len(av), "episodes": len(ep), "catalog_failures": s.get("catalog_failures", []),
                 "regional_catalog": s.get("catalog", {}).get("regional"), "outage_days": int((av.MK31_valid_share < 0.1).sum()), "reference": s.get("reference")})
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
num = np.zeros(len(ep)); den = np.zeros(len(ep))
for k in NB:
    q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
dd = den >= 0.45; Dv = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
cg = np.full(len(ep), "ESCALATE", dtype=object); cg[dd & (Dv >= 0.6)] = "ALERT"; cg[dd & (Dv <= 0.16)] = "DISMISS"; act["CG"] = cg
reg = ep.regime.to_numpy(); days = ep.day.to_numpy(); cal = np.array(sorted(set(cal))); nd = len(cal)
nout = sum(i["outage_days"] for i in info); nnorm = None
def summ(a, m, n):
    return {"episodes": int(m.sum()), "assoc": int((assoc & m).sum()), "missed": int(((a == "DISMISS") & assoc & m).sum()),
            "alert_unassoc": int(((a == "ALERT") & ~assoc & m).sum()), "escalate": int(((a == "ESCALATE") & m).sum()),
            "esc_per_day": round(float(((a == "ESCALATE") & m).sum()) / max(n, 1), 2)}
allm = np.ones(len(ep), bool)
res = {"preregistration": "PREREGISTRATION_KURK_EXTENDED.md, commit a53686d", "reference": "II.KURK", "neighbours_by_distance_km": {k: dist.get(k) for k in NB},
       "chunks": info, "calendar_days": int(nd), "outage_days": int(nout),
       "all": {n: summ(a, allm, nd) for n, a in act.items()}, "outage": {n: summ(a, reg == "outage", nout) for n, a in act.items()}}
o = res["outage"]; a_ = res["all"]
res["K1"] = {"CG_missed": o["CG"]["missed"], "P1_missed": o["P1"]["missed"], "assoc": o["CG"]["assoc"],
             "holds": (o["CG"]["missed"] < o["P1"]["missed"]) if o["CG"]["assoc"] > 0 else None}
res["K2"] = {"CG": a_["CG"]["alert_unassoc"], "P3": a_["P3"]["alert_unassoc"], "P1t": a_["P1t"]["alert_unassoc"],
             "holds": a_["CG"]["alert_unassoc"] < a_["P3"]["alert_unassoc"] and a_["CG"]["alert_unassoc"] < a_["P1t"]["alert_unassoc"]}
obs = ((cg[assoc] == "DISMISS").mean() - (act["P3"][assoc] == "DISMISS").mean()) * 100
rng = np.random.default_rng(7); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}; v = []
for _ in range(2000):
    ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
    if len(ids): v.append(((cg[ids] == "DISMISS").mean() - (act["P3"][ids] == "DISMISS").mean()) * 100)
ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
di = {d: i for i, d in enumerate(cal)}; dix = ep.day.map(di).to_numpy(); per = [np.flatnonzero((dix == i) & assoc) for i in range(nd)]
r2 = np.random.default_rng(7); v2 = []
for _ in range(2000):
    ids = np.concatenate([per[i] for i in r2.integers(0, nd, nd)])
    if len(ids): v2.append(((cg[ids] == "DISMISS").mean() - (act["P3"][ids] == "DISMISS").mean()) * 100)
res["K3"] = {"diff_pp": round(float(obs), 2), "ci95_pp": ci, "margin_pp": 3.0, "holds": ci[1] <= 3.0,
             "calendar_sensitivity_ci95_pp": [round(float(np.percentile(v2, 2.5)), 2), round(float(np.percentile(v2, 97.5)), 2)]}
am = np.ones(len(ep), bool)
for k in NB: am &= S[k] == "MISSING"
res["K4"] = {"all_missing_episodes": int(am.sum()), "escalated": int((cg[am] == "ESCALATE").sum()),
             "holds": bool((cg[am] == "ESCALATE").all()) if am.any() else None}
json.dump(res, open(os.path.join(B, "kurk_ext_eval.json"), "w"), indent=1, default=str)
for c in info: print(c)
print("days", nd, "outage", nout, "episodes", len(ep))
for n in act: print(n, res["all"][n], "| outage", res["outage"][n])
for h in ["K1", "K2", "K3", "K4"]: print(h, res[h])
