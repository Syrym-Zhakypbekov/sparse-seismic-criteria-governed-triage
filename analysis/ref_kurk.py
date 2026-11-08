"""Second reference station (R3: one reference station only). II.KURK is the reference; IU.MAKZ, IM.MK31, G.WUS are
neighbours. Same pipeline, detector tuned on KURK in 2026-07-01..07, evaluated 2026-07-08..09-30 (Google Cloud VM,
results/extended/ref_KURK). Exploratory, not pre-registered. Policy parameters FROZEN from the MAKZ development:
weights by distance rank (0.25, 0.20, 0.15) + SNR 0.40, delta 0.45, theta_A 0.60, theta_D 0.16, SNR 30 dB; tau as frozen.
Regimes by MK31 availability (an MK31 outage removes one neighbour of KURK as well).
Output: results/extended/ref_KURK/ref_kurk_eval.json
"""
import os, json, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(root, "results", "extended", "ref_KURK", "outB_ref_KURK")
ep = pd.read_csv(os.path.join(D, "episodes.csv")); av = pd.read_csv(os.path.join(D, "availability.csv"))
log = open(os.path.join(D, "run.log"), encoding="utf-8", errors="ignore").read()
dist = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)}
NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
ep["day"] = ep.t_on_utc.str[:10]; mk = av.set_index("day")["MK31_valid_share"]
reg = ep.day.map(lambda x: "normal" if mk.get(x, 0) >= 0.9 else ("outage" if mk.get(x, 0) < 0.1 else "partial")).to_numpy()
assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)}
for n, t in [("P3", 7.5), ("P2", 10.5)]:
    a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"
    d = (~yes) & ok & (snr < t); d = d & no if n == "P2" else d; a[d] = "DISMISS"; act[n] = a
num = np.zeros(len(ep)); den = np.zeros(len(ep))
for k in NB:
    q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
defd = den >= 0.45; Dv = np.where(defd, num / np.where(den > 0, den, 1), np.nan)
cg = np.full(len(ep), "ESCALATE", dtype=object); cg[defd & (Dv >= 0.6)] = "ALERT"; cg[defd & (Dv <= 0.16)] = "DISMISS"; act["CG"] = cg
nd = len(av); nout = int((av.MK31_valid_share < 0.1).sum())
def summ(a, m, n):
    return {"assoc": int((assoc & m).sum()), "missed": int(((a == "DISMISS") & assoc & m).sum()),
            "alert_unassoc": int(((a == "ALERT") & ~assoc & m).sum()), "esc_per_day": round(float(((a == "ESCALATE") & m).sum()) / max(n, 1), 2)}
allm = np.ones(len(ep), bool)
res = {"reference": "II.KURK", "neighbours_by_distance_km": {k: dist.get(k) for k in NB}, "weights": W, "days": nd, "outage_days": nout,
       "episodes": len(ep), "episodes_per_day": round(len(ep) / nd, 1),
       "all": {n: summ(a, allm, nd) for n, a in act.items()}, "outage": {n: summ(a, reg == "outage", nout) for n, a in act.items()},
       "all_missing_episodes": int(np.all([S[k] == "MISSING" for k in NB], axis=0).sum())}
json.dump(res, open(os.path.join(D, "..", "ref_kurk_eval.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
