"""POST HOC (15.11.2026, Paper 1 v5 Appendix B): 95% intervals for the chance-corrected CG - P3 differences of the
registered non-inferiority contrasts E3 (extended IU.MAKZ), K3 (extended II.KURK), N3 (KZ network) and R3 (AK network),
which cold_panel_posthoc.py reports only as approximate point values. Not pre-specified; no frozen parameter changes.

Correction (the method of analysis/ak_chance_by_policy.py, applied to catalogue association):
  catalogue predicted P arrivals are shifted by random offsets (100 offsets, uniform 1..7 days, random sign, seed 7 --
  the offsets of cold_panel_posthoc.py block 1) and re-associated with the pipeline rule; for policy k
  corrected share_k = (D_k&assoc - mean_s D_k&assoc_s) / (n_assoc - mean_s n_assoc_s),
  corrected difference = corrected share_CG - corrected share_P3 (percentage points).
Interval: day bootstrap over days with episodes (2000 resamples, seed 7, as every test in the paper), the correction
recomputed inside each resample from per-day counts. Criterion: upper bound <= 3 points (the registered margin).
Output: results/paper1/chance_corrected_ci.json
"""
import os, json
import numpy as np

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, "analysis", "cold_panel_posthoc.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(root, "analysis", "cold_panel_posthoc.py"), "__name__": "cp_helpers"}
# helper definitions and data loading only (everything before block 1)
exec(compile(src[:src.index("DATA = {n: load_any(n)")], "cold_panel_helpers", "exec"), ns)
load_any, frozen_actions, assoc_vec = ns["load_any"], ns["frozen_actions"], ns["assoc_vec"]
import pandas as pd

SETS = {"E3": "extended IU.MAKZ", "K3": "extended II.KURK", "N3": "KZ network", "R3": "AK network"}
NB, SEED, MARGIN = 2000, 7, 3.0
rng_master = np.random.default_rng(7)
offs = rng_master.uniform(1, 7, 100) * 86400 * rng_master.choice([-1, 1], 100)   # identical to cold_panel block 1


def pct(v, q):
    return round(float(np.percentile(v, q)), 2)


out = {"status": "post hoc (15.11.2026), not pre-specified; intervals for the approximate chance-corrected differences of Appendix B",
       "method": __doc__.split("Correction")[1].strip(), "contrasts": {}}
for code, name in SETS.items():
    ep, av, dist, cat, ref = load_any(name)
    P = frozen_actions(ep, dist, ref)
    assoc = (ep.assoc_event >= 0).to_numpy()
    days = ep.t_on_utc.str[:10].to_numpy()
    t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy()
    pp = cat.p_pred.to_numpy(dtype=float)
    t0 = pd.Timestamp(av.day.min()).timestamp(); span = pd.Timestamp(av.day.max()).timestamp() + 86400 - t0
    dCG, dP3 = (P["CG"] == "D"), (P["P3"] == "D")
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    cnt = lambda m: np.bincount(inv, weights=m.astype(float), minlength=nd)
    real = np.vstack([cnt(assoc), cnt(dCG & assoc), cnt(dP3 & assoc)])          # per-day counts, shape (3, days)
    sh = np.zeros((3, nd))
    for o in offs:
        s = assoc_vec(t0 + np.mod(pp + o - t0, span), t_on, t_off)
        sh += np.vstack([cnt(s), cnt(dCG & s), cnt(dP3 & s)])
    sh /= len(offs)                                                            # expected chance counts per day

    def corrected(idx):
        r = real[:, idx].sum(1); c = sh[:, idx].sum(1); den = r[0] - c[0]
        return ((r[1] - c[1]) - (r[2] - c[2])) / den * 100, (r[1] - r[2]) / r[0] * 100

    allidx = np.arange(nd); obs_c, obs_raw = corrected(allidx)
    rng = np.random.default_rng(SEED); bc = []
    for _ in range(NB):
        bc.append(corrected(rng.integers(0, nd, nd))[0])
    bc = np.array(bc)
    out["contrasts"][code] = {"set": name, "days_with_episodes": int(nd), "associated": int(assoc.sum()),
                              "expected_chance_associated": round(float(sh[0].sum()), 1),
                              "raw_CG_minus_P3_pp": round(float(obs_raw), 2),
                              "chance_corrected_CG_minus_P3_pp": round(float(obs_c), 2),
                              "ci95_pp": [pct(bc, 2.5), pct(bc, 97.5)],
                              "upper_bound_within_3pt_margin": bool(np.percentile(bc, 97.5) <= MARGIN)}
    print(code, out["contrasts"][code], flush=True)
json.dump(out, open(os.path.join(root, "results", "paper1", "chance_corrected_ci.json"), "w"), indent=1)
