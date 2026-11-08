"""Post hoc (08.11.2026, internal review v30): Alaska analyst-label test (Section 4.11) with the chance-matching control
applied PER POLICY.

The pre-specified control (analysis/ground_truth_v2.py) shifts the label arrival times by +-1, +-2, +-3 days and reports how
many episodes become CONFIRMED by chance. Chance matches fall on the whole episode population, where CG dismisses far more
episodes than P3, so the control must be applied to each policy's dismissals. Estimator, for policy k:
  corrected dismissed share_k = (D_k|CONFIRMED - mean_s D_k|CONFIRMED_s) / (n_CONFIRMED - mean_s n_CONFIRMED_s)
  corrected difference = corrected share_k - corrected share_P3 (percentage points)
95% interval: day bootstrap (2000 resamples, seed 7, as every earlier test), the six shifts recomputed inside each resample.
Policies: CG (c = 1), CG-D, CG with c = 0.5 (constant), against P3 7.5 dB. Frozen actions from ground_truth_v2.episodes_and_actions.
Writes results/posthoc/ak_chance_by_policy.json only.
"""
import os, sys, json, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
sys.path.insert(0, here)
import ground_truth_v2 as gt


def main():
  ep, act = gt.episodes_and_actions()
  # constant c = 0.5 variant of CG (same weights and thresholds as the frozen CG)
  NB = [c[2:] for c in ep.columns if c.startswith("n_")]
  import re, glob
  dist = {}
  for d in sorted(glob.glob(os.path.join(gt.A, "outAK_20*"))):
      dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read(), re.M)})
  NB = sorted(NB, key=lambda k: dist.get(k, 1e9)); W = dict(zip(NB, [0.25, 0.20, 0.15]))
  snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
  num = np.zeros(len(ep)); den = np.zeros(len(ep))
  for k in NB:
      S = ep[f"n_{k}"].astype(str).to_numpy(); q = np.isin(S, ["YES", "NO"]).astype(float); q = np.where(S == "NO", 0.5, q)
      num += W[k] * (S == "YES") * q; den += W[k] * q
  num += 0.40 * np.clip(snr / 30, 0, 1) * ok; den += 0.40 * ok
  dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
  a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"; act["CG_c05"] = a

  lab = gt.labels()
  cls, _ = gt.match(ep, lab)
  C0 = cls == "CONFIRMED"
  CS = [gt.match(ep, lab, shift=s * 86400.0)[0] == "CONFIRMED" for s in gt.SHIFTS_D]
  days = ep.day.to_numpy()
  POL = ["CG", "CG-D", "CG_c05"]
  Dm = {k: act[k] == "DISMISS" for k in POL + ["P3"]}


  def est(ids):
      c0 = C0[ids]; n = c0.sum(); ns = np.mean([c[ids].sum() for c in CS])
      out = {}
      for k in POL + ["P3"]:
          dk = Dm[k][ids]; d0 = (dk & c0).sum(); dsh = np.mean([(dk & c[ids]).sum() for c in CS])
          out[k] = ((d0 - dsh) / max(n - ns, 1) * 100, d0 / max(n, 1) * 100, d0, dsh)
      return out, n, ns


  allids = np.arange(len(ep)); obs, n, ns = est(allids)
  rng = np.random.default_rng(7); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero(days == d) for d in ud}
  bs = {k: {"raw": [], "corr": []} for k in POL}
  for _ in range(2000):
      ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))]); e, _, _ = est(ids)
      for k in POL:
          bs[k]["raw"].append(e[k][1] - e["P3"][1]); bs[k]["corr"].append(e[k][0] - e["P3"][0])
  pc = lambda v: [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
  res = {"status": "post hoc (internal review v30); pre-specified G1/G2 unchanged",
         "confirmed_episodes": int(n), "chance_confirmed_mean": round(float(ns), 2), "shifts_days": gt.SHIFTS_D,
         "P3": {"dismissed_confirmed": int(obs["P3"][2]), "chance_dismissed_mean": round(float(obs["P3"][3]), 2)},
         "policies": {}}
  for k in POL:
      raw = obs[k][1] - obs["P3"][1]; cor = obs[k][0] - obs["P3"][0]
      res["policies"][k] = {"dismissed_confirmed": int(obs[k][2]), "chance_dismissed_mean": round(float(obs[k][3]), 2),
                            "raw_minus_P3_pp": round(float(raw), 2), "raw_ci95": pc(bs[k]["raw"]),
                            "chance_corrected_minus_P3_pp": round(float(cor), 2), "chance_corrected_ci95": pc(bs[k]["corr"]),
                            "corrected_criterion_met": bool(np.percentile(bs[k]["corr"], 97.5) <= 3.0)}
  os.makedirs(os.path.join(root, "results", "posthoc"), exist_ok=True)
  json.dump(res, open(os.path.join(root, "results", "posthoc", "ak_chance_by_policy.json"), "w"), indent=1)
  print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
