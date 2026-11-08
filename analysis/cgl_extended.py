"""Scoring of PREREGISTRATION_LEARNED_CRITERION.md (repository commit d11004c), written before the extended EQTransformer
output was read. Inputs: extended episodes (results/extended, chunks of extended_eval.json), EQTransformer scores
results/eqt_extended/eqt_extended_episodes.csv (columns set, t_on, det, p, s, n_comp, error; matched on t_on),
frozen parameters results/prereg_cgl_params.json, detectability table (MAKZ).
L1 CG-L vs P3 non-inferiority (episode-date bootstrap, 2000, seed 7, 3 pp); L2 CG-L unassociated alerts < P3;
L3 CG-L escalations per day < CG-D; L4 no episode dropped when EQTransformer failed.
Output: results/eqt_extended/cgl_eval.json
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(root, "results", "prereg", "cgl_params.json"))); W = P["weights"]
T = json.load(open(os.path.join(root, "results", "prereg", "detectability_tables_dev.json")))["MAKZ"]
E = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
ep = pd.concat([pd.read_csv(os.path.join(root, c["source"], "episodes.csv")) for c in E["chunks"]], ignore_index=True)
ep["day"] = ep.t_on_utc.str[:10]
eq = pd.read_csv(os.path.join(root, "results", "eqt_extended", "eqt_extended_episodes.csv")).drop_duplicates("t_on")
m = ep.merge(eq[["t_on", "det", "error"]], on="t_on", how="left")
assert len(m) == len(ep)
assoc = (m.assoc_event >= 0).to_numpy(); snr = m.snr_db.fillna(0).to_numpy(); ok = m.snr_db.notna().to_numpy()
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
NB = ["MK31", "KURK", "WUS"]; S = {k: m[f"n_{k}"].astype(str).to_numpy() for k in NB}
def neighbour_terms(w):
    num = np.zeros(len(m)); den = np.zeros(len(m))
    for k in NB:
        q = np.isin(S[k], ["YES", "NO"]).astype(float)
        p = np.array([T[k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]); q = np.where(S[k] == "NO", p, q)
        num += w[k] * (S[k] == "YES") * q; den += w[k] * q
    return num, den
def decide(num, den, thD, thA=0.60, delta=0.45):
    dd = den >= delta; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(len(m), "ESCALATE", dtype=object); a[dd & (D >= thA)] = "ALERT"; a[dd & (D <= thD)] = "DISMISS"; return a
# CG-L
num, den = neighbour_terms(W); num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
e_ok = m.det.notna().to_numpy() & (m.error.fillna("").astype(str).to_numpy() == ""); e = np.nan_to_num(m.det.to_numpy())
num += W["EQT"] * e * e_ok; den += W["EQT"] * e_ok
cgl = decide(num, den, P["theta_D"])
# CG-D (frozen as in PREREGISTRATION_DETECTABILITY_2024.md)
W2 = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}
n2, d2 = neighbour_terms(W2); n2 += W2["SNR"] * np.clip(snr / 30, 0, 1) * ok; d2 += W2["SNR"] * ok
cgd = decide(n2, d2, 0.16)
yes = np.zeros(len(m), bool)
for k in NB: yes |= S[k] == "YES"
p3 = np.full(len(m), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"
nd = sum(c["days"] for c in E["chunks"])
def summ(a): return {"missed": int(((a == "DISMISS") & assoc).sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
                     "esc_per_day": round(float((a == "ESCALATE").sum()) / nd, 2)}
days = m.day.to_numpy(); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
rng = np.random.default_rng(7); v = []
for _ in range(2000):
    ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
    if len(ids): v.append(((cgl[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
res = {"preregistration": "PREREGISTRATION_LEARNED_CRITERION.md, commit d11004c", "episodes": int(len(m)), "associated": int(assoc.sum()),
       "eqt_scored": int(e_ok.sum()), "eqt_failed_or_missing": int((~e_ok).sum()), "days": nd,
       "CG-L": summ(cgl), "CG-D": summ(cgd), "P3": summ(p3),
       "L1": {"diff_pp": round(float(((cgl[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100), 2), "ci95_pp": ci, "holds": ci[1] <= 3.0},
       "L2": {"CG-L": summ(cgl)["alert_unassoc"], "P3": summ(p3)["alert_unassoc"], "holds": summ(cgl)["alert_unassoc"] < summ(p3)["alert_unassoc"]},
       "L3": {"CG-L": summ(cgl)["esc_per_day"], "CG-D": summ(cgd)["esc_per_day"], "holds": summ(cgl)["esc_per_day"] < summ(cgd)["esc_per_day"]},
       "L4": {"eqt_failed": int((~e_ok).sum()), "decided_or_escalated": int(np.isin(cgl[~e_ok], ["ALERT", "DISMISS", "ESCALATE"]).sum()), "holds": bool(np.isin(cgl[~e_ok], ["ALERT", "DISMISS", "ESCALATE"]).all())}}
json.dump(res, open(os.path.join(root, "results", "eqt_extended", "cgl_eval.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
