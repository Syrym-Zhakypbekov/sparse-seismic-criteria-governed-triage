"""Scoring of PREREGISTRATION_EXTENDED.md (repository commit 84e93ce, 2026-11-07 16:38 +05): frozen detector, frozen policies.
Chunks: results/extended/vm_2025/out_* (Google Cloud VM) and results/extended/kaggle_2026h1 (Kaggle).
A chunk whose summary lists catalogue failures, or whose regional catalogue count is implausibly low, is reported but
excluded from E1-E3 until it is re-run (results/extended/vm_2025_rerun/ replaces it when present).
Hypotheses:
 E1 outage days (MK31 valid < 10 %): CG dismisses fewer associated alarms than P1
 E2 whole period: CG forwards fewer unassociated alerts than P3 and than P1t
 E3 non-inferiority: upper bound of the 95 % paired day-bootstrap interval of (missed share CG - missed share P3) <= 3 pp
 E4 every episode with all neighbours MISSING is escalated by CG
Output: results/extended/extended_eval.json
"""
import os, json, glob
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = os.path.join(root, "results", "extended")
NB = ["MK31", "KURK", "WUS"]; W = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}
TAU = {"P1t": 8.0, "P2": 10.5, "P3": 7.5}; DELTA, THA, THD, FULL = 0.45, 0.60, 0.16, 30.0

chunks = sorted(glob.glob(os.path.join(E, "vm_2025", "out_*"))) + [os.path.join(E, "kaggle_2026h1")]
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
frames, chunk_info = [], []
for d in chunks:
    name = os.path.basename(d); src = d
    if name in rerun: src = rerun[name]
    s = json.load(open(os.path.join(src, "summary.json")))
    fails = s.get("catalog_failures", [])
    log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(src, "*.log")))
    if "regional catalog error" in log and not s.get("catalog_failures") and "catalog_failures" not in s:
        fails = ["ISC (rate limit, first run)"]
    usable = not fails
    ep = pd.read_csv(os.path.join(src, "episodes.csv")); av = pd.read_csv(os.path.join(src, "availability.csv"))
    ep["day"] = ep.t_on_utc.str[:10]; mk = av.set_index("day")["MK31_valid_share"]
    ep["regime"] = ep.day.map(lambda x: "normal" if mk.get(x, 0) >= 0.9 else ("outage" if mk.get(x, 0) < 0.1 else "partial"))
    ep["chunk"] = name; ep["usable"] = usable
    frames.append(ep)
    chunk_info.append({"chunk": name, "source": os.path.relpath(src, root), "days": len(av), "episodes": len(ep),
                       "per_day": round(len(ep) / len(av), 1), "regional_catalog": s["catalog"]["regional"],
                       "outage_days": int((av.MK31_valid_share < 0.1).sum()), "normal_days": int((av.MK31_valid_share >= 0.9).sum()), "catalog_failures": fails, "usable": usable,
                       "days_list": av.day.tolist()})
ep = pd.concat(frames, ignore_index=True)
assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object),
       "P1t": np.where(yes | (ok & (snr >= TAU["P1t"])), "ALERT", "DISMISS").astype(object)}
for n in ["P3", "P2"]:
    a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= TAU[n])] = "ALERT"
    d = (~yes) & ok & (snr < TAU[n]); d = d & no if n == "P2" else d; a[d] = "DISMISS"; act[n] = a
num = np.zeros(len(ep)); den = np.zeros(len(ep))
for k in NB:
    s_ = (S[k] == "YES").astype(float); q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * s_ * q; den += W[k] * q
num += W["SNR"] * np.clip(snr / FULL, 0, 1) * ok; den += W["SNR"] * ok
defined = den >= DELTA; D = np.where(defined, num / np.where(den > 0, den, 1), np.nan)
cg = np.full(len(ep), "ESCALATE", dtype=object); cg[defined & (D >= THA)] = "ALERT"; cg[defined & (D <= THD)] = "DISMISS"; act["CG"] = cg

