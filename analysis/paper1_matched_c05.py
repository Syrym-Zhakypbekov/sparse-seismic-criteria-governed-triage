"""Addendum 2 of PLAN_PAPER1_HARMONISED_2026-11-09.md: P3-2t with its alert threshold matched to the development escalation
count of CG c = 0.5; contrasts of the discounted rules against it; outage-day contrasts against P3-2t (8.0/10.0 dB).
Reuses the functions of analysis/paper1_harmonised.py (definitions only). Output: results/paper1/matched_c05.json."""
import os, json, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(HERE, "paper1_harmonised.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(HERE, "paper1_harmonised.py")}
exec(src[:src.index("# ---------- development")], ns)
load, actions, dayboot, R = ns["load"], ns["actions"], ns["dayboot"], ns["R"]
NB, SEED = 2000, 7
dev, dav, ddist = load([os.path.join(R, "stage1_v3")], {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1})
a0, assoc0, *_ = actions(dev, dav, ddist, "MAKZ", None)
yes0 = np.zeros(len(dev), bool)
for k in ("MK31", "KURK", "WUS"): yes0 |= dev[f"n_{k}"].astype(str).to_numpy() == "YES"
snr0 = dev.snr_db.fillna(0).to_numpy(); ok0 = dev.snr_db.notna().to_numpy()
tD = 8.0; target = int((a0["CG c=0.5"] == "E").sum()); cand = []
for tA in np.round(np.arange(tD, 30.01, 0.5), 2):
    e = int(((yes0 & ok0 & (snr0 < tA)) | ((~yes0) & ok0 & (snr0 >= tD)) | ~ok0).sum())
    cand.append((abs(e - target), float(tA), e))
cand.sort(key=lambda r: (r[0], r[1])); tA = cand[0][1]
res = {"plan": "PLAN_PAPER1_HARMONISED_2026-11-09.md addendum 2", "P3_2t_c05": {"tD": tD, "tA": tA, "dev_escalations": cand[0][2], "dev_CG_c05_escalations": target}, "sets": {}}
print(res["P3_2t_c05"])
E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
        "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
        "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}
for name, (dirs, tref) in SETS.items():
    ep, av, dist = load(dirs); ndays = int(av.day.nunique())
    act, assoc, days, outage, *_ = actions(ep, av, dist, tref, (tD, tA))
    act2, *_ = actions(ep, av, dist, tref, (8.0, 10.0))
    r = {"P3-2t-c05": {"dismissed_assoc": int(((act["P3-2t"] == "D") & assoc).sum()), "unassoc_alerts": int(((act["P3-2t"] == "A") & ~assoc).sum()),
                       "esc_per_day": round(float((act["P3-2t"] == "E").sum()) / ndays, 2)},
         "contrasts": {f"{x} - P3-2t-c05": dayboot(days, assoc, act[x], act["P3-2t"], ndays=ndays) for x in ("CG c=0.5", "CG-D")}}
    if outage.any() and (assoc & outage).any():
        sel = assoc & outage; ud = np.array(sorted(set(days[outage]))); idx = {d: np.flatnonzero((days == d) & sel) for d in ud}
        for x in ("CG", "CG c=0.5"):
            rng = np.random.default_rng(SEED); v = []
            for _ in range(NB):
                ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
                if len(ids): v.append(((act2[x][ids] == "D").mean() - (act2["P3-2t"][ids] == "D").mean()) * 100)
            r[f"outage {x} - P3-2t"] = {"diff_pp": round(float(((act2[x][sel] == "D").mean() - (act2["P3-2t"][sel] == "D").mean()) * 100), 2),
                                         "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
                                         "counts": [int(((act2[x] == "D") & sel).sum()), int(((act2["P3-2t"] == "D") & sel).sum()), int(sel.sum())]}
    res["sets"][name] = r; print(name, json.dumps(r)[:600])
json.dump(res, open(os.path.join(R, "paper1", "matched_c05.json"), "w", encoding="utf-8"), indent=1)
