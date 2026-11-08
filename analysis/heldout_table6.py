"""Authoritative entry point for Table 6 (held-out period 2026-10-01..2026-11-06 (dates from results/heldout/availability.csv), review R6-M04): all five policies with the frozen
thresholds (P1t 8.0, P2 10.5 dB from PREREGISTRATION.md; P3 7.5 dB; CG theta_D 0.16, theta_A 0.60, delta 0.45) and the
37-calendar-day denominator from results/heldout/availability.csv.
Output: results/heldout/table6.json.
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(root, "results", "heldout")
ep = pd.read_csv(os.path.join(H, "episodes.csv")); nd = len(pd.read_csv(os.path.join(H, "availability.csv")))
NB = ["MK31", "KURK", "WUS"]; W = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}
assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)}
for n, t in [("P2", 10.5), ("P3", 7.5)]:
    a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"
    d = (~yes) & ok & (snr < t); d = d & no if n == "P2" else d; a[d] = "DISMISS"; act[n] = a
num = np.zeros(len(ep)); den = np.zeros(len(ep))
for k in NB:
    q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
assert 0.16 < 0.60
cg = np.full(len(ep), "ESCALATE", dtype=object); cg[dd & (D >= 0.60)] = "ALERT"; cg[dd & (D <= 0.16)] = "DISMISS"; act["CG"] = cg
tab = {n: {"assoc_dismissed": int(((a == "DISMISS") & assoc).sum()), "unassoc_alerts": int(((a == "ALERT") & ~assoc).sum()),
           "escalations": int((a == "ESCALATE").sum()), "esc_per_day": round(float((a == "ESCALATE").sum()) / nd, 2)} for n, a in act.items()}
out = {"episodes": int(len(ep)), "associated": int(assoc.sum()), "calendar_days": nd, "table6": tab}
json.dump(out, open(os.path.join(H, "table6.json"), "w"), indent=1); print(json.dumps(out, indent=1))