use = ep.usable.to_numpy(); reg = ep.regime.to_numpy(); days = ep.day.to_numpy()
ndays_use = sum(len(c["days_list"]) for c in chunk_info if c["usable"])
def summ(a, m, nd):
    return {"episodes": int(m.sum()), "assoc": int((assoc & m).sum()), "missed": int(((a == "DISMISS") & assoc & m).sum()),
            "alert_unassoc": int(((a == "ALERT") & ~assoc & m).sum()), "escalate": int(((a == "ESCALATE") & m).sum()),
            "esc_per_day": round(float(((a == "ESCALATE") & m).sum()) / max(nd, 1), 2)}
out_days = sum(c["outage_days"] for c in chunk_info if c["usable"])
res = {"preregistration": "PREREGISTRATION_EXTENDED.md, commit 84e93ce", "chunks": [{k: v for k, v in c.items() if k != "days_list"} for c in chunk_info],
       "usable_days": ndays_use, "outage_days_usable": out_days,
       "all_usable": {n: summ(a, use, ndays_use) for n, a in act.items()},
       "outage_usable": {n: summ(a, use & (reg == "outage"), out_days) for n, a in act.items()},
       "normal_usable": {n: summ(a, use & (reg == "normal"), sum(c["normal_days"] for c in chunk_info if c["usable"])) for n, a in act.items()}}
# E1
o = res["outage_usable"]
res["E1"] = {"testable": o["CG"]["assoc"] > 0, "CG_missed": o["CG"]["missed"], "P1_missed": o["P1"]["missed"], "assoc": o["CG"]["assoc"],
             "holds": (o["CG"]["missed"] < o["P1"]["missed"]) if o["CG"]["assoc"] > 0 else None}
# E2
a_ = res["all_usable"]
res["E2"] = {"CG": a_["CG"]["alert_unassoc"], "P3": a_["P3"]["alert_unassoc"], "P1t": a_["P1t"]["alert_unassoc"],
             "holds": a_["CG"]["alert_unassoc"] < a_["P3"]["alert_unassoc"] and a_["CG"]["alert_unassoc"] < a_["P1t"]["alert_unassoc"]}
# E3 paired day bootstrap of the missed-share difference
rng = np.random.default_rng(7); ud = np.array(sorted(set(days[use]))); idx = {d: np.where((days == d) & use & assoc)[0] for d in ud}
diffs = []
for _ in range(2000):
    ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
    if len(ids) == 0: continue
    diffs.append(((act["CG"][ids] == "DISMISS").mean() - (act["P3"][ids] == "DISMISS").mean()) * 100)
obs = ((act["CG"][use & assoc] == "DISMISS").mean() - (act["P3"][use & assoc] == "DISMISS").mean()) * 100
res["E3"] = {"diff_pp": round(float(obs), 2), "ci95_pp": [round(float(np.percentile(diffs, 2.5)), 2), round(float(np.percentile(diffs, 97.5)), 2)],
             "margin_pp": 3.0, "holds": float(np.percentile(diffs, 97.5)) <= 3.0}
# E4 (all chunks, catalogue not needed)
allmiss = np.ones(len(ep), bool)
for k in NB: allmiss &= S[k] == "MISSING"
res["E4"] = {"all_missing_episodes": int(allmiss.sum()), "escalated": int((cg[allmiss] == "ESCALATE").sum()),
             "holds": (bool((cg[allmiss] == "ESCALATE").all()) if allmiss.any() else None), "note": "not exercised" if not allmiss.any() else ""}
json.dump(res, open(os.path.join(E, "extended_eval.json"), "w"), indent=1)
for c in res["chunks"]: print(c)
print("usable days", ndays_use, "outage days", out_days)
for n in act: print(n, "all", res["all_usable"][n], "| outage", res["outage_usable"][n])
for h in ["E1", "E2", "E3", "E4"]: print(h, res[h])
