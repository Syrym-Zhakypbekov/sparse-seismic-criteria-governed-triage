"""Analyses requested in internal review round R3 (07.11.2026). Development period unless stated; all thresholds FIXED
(no retuning) so that every comparison is a paired, fixed-parameter contrast on the same episodes.
  A  CG mechanism ablations (R3-M03): no evidence gate; MISSING treated as NO; equal neighbour weights; binary SNR score.
  B  controlled masking (R3-M09/M10): on normal days, set MK31 (or KURK, or all neighbours) to MISSING; action transitions.
  C  station subset without WUS (R3-M10).
  D  risk-review-alert frontier (R3-M04): threshold sweeps for P3, P2, CG; best unassociated-alert count at matched
     escalation budgets with missed associated alarms <= 5 and <= 7 (in-sample, descriptive).
  E  association controls (R3-M11): accidental association under catalogue time shifts; tolerance sensitivity;
     regional vs teleseismic outcomes.
  F  calendar-day rates for the held-out period (R3-M01).
Output: results/r3/r3_analyses.json, results/r3/frontier.csv
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "r3"); os.makedirs(OUT, exist_ok=True)
NB = ["MK31", "KURK", "WUS"]
FIX = {"P1t": 8.0, "P2": 10.5, "P3": 7.5, "CG_thD": 0.16, "CG_thA": 0.60, "delta": 0.45, "snr_full": 30.0}
W0 = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}

def load(per):
    ep = pd.read_csv(os.path.join(root, "results", per, "episodes.csv")); ep["day"] = ep.t_on_utc.str[:10]
    av = pd.read_csv(os.path.join(root, "results", per, "availability.csv")).set_index("day")
    mk = [c for c in av.columns if c.startswith("MK31")][0]
    ep["regime"] = ep.day.map(lambda d: "normal" if av.loc[d, mk] >= 0.9 else ("outage" if av.loc[d, mk] < 0.1 else "partial"))
    return ep, len(av)

def states(ep, mask=(), drop=()):
    S = {k: ep[f"n_{k}"].astype(str).to_numpy().copy() for k in NB}
    for k in mask: S[k][:] = "MISSING"
    for k in drop: S[k][:] = "MISSING"
    return S

def act_rules(S, snr, ok, name, tau):
    yes = np.zeros(len(snr), bool); no = np.zeros(len(snr), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    if name == "P1": return np.where(yes, "ALERT", "DISMISS").astype(object)
    if name == "P1t": return np.where(yes | (ok & (snr >= tau)), "ALERT", "DISMISS").astype(object)
    a = np.full(len(snr), "ESCALATE", dtype=object); a[yes & ok & (snr >= tau)] = "ALERT"
    d = (~yes) & ok & (snr < tau)
    if name == "P2": d &= no
    a[d] = "DISMISS"; return a

def act_cg(S, snr, ok, W=W0, delta=0.45, thD=0.16, thA=0.60, full=30.0, missing_as_no=False, snr_binary=None):
    num = np.zeros(len(snr)); den = np.zeros(len(snr))
    for k in NB:
        s = (S[k] == "YES").astype(float); q = np.isin(S[k], ["YES", "NO"]).astype(float)
        if missing_as_no: q = np.ones(len(snr))
        num += W[k] * s * q; den += W[k] * q
    s4 = (ok & (snr >= snr_binary)).astype(float) if snr_binary is not None else np.clip(np.where(ok, snr, 0) / full, 0, 1)
    num += W["SNR"] * s4 * ok; den += W["SNR"] * ok
    defined = den >= delta; D = np.where(defined, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(len(snr), "ESCALATE", dtype=object)
    a[defined & (D >= thA)] = "ALERT"; a[defined & (D <= thD)] = "DISMISS"
    return a

def summ(a, assoc, ndays):
    return {"missed": int(((a == "DISMISS") & assoc).sum()), "assoc": int(assoc.sum()),
            "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()), "escalate": int((a == "ESCALATE").sum()),
            "esc_per_day": round(float((a == "ESCALATE").sum()) / ndays, 2), "dismiss": int((a == "DISMISS").sum())}

def trans(a, b, assoc):
    t = pd.crosstab(pd.Series(a, name="from"), pd.Series(b, name="to"))
    ta = pd.crosstab(pd.Series(a[assoc], name="from"), pd.Series(b[assoc], name="to"))
    return {"all": {f"{i}->{j}": int(t.loc[i, j]) for i in t.index for j in t.columns if i != j and t.loc[i, j]},
            "associated": {f"{i}->{j}": int(ta.loc[i, j]) for i in ta.index for j in ta.columns if i != j and ta.loc[i, j]}}

ep, ndays = load("stage1_v3")
assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
reg = ep.regime.to_numpy(); S0 = states(ep)
res = {"fixed_parameters": FIX, "development_days": ndays}

# A ablations
full = act_cg(S0, snr, ok)
abl = {"CG_full": full, "no_gate (delta=0)": act_cg(S0, snr, ok, delta=0.0),
       "missing_as_NO": act_cg(S0, snr, ok, missing_as_no=True),
       "equal_neighbour_weights": act_cg(S0, snr, ok, W={"MK31": 0.2, "KURK": 0.2, "WUS": 0.2, "SNR": 0.4}),
       "binary_SNR_10dB": act_cg(S0, snr, ok, snr_binary=10.0)}
res["A_ablations"] = {k: {**summ(a, assoc, ndays), "outage_missed": int(((a == "DISMISS") & assoc & (reg == "outage")).sum()),
                          "transitions_from_full": trans(full, a, assoc)} for k, a in abl.items()}

# B controlled masking on normal days
nm = reg == "normal"; ndn = int(len(set(ep.day[nm])))
pol = lambda S: {"P1": act_rules(S, snr, ok, "P1", 0), "P1t": act_rules(S, snr, ok, "P1t", FIX["P1t"]),
                 "P3": act_rules(S, snr, ok, "P3", FIX["P3"]), "P2": act_rules(S, snr, ok, "P2", FIX["P2"]),
                 "CG": act_cg(S, snr, ok)}
base = pol(S0); res["B_masking_normal_days"] = {"normal_days": ndn, "assoc_on_normal_days": int((assoc & nm).sum())}
for label, mask in [("none", ()), ("mask_MK31", ("MK31",)), ("mask_KURK", ("KURK",)), ("mask_all_neighbours", tuple(NB))]:
    P = pol(states(ep, mask=mask)); row = {}
    for n, a in P.items():
        row[n] = {**summ(a[nm], assoc[nm], ndn), "transitions_from_unmasked": trans(base[n][nm], a[nm], assoc[nm])}
    res["B_masking_normal_days"][label] = row

# C without WUS
Pw = pol(states(ep, drop=("WUS",)))
res["C_without_WUS"] = {n: summ(a, assoc, ndays) for n, a in Pw.items()}

# D frontier
rows = []
for t in np.arange(0, 30.5, 0.5):
    for n in ["P3", "P2"]:
        rows.append({"policy": n, "param": f"tau={t}", **summ(act_rules(S0, snr, ok, n, t), assoc, ndays)})
for thD in np.round(np.arange(0, 0.6, 0.02), 2):
    for thA in np.round(np.arange(0.4, 1.0, 0.05), 2):
        if thA <= thD: continue
        rows.append({"policy": "CG", "param": f"thD={thD},thA={thA}", **summ(act_cg(S0, snr, ok, thD=thD, thA=thA), assoc, ndays)})
for t in np.arange(0, 30.5, 0.5):
    rows.append({"policy": "P1t", "param": f"tau={t}", **summ(act_rules(S0, snr, ok, "P1t", t), assoc, ndays)})
F = pd.DataFrame(rows); F.to_csv(os.path.join(OUT, "frontier.csv"), index=False)
budget = {}
for mx in [5, 7]:
    for b in [2.0, 3.0, 4.0, 5.0, 6.0]:
        cell = {}
        for n in ["P1t", "P3", "P2", "CG"]:
            g = F[(F.policy == n) & (F.missed <= mx) & (F.esc_per_day <= b)]
            cell[n] = None if g.empty else int(g.alert_unassoc.min())
        budget[f"missed<={mx}, esc/day<={b}"] = cell
res["D_matched_budget_min_unassoc_alerts_in_sample"] = budget

# E association controls
cat = pd.read_csv(os.path.join(root, "results", "stage1_v3", "catalog.csv"))
cat = cat[cat.makz_valid_at_p.astype(bool)]
ton = ep.t_on.to_numpy(); toff = ep.t_off.to_numpy()
def n_assoc(shift, lo=-15.0, hi_extra=0.0):
    p = cat.p_pred.to_numpy() + shift; hit = np.zeros(len(ep), bool)
    for pp in p:
        m = (pp >= ton + lo) & (pp <= toff + hi_extra); hit |= m
    return int(hit.sum())
real = n_assoc(0.0)
shifts = [s for s in range(-3600, 3601, 300) if abs(s) >= 600]
shifted = [n_assoc(float(s)) for s in shifts]
res["E_association"] = {"associated_episodes_real": real, "mean_associated_under_time_shift": round(float(np.mean(shifted)), 2),
                        "shifts_s": shifts, "per_shift": shifted,
                        "tolerance": {"[-10 s, end]": n_assoc(0, -10), "[-15 s, end] (used)": real, "[-20 s, end]": n_assoc(0, -20),
                                      "[-15 s, end+5 s]": n_assoc(0, -15, 5)}}
kind = ep.assoc_kind.fillna("none").to_numpy(); per_kind = {}
for n, a in base.items():
    per_kind[n] = {k: int(((a == "DISMISS") & assoc & (kind == k)).sum()) for k in ["regional", "tele"]}
res["E_missed_by_kind"] = {"associated_by_kind": {k: int((assoc & (kind == k)).sum()) for k in ["regional", "tele"]}, **per_kind}

# F held-out calendar-day rates (frozen thresholds)
ho, nho = load("heldout"); ha = (ho.assoc_event >= 0).to_numpy(); hs = ho.snr_db.fillna(0).to_numpy(); hk = ho.snr_db.notna().to_numpy()
Sh = states(ho)
res["F_heldout_frozen_calendar_days"] = {"days": nho, **{n: summ(a, ha, nho) for n, a in {
    "P1": act_rules(Sh, hs, hk, "P1", 0), "P1t": act_rules(Sh, hs, hk, "P1t", 8.0), "P2": act_rules(Sh, hs, hk, "P2", 10.5),
    "P3": act_rules(Sh, hs, hk, "P3", 7.5), "CG": act_cg(Sh, hs, hk)}.items()}}
json.dump(res, open(os.path.join(OUT, "r3_analyses.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "B_masking_normal_days"}, indent=1)[:6000])
for lab in ["none", "mask_MK31", "mask_KURK", "mask_all_neighbours"]:
    print(lab, {n: (r["missed"], r["alert_unassoc"], r["esc_per_day"]) for n, r in res["B_masking_normal_days"][lab].items()})
