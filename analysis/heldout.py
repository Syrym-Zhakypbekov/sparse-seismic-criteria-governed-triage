"""P10 held-out scoring with thresholds FROZEN from the development period (PREREGISTRATION.md, commit cc0b46f).
Input: results/heldout/{episodes,availability}.csv from the held-out Kaggle run. No threshold is chosen here.
Output: results/heldout/heldout_policies.json + episodes_policies.csv. Run once.
"""
import os, json
import numpy as np, pandas as pd

TAU_P2, TAU_P1T = 10.5, 8.0          # frozen (development in-sample values), do not change
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results", "heldout")
ep = pd.read_csv(os.path.join(R, "episodes.csv"))
av = pd.read_csv(os.path.join(R, "availability.csv")).set_index("day")
NEIGH = [c[2:] for c in ep.columns if c.startswith("n_")]
ep["day"] = ep["t_on_utc"].str[:10]
ep["assoc"] = ep.assoc_event >= 0
yes = ep[[f"n_{k}" for k in NEIGH]].eq("YES").any(axis=1).to_numpy()
no = ep[[f"n_{k}" for k in NEIGH]].eq("NO").any(axis=1).to_numpy()
snr = ep.snr_db.fillna(-np.inf).to_numpy()

p2 = np.full(len(ep), "ESCALATE", dtype=object)
p2[yes & (snr >= TAU_P2)] = "ALERT"
p2[(~yes) & no & (snr < TAU_P2)] = "DISMISS"
pol = {"P1_classic_coincidence": np.where(yes, "ALERT", "DISMISS").astype(object),
       "P1t_tuned_coincidence": np.where(yes | (snr >= TAU_P1T), "ALERT", "DISMISS").astype(object),
       "P2_availability_aware": p2}

mk = [c for c in av.columns if c.startswith("MK31")]
regime = {d: ("normal" if (float(av.loc[d, mk[0]]) if mk else 1) >= 0.9 else
              ("outage" if (float(av.loc[d, mk[0]]) if mk else 1) < 0.1 else "partial")) for d in av.index}
ep["regime"] = ep.day.map(regime)
rng = np.random.default_rng(7)

def metrics(a, m, ndays):
    e = ep[m]; a = a[m.to_numpy()]
    out = {"episodes": int(m.sum()), "days": ndays, "alert": int((a == "ALERT").sum()),
           "escalate": int((a == "ESCALATE").sum()), "dismiss": int((a == "DISMISS").sum()),
           "analyst_per_day": float((a == "ESCALATE").sum() / max(1, ndays)),
           "assoc": int(e.assoc.sum()), "unsafe": int((a[e.assoc.to_numpy()] == "DISMISS").sum()),
           "unassoc_alerts": int(((a == "ALERT") & ~e.assoc.to_numpy()).sum())}
    if e.assoc.any():
        dis = pd.Series(a == "DISMISS", index=e.index) & e.assoc
        per = pd.DataFrame({"n": e.assoc.groupby(e.day).sum(), "k": dis.groupby(e.day).sum()})
        pick = rng.integers(0, len(per), size=(2000, len(per)))
        den = per.n.to_numpy(float)[pick].sum(1); num = per.k.to_numpy(float)[pick].sum(1)
        v = num[den > 0] / den[den > 0]
        out["unsafe_rate"] = out["unsafe"] / out["assoc"]
        out["unsafe_rate_ci95"] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return out

res = {"frozen": {"tau_P2": TAU_P2, "tau_P1t": TAU_P1T}, "days_by_regime": pd.Series(regime).value_counts().to_dict(), "policies": {}}
for name, a in pol.items():
    res["policies"][name] = {}
    for rg in ("all", "normal", "outage"):
        m = pd.Series(True, index=ep.index) if rg == "all" else ep.regime.eq(rg)
        nd = len(regime) if rg == "all" else sum(v == rg for v in regime.values())
        if m.any():
            res["policies"][name][rg] = metrics(a, m, nd)
    ep["action_" + name] = a
ep.to_csv(os.path.join(R, "episodes_policies.csv"), index=False)
json.dump(res, open(os.path.join(R, "heldout_policies.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
