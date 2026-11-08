"""Analyses requested in internal review round R2 (07.11.2026), all on the existing development episodes.
R2-M02 mechanism ablation / R2-M04 equally informed baseline:
  P3 availability-blind abstaining rule = P2 without the "valid NO" condition:
     ALERT if any YES and SNR >= tau; DISMISS if no YES and SNR < tau; otherwise ESCALATE.
  P3 and P2 have the same actions and the same information except neighbour validity, so P2 - P3 isolates
  the availability mechanism; P3 - P1t isolates abstention.
R2-M06 contiguous blocked CV: 5 consecutive day blocks (not interleaved days); tau chosen on the other 4 blocks.
  Paired day bootstrap of DIFFERENCES between policies (same resampled days for both).
R2-M10 invalid SNR: treated as unknown -> never DISMISS (escalate), not as -inf.
Output: results/stage1_v3/r2_analyses.json and printed table.
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results", "stage1_v3")
ep = pd.read_csv(os.path.join(R, "episodes.csv"))
av = pd.read_csv(os.path.join(R, "availability.csv")).set_index("day")
NB = [c[2:] for c in ep.columns if c.startswith("n_")]
ep["day"] = ep.t_on_utc.str[:10]
assoc = (ep.assoc_event >= 0).to_numpy()
yes = ep[[f"n_{k}" for k in NB]].eq("YES").any(axis=1).to_numpy()
no = ep[[f"n_{k}" for k in NB]].eq("NO").any(axis=1).to_numpy()
snr_ok = ep.snr_db.notna().to_numpy()
snr = ep.snr_db.fillna(0).to_numpy()
mk = [c for c in av.columns if c.startswith("MK31")][0]
regime = ep.day.map(lambda d: "normal" if av.loc[d, mk] >= 0.9 else ("outage" if av.loc[d, mk] < 0.1 else "partial")).to_numpy()

def P1(t):  return np.where(yes, "ALERT", "DISMISS").astype(object)
def P1t(t): return np.where(yes | (snr_ok & (snr >= t)), "ALERT", "DISMISS").astype(object)
def P2(t):
    a = np.full(len(ep), "ESCALATE", dtype=object)
    a[yes & snr_ok & (snr >= t)] = "ALERT"
    a[(~yes) & no & snr_ok & (snr < t)] = "DISMISS"
    return a
def P3(t):
    a = np.full(len(ep), "ESCALATE", dtype=object)
    a[yes & snr_ok & (snr >= t)] = "ALERT"
    a[(~yes) & snr_ok & (snr < t)] = "DISMISS"
    return a

cands = np.arange(0, 30.5, 0.5)
def pick(pol, rows):
    a = assoc & rows; best = 0.0
    for t in cands:
        if not a.any() or (pol(t)[a] != "DISMISS").mean() >= 0.95:
            best = float(t)
    return best

days = np.array(sorted(ep.day.unique()))
blocks = np.array_split(days, 5)                       # contiguous blocks
blk = ep.day.map({d: i for i, b in enumerate(blocks) for d in b}).to_numpy()
pols = {"P1": P1, "P1t": P1t, "P2": P2, "P3": P3}
act, taus = {}, {}
for name, f in pols.items():
    a = np.empty(len(ep), dtype=object); taus[name] = []
    for k in range(5):
        tr, te = blk != k, blk == k
        t = pick(f, tr) if name != "P1" else 0.0
        taus[name].append(t); a[te] = f(t)[te]
    act[name] = a

def summary(a, m):
    d = ep.day.to_numpy()[m]; aa = a[m]; asc = assoc[m]; nd = len(set(d))
    return {"unsafe": int(((aa == "DISMISS") & asc).sum()), "assoc": int(asc.sum()),
            "alert": int((aa == "ALERT").sum()), "alert_unassoc": int(((aa == "ALERT") & ~asc).sum()),
            "escalate": int((aa == "ESCALATE").sum()), "esc_per_day": round(float((aa == "ESCALATE").sum()) / max(1, nd), 2),
            "retained_unassoc": int(((aa != "DISMISS") & ~asc).sum())}

out = {"cv": "5 contiguous day blocks", "taus": taus, "policies": {}, "paired_differences": {}}
for name in pols:
    out["policies"][name] = {rg: summary(act[name], (regime == rg) if rg != "all" else np.ones(len(ep), bool))
                             for rg in ("all", "normal", "outage")}

# paired day bootstrap of differences
rng = np.random.default_rng(7); dlist = ep.day.to_numpy(); udays = days
idx_by_day = {d: np.where(dlist == d)[0] for d in udays}
def stat(a, ids):
    return np.array([((a[ids] == "DISMISS") & assoc[ids]).sum(), ((a[ids] == "ALERT") & ~assoc[ids]).sum()])
for A, B in [("P2", "P1t"), ("P2", "P3"), ("P3", "P1t"), ("P2", "P1")]:
    diffs = []
    for _ in range(2000):
        pick_days = rng.choice(udays, len(udays), replace=True)
        ids = np.concatenate([idx_by_day[d] for d in pick_days])
        diffs.append(stat(act[A], ids) - stat(act[B], ids))
    diffs = np.array(diffs); allids = np.arange(len(ep))
    obs = stat(act[A], allids) - stat(act[B], allids)
    out["paired_differences"][f"{A}-{B}"] = {
        "unsafe_diff": int(obs[0]), "unsafe_ci95": [float(np.percentile(diffs[:, 0], 2.5)), float(np.percentile(diffs[:, 0], 97.5))],
        "unassoc_alert_diff": int(obs[1]), "unassoc_alert_ci95": [float(np.percentile(diffs[:, 1], 2.5)), float(np.percentile(diffs[:, 1], 97.5))]}
# R2-M01: how often P2 dismisses while a neighbour is MISSING
missing_any = ep[[f"n_{k}" for k in NB if k != "WUS"]].eq("MISSING").any(axis=1).to_numpy()
out["P2_dismiss_with_missing_neighbour"] = {"episodes": int(((act["P2"] == "DISMISS") & missing_any).sum()),
                                            "associated": int(((act["P2"] == "DISMISS") & missing_any & assoc).sum())}
# R2-M12: confirmation latency implied by the neighbour windows (d / 5.5 km/s + 5 s)
dist = {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}
out["confirmation_window_s"] = {k: round(v / 5.5 + 5, 1) for k, v in dist.items()}
json.dump(out, open(os.path.join(R, "r2_analyses.json"), "w"), indent=1)
for name in pols:
    for rg in ("all", "outage"):
        s = out["policies"][name][rg]
        print(f"{name:4s} {rg:6s} unsafe {s['unsafe']:2d}/{s['assoc']:3d}  alert {s['alert']:4d}  alert_unassoc {s['alert_unassoc']:4d}  esc/day {s['esc_per_day']:5.2f}  retained_unassoc {s['retained_unassoc']}")
print("taus", taus)
for k, v in out["paired_differences"].items(): print(k, v)
print("P2 dismiss with MISSING neighbour:", out["P2_dismiss_with_missing_neighbour"], "| windows:", out["confirmation_window_s"])
