"""Regional reference labels from NNC/KNDC via the ISC FDSN event service (ANALYSIS_PLAN_NNC.md, commit 9ad4cc0).
Step 1 (cached): download NNC events within 6 deg of IU.MAKZ, 2025-01..2026-02, month by month (serial, retries).
Step 2: predicted first P at IU.MAKZ (TauP iasp91), associate extended-test episodes with [t_on-15 s, t_off].
Step 3: per frozen policy, dismissal shares for NNC earthquakes / NNC mining explosions, alerts with no event at all,
        CG-P3 difference in dismissed share with NNC earthquakes as reference (paired day bootstrap, 2000, seed 7).
Outputs: results/nnc/nnc_events.csv, results/nnc/nnc_eval.json
"""
import os, json, time, glob
import numpy as np, pandas as pd
from obspy import UTCDateTime, read_events
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "nnc"); os.makedirs(OUT, exist_ok=True)
REF = (46.808, 81.977); model = TauPyModel("iasp91")
fe = os.path.join(OUT, "nnc_events.csv")
if not os.path.exists(fe):
    rows = []; m0 = UTCDateTime("2025-01-01")
    while m0 < UTCDateTime("2026-03-01"):
        m1 = UTCDateTime(m0.year + (m0.month == 12), m0.month % 12 + 1, 1)
        url = (f"https://www.isc.ac.uk/fdsnws/event/1/query?starttime={m0.date}&endtime={m1.date}"
               f"&latitude={REF[0]}&longitude={REF[1]}&maxradius=6&contributor=NNC")
        for att in range(6):
            try:
                cat = read_events(url); break
            except Exception as e:
                print(m0.date, "retry", att, str(e)[:100], flush=True); time.sleep(30 * (att + 1)); cat = None
        if cat is None: raise SystemExit(f"failed month {m0.date}")
        for ev in cat:
            o = ev.preferred_origin() or ev.origins[0]; mg = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
            deg = gps2dist_azimuth(REF[0], REF[1], o.latitude, o.longitude)[0] / 111195
            arr = model.get_travel_times(source_depth_in_km=max((o.depth or 0) / 1000, 0), distance_in_degree=deg, phase_list=["p", "P", "Pn", "Pg"])
            rows.append({"time": float(o.time), "lat": o.latitude, "lon": o.longitude, "depth_km": (o.depth or 0) / 1000,
                         "mag": mg.mag if mg else np.nan, "mag_type": mg.magnitude_type if mg else "", "type": str(ev.event_type),
                         "dist_deg": deg, "p_pred": float(o.time + min(a.time for a in arr)) if arr else np.nan})
        print(m0.date, len(cat), flush=True); m0 = m1; time.sleep(5)
    pd.DataFrame(rows).to_csv(fe, index=False)
nnc = pd.read_csv(fe).dropna(subset=["p_pred"]).sort_values("p_pred").reset_index(drop=True)

E = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
frames = []
for c in E["chunks"]:
    x = pd.read_csv(os.path.join(root, c["source"], "episodes.csv")); frames.append(x)
ep = pd.concat(frames, ignore_index=True)
ep = ep[ep.t_on < UTCDateTime("2026-03-01").timestamp].reset_index(drop=True); ep["day"] = ep.t_on_utc.str[:10]
P = nnc.p_pred.to_numpy(); typ = np.full(len(ep), "none", dtype=object)
for i, (a, b) in enumerate(zip(ep.t_on.to_numpy(), ep.t_off.to_numpy())):
    lo, hi = np.searchsorted(P, a - 15), np.searchsorted(P, b, side="right")
    if hi > lo:
        j = lo + np.argmin(np.abs(P[lo:hi] - a)); typ[i] = nnc.type.iloc[j]
ep["nnc"] = typ
glob_assoc = (ep.assoc_event >= 0).to_numpy()
NB = ["MK31", "KURK", "WUS"]; W = {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}
S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}; snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)}
for n, t in [("P3", 7.5), ("P2", 10.5)]:
    a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"; d = (~yes) & ok & (snr < t)
    a[d & no if n == "P2" else d] = "DISMISS"; act[n] = a
num = np.zeros(len(ep)); den = np.zeros(len(ep))
for k in NB:
    q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
cg = np.full(len(ep), "ESCALATE", dtype=object); cg[dd & (D >= 0.6)] = "ALERT"; cg[dd & (D <= 0.16)] = "DISMISS"; act["CG"] = cg
eq = ep.nnc.to_numpy() == "earthquake"; ex = ep.nnc.to_numpy() == "mining explosion"; noev = (ep.nnc.to_numpy() == "none") & ~glob_assoc
res = {"window": "2025-01-01..2026-02-28", "nnc_events": int(len(nnc)), "nnc_by_type": nnc.type.value_counts().to_dict(),
       "episodes": int(len(ep)), "episodes_nnc_earthquake": int(eq.sum()), "episodes_nnc_explosion": int(ex.sum()),
       "episodes_global_catalogue": int(glob_assoc.sum()), "episodes_any_event": int((eq | ex | glob_assoc).sum()), "policies": {}}
for n, a in act.items():
    res["policies"][n] = {"nnc_eq_dismissed": int(((a == "DISMISS") & eq).sum()), "nnc_eq_dismissed_share_pct": round(100 * float(((a == "DISMISS") & eq).sum()) / max(eq.sum(), 1), 2),
                          "nnc_expl_dismissed": int(((a == "DISMISS") & ex).sum()), "nnc_expl_alert": int(((a == "ALERT") & ex).sum()),
                          "alerts_no_event_any_catalogue": int(((a == "ALERT") & noev).sum()), "alerts_nnc_earthquake": int(((a == "ALERT") & eq).sum())}
days = ep.day.to_numpy(); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & eq) for d in ud}
rng = np.random.default_rng(7); vals = []
for _ in range(2000):
    ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
    if len(ids): vals.append(((cg[ids] == "DISMISS").mean() - (act["P3"][ids] == "DISMISS").mean()) * 100)
res["CG_minus_P3_dismissed_share_nnc_eq_pp"] = {"observed": round(float(((cg[eq] == "DISMISS").mean() - (act["P3"][eq] == "DISMISS").mean()) * 100), 2),
                                               "ci95": [round(float(np.percentile(vals, 2.5)), 2), round(float(np.percentile(vals, 97.5)), 2)]}
ep[["t_on_utc", "nnc"]].assign(global_assoc=glob_assoc, **{f"action_{k}": v for k, v in act.items()}).to_csv(os.path.join(OUT, "episodes_nnc.csv"), index=False)
json.dump(res, open(os.path.join(OUT, "nnc_eval.json"), "w"), indent=1, default=int)
print(json.dumps(res, indent=1, default=int))
