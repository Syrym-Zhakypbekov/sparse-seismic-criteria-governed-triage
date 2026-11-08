"""The dissertation's criteria-governed model (chapter 2, section 2.7, formulas 2.25-2.31) applied to seismic alarms.

Criteria c_i for an alarm x at IU.MAKZ:
  c_MK31, c_KURK, c_WUS  neighbour confirmation: s_i = 1 if the neighbour triggered in its window (YES), 0 if it recorded
                         without a trigger (NO); data quality q_i = 1 if the window is valid (YES/NO), 0 if MISSING.
  c_SNR                  signal strength at MAKZ: s = clip(SNR_dB / SNR_FULL, 0, 1); q = 1 if SNR was computed, else 0.
Aggregate (2.25):  D(x) = sum w_i s_i q_i / sum w_i q_i  if  sum w_i q_i >= delta,  else  D(x) = bottom (no decision).
Effective weights:  w_i^eff = w_i q_i / sum_j w_j q_j  (Statement 2.2: sum w_i^eff s_i = D).
Actions: D = bottom -> ESCALATE (condition E5);  D >= theta_A -> ALERT;  D <= theta_D -> DISMISS;  otherwise ESCALATE (band).
delta > w_SNR means: signal strength alone can never produce a decision; at least one valid neighbour record is needed.
theta_D is chosen by 5-fold contiguous-block CV (largest value that keeps >= 95 % of catalogue-associated alarms out of
DISMISS on the training blocks), as for the other policies. Statements 2.2, 2.3 and 2.5 are checked numerically on every
alarm and the ledger of contributions is written per episode.
Outputs: results/dissertation_model/{dm_summary.json, dm_ledger_dev.csv, dm_ledger_heldout.csv}
"""
import os, json
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "criteria_governed"); os.makedirs(OUT, exist_ok=True)
NB = ["MK31", "KURK", "WUS"]
W = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}       # sum = 1; nearer neighbour weighs more
DELTA = 0.45                                                     # > w_SNR = 0.40
SNR_FULL = 30.0
THETA_A = 0.60
CANDS = np.round(np.arange(0.0, THETA_A - 0.005, 0.01), 2)   # theta_D < theta_A strictly

def criteria(ep):
    S = {}; Q = {}
    for k in NB:
        st = ep[f"n_{k}"].astype(str).to_numpy()
        S[k] = (st == "YES").astype(float); Q[k] = np.isin(st, ["YES", "NO"]).astype(float)
    ok = ep.snr_db.notna().to_numpy()
    S["SNR"] = np.clip(ep.snr_db.fillna(0).to_numpy() / SNR_FULL, 0, 1); Q["SNR"] = ok.astype(float)
    return S, Q

def model(ep):
    S, Q = criteria(ep); keys = list(W)
    den = sum(W[k] * Q[k] for k in keys)
    num = sum(W[k] * S[k] * Q[k] for k in keys)
    defined = den >= DELTA
    D = np.where(defined, num / np.where(den > 0, den, 1), np.nan)
    weff = {k: np.where(den > 0, W[k] * Q[k] / np.where(den > 0, den, 1), 0.0) for k in keys}
    return S, Q, den, D, defined, weff

def act(D, defined, theta_d):
    assert theta_d < THETA_A, "theta_D must be < theta_A"
    a = np.full(len(D), "ESCALATE", dtype=object)
    a[defined & (D >= THETA_A)] = "ALERT"
    a[defined & (D <= theta_d)] = "DISMISS"
    return a

def pick(D, defined, assoc, rows):
    best = 0.0; m = assoc & rows
    for t in CANDS:
        if (act(D, defined, t)[m] != "DISMISS").mean() >= 0.95: best = float(t)
    return best

