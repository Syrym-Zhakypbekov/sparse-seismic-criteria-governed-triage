"""P10: compare alarm-triage policies on the v3 development output (results/stage1_v3).

Policies (every MAKZ episode gets one action: ALERT, ESCALATE to analyst, or DISMISS automatically):
  P0  all-to-analyst      : everything ESCALATE (no automation)
  P1  classic coincidence : DISMISS if no neighbour says YES (missing counted as no); else ALERT
                            (= standard network coincidence; silence and absence are the same)
  P2  availability-aware  : q_i strength + m_i validity
        ALERT    if >=1 neighbour YES and SNR >= tau
        DISMISS  if no YES, >=1 neighbour validly NO, and SNR < tau           (non-compensatory veto)
        ESCALATE otherwise: all neighbours MISSING (abstain), or conflict (YES with low SNR, NO with high SNR)
  tau (dB) is chosen on development data as the smallest value keeping >= 95% of catalogue-associated episodes
  out of DISMISS under P2 (it does not use the test period; a held-out test comes later).
Unsafe = a catalogue-associated episode that a policy DISMISSES. Reported separately for normal coverage
(MK31 valid >= 90% of the day) and the outage (MK31 valid < 10%). 95% CI by day-level bootstrap.
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results", "stage1_v3")
ep = pd.read_csv(os.path.join(R, "episodes.csv"))
av = pd.read_csv(os.path.join(R, "availability.csv"))
NEIGH = [c[2:] for c in ep.columns if c.startswith("n_")]
ep["day"] = ep["t_on_utc"].str[:10]
ep["assoc"] = ep.assoc_event >= 0
ep["assoc_reg"] = ep.assoc & ep.assoc_kind.eq("regional")
yes = ep[[f"n_{k}" for k in NEIGH]].eq("YES").any(axis=1)
no = ep[[f"n_{k}" for k in NEIGH]].eq("NO").any(axis=1)
allmiss = ep[[f"n_{k}" for k in NEIGH]].eq("MISSING").all(axis=1)
snr = ep.snr_db.fillna(-np.inf)

def p2(tau):
    act = np.full(len(ep), "ESCALATE", dtype=object)
    act[(yes & (snr >= tau)).to_numpy()] = "ALERT"
    act[((~yes) & no & (snr < tau)).to_numpy()] = "DISMISS"
    return act

cands = np.arange(0, 30.5, 0.5)
def p1t(tau):
    """tuned coincidence baseline: ALERT if a neighbour says YES or SNR >= tau; else DISMISS (missing counted as no)"""
    return np.where(yes | (snr >= tau), "ALERT", "DISMISS").astype(object)
def pick_tau(policy, rows):
    """largest tau keeping >= 95 % of catalogue-associated episodes in `rows` out of DISMISS"""
    a = ep.assoc.to_numpy() & rows
    best = 0.0
    for t in cands:
        if not a.any() or (policy(t)[a] != "DISMISS").mean() >= 0.95:
            best = float(t)
    return best
allrows = np.ones(len(ep), bool)
tau = pick_tau(p2, allrows)          # in-sample (reported only as a reference)
tau_p1t = pick_tau(p1t, allrows)
# day-blocked 5-fold cross-validation: tau for each fold is chosen on the other folds only
days_sorted = np.array(sorted(ep.day.unique()))
fold_of_day = {d: i % 5 for i, d in enumerate(days_sorted)}
fold = ep.day.map(fold_of_day).to_numpy()
cv_p2 = np.empty(len(ep), dtype=object); cv_p1t = np.empty(len(ep), dtype=object); cv_taus = []
for k in range(5):
    tr, te = fold != k, fold == k
    t2, t1 = pick_tau(p2, tr), pick_tau(p1t, tr)
    cv_taus.append({"fold": k, "tau_P2": t2, "tau_P1tuned": t1})
    cv_p2[te] = p2(t2)[te]; cv_p1t[te] = p1t(t1)[te]
pol = {"P0_all_to_analyst": np.full(len(ep), "ESCALATE", dtype=object),
       "P1_classic_coincidence": np.where(yes, "ALERT", "DISMISS").astype(object),
       "P1t_tuned_coincidence_cv": cv_p1t,
       "P2_availability_aware_cv": cv_p2,
       "P2_availability_aware_insample": p2(tau)}

avd = av.set_index("day")
mk = [c for c in av.columns if c.startswith("MK31")]
regime = {}
for d in av.day:
    s = float(avd.loc[d, mk[0]]) if mk else 1.0
    regime[d] = "normal" if s >= 0.9 else ("outage" if s < 0.1 else "partial")
ep["regime"] = ep.day.map(regime)
rng = np.random.default_rng(7)

def metrics(act, mask, ndays):
    a = act[mask.to_numpy()]; e = ep[mask]
    out = {"episodes": int(mask.sum()), "per_day": len(a) / max(1, ndays),
           "alert": int((a == "ALERT").sum()), "escalate": int((a == "ESCALATE").sum()), "dismiss": int((a == "DISMISS").sum()),
           "analyst_per_day": float(((a == "ESCALATE").sum()) / max(1, ndays)),
           "automated_share": float(np.mean(a != "ESCALATE")) if len(a) else np.nan,
           "assoc": int(e.assoc.sum()), "unsafe_dismissed_assoc": int((a[e.assoc.to_numpy()] == "DISMISS").sum()),
           "unsafe_dismissed_regional": int((a[e.assoc_reg.to_numpy()] == "DISMISS").sum())}
    # day bootstrap CI for unsafe rate among associated episodes
    if e.assoc.any():
        # day-level bootstrap on per-day counts (vectorised: resample days, sum numerators/denominators)
        dis = pd.Series(a == "DISMISS", index=e.index) & e.assoc
        per = pd.DataFrame({"n": e.assoc.groupby(e.day).sum(), "k": dis.groupby(e.day).sum()})
        n_d, k_d = per.n.to_numpy(float), per.k.to_numpy(float)
        pick = rng.integers(0, len(per), size=(2000, len(per)))
        den = n_d[pick].sum(1); num = k_d[pick].sum(1)
        vals = (num[den > 0] / den[den > 0]).tolist()
        out["unsafe_rate"] = float(np.mean(act[mask.to_numpy()][e.assoc.to_numpy()] == "DISMISS"))
        out["unsafe_rate_ci95"] = [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else None
    return out

res = {"tau_db_insample": tau, "tau_p1t_insample": tau_p1t, "cv_taus": cv_taus, "neighbours": NEIGH, "days_by_regime": pd.Series(regime).value_counts().to_dict(), "policies": {}}
for name, act in pol.items():
    res["policies"][name] = {}
    for rg in ("all", "normal", "outage"):
        mask = pd.Series(True, index=ep.index) if rg == "all" else ep.regime.eq(rg)
        nd = len(av) if rg == "all" else sum(1 for v in regime.values() if v == rg)
        res["policies"][name][rg] = metrics(act, mask, nd)
for k_, v_ in pol.items(): ep["action_" + k_] = v_
ep.to_csv(os.path.join(R, "episodes_policies.csv"), index=False)
json.dump(res, open(os.path.join(R, "policies.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