def summ(a, assoc, days):
    nd = len(set(days))
    return {"n": int(len(a)), "assoc": int(assoc.sum()),
            "missed_assoc": int(((a == "DISMISS") & assoc).sum()),
            "alert": int((a == "ALERT").sum()), "alert_unassoc": int(((a == "ALERT") & ~assoc).sum()),
            "escalate": int((a == "ESCALATE").sum()), "esc_per_day": round(float((a == "ESCALATE").sum()) / max(nd, 1), 2),
            "dismiss": int((a == "DISMISS").sum())}

def run(path, theta_fixed=None):
    ep = pd.read_csv(path); ep["day"] = ep.t_on_utc.str[:10]
    assoc = (ep.assoc_event >= 0).to_numpy()
    S, Q, den, D, defined, weff = model(ep)
    if theta_fixed is None:
        days = np.array(sorted(ep.day.unique())); blocks = np.array_split(days, 5)
        blk = ep.day.map({d: i for i, b in enumerate(blocks) for d in b}).to_numpy()
        a = np.empty(len(ep), dtype=object); thetas = []
        for k in range(5):
            t = pick(D, defined, assoc, blk != k); thetas.append(t); a[blk == k] = act(D, defined, t)[blk == k]
    else:
        thetas = [theta_fixed]; a = act(D, defined, theta_fixed)
    # numerical checks of the dissertation statements on every defined decision
    dd = defined
    recon = sum(weff[k] * S[k] for k in W)                                  # Statement 2.2
    err22 = float(np.nanmax(np.abs(recon[dd] - D[dd]))) if dd.any() else 0.0
    sumw = sum(weff[k] for k in W)
    err23 = float(np.nanmax(np.abs(sumw[dd] - 1))) if dd.any() else 0.0    # Statement 2.3: weights sum to 1
    lo = np.min(np.vstack([np.where(Q[k] > 0, S[k], np.inf) for k in W]), axis=0)
    hi = np.max(np.vstack([np.where(Q[k] > 0, S[k], -np.inf) for k in W]), axis=0)
    bound_ok = bool(np.all((D[dd] >= lo[dd] - 1e-12) & (D[dd] <= hi[dd] + 1e-12)))
    grad = np.max(np.vstack([np.abs(W[k] * (S[k] - np.nan_to_num(D)) / np.where(den > 0, den, 1)) for k in W]), axis=0)
    sens_ok = bool(np.all(grad[dd] <= 1 / DELTA + 1e-12))                   # Statement 2.5: |dD/dq_i| <= 1/delta
    e5_only = int((~defined).sum())
    ledger = pd.DataFrame({"t_on_utc": ep.t_on_utc, "assoc": assoc, "den": den, "D": D, "action": a,
                           **{f"s_{k}": S[k] for k in W}, **{f"q_{k}": Q[k] for k in W},
                           **{f"contrib_{k}": weff[k] * S[k] for k in W}})
    return ledger, {"thetas_D": thetas, "policy": summ(a, assoc, ep.day.to_numpy()),
                    "checks": {"stmt2_2_max_abs_error": err22, "stmt2_3_weights_sum_err": err23,
                               "stmt2_3_D_within_min_max": bound_ok, "stmt2_5_grad_le_1_over_delta": sens_ok},
                    "E5_undefined_escalations": e5_only}

dev_led, dev = run(os.path.join(root, "results", "stage1_v3", "episodes.csv"))
theta_final = float(np.median(dev["thetas_D"]))
ho_led, ho = run(os.path.join(root, "results", "heldout", "episodes_policies.csv"), theta_fixed=theta_final)
dev_led.to_csv(os.path.join(OUT, "dm_ledger_dev.csv"), index=False); ho_led.to_csv(os.path.join(OUT, "dm_ledger_heldout.csv"), index=False)
res = {"weights": W, "delta": DELTA, "snr_full_db": SNR_FULL, "theta_A": THETA_A, "theta_D_heldout": theta_final,
       "development_cv": dev, "heldout_exploratory": ho,
       "note": "held-out use of this model is exploratory: the model was specified after the pre-registration of P2"}
json.dump(res, open(os.path.join(OUT, "dm_summary.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
