"""POST HOC mechanism check (07.11.2026, after E3/K3 were known): in the January 2025 - June 2026 periods, which
neighbour records lie behind the associated alarms that CG dismissed and P3 did not?
For each reference: (1) per neighbour, distance and the share of associated alarms on which it recorded NO, by
reference-SNR bin; (2) for the excess dismissals (CG DISMISS, P3 not DISMISS), the count with a NO from each neighbour
and the count whose only NO votes come from neighbours farther than 400 km.
Descriptive; it cannot separate distance from station noise, detector threshold or window length.
Output: results/posthoc/mechanism_extended.json
"""
import os, json, importlib.util
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ph", next(f for f in [os.path.join(root, "analysis", "posthoc_extended.py"), os.path.join(root, "code", "26_posthoc_extended.py")] if os.path.exists(f)))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)
BINS, LAB = ph.BINS, ph.LAB

out = {"status": "post hoc, descriptive"}
for ref in ["MAKZ", "KURK"]:
    ep, cal, dist = ph.load(ref)
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist[k])
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"
    p3 = np.full(len(ep), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"
    num = np.zeros(len(ep)); den = np.zeros(len(ep))
    for k in NB:
        q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
    num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
    dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    cg = np.full(len(ep), "ESCALATE", dtype=object); cg[dd & (D >= 0.6)] = "ALERT"; cg[dd & (D <= 0.16)] = "DISMISS"
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    per = {}
    for k in NB:
        valid = assoc & np.isin(S[k], ["YES", "NO"])
        row = {"distance_km": dist[k], "assoc_valid": int(valid.sum()),
               "no_share": round(float((S[k][valid] == "NO").mean()), 3) if valid.any() else None, "by_snr_bin": {}}
        for bb in LAB:
            m = valid & (b == bb)
            row["by_snr_bin"][bb] = {"n": int(m.sum()), "no_share": round(float((S[k][m] == "NO").mean()), 3) if m.any() else None}
        per[k] = row
    ex = assoc & (cg == "DISMISS") & (p3 != "DISMISS")
    far = [k for k in NB if dist[k] > 400]; near = [k for k in NB if dist[k] <= 400]
    no_far = np.zeros(len(ep), bool); no_near = np.zeros(len(ep), bool)
    for k in far: no_far |= S[k] == "NO"
    for k in near: no_near |= S[k] == "NO"
    out[ref] = {"neighbours": per,
                "excess_dismissals": int(ex.sum()),
                "excess_with_NO_from": {k: int((ex & (S[k] == "NO")).sum()) for k in NB},
                "excess_only_far_NO_gt_400km": int((ex & no_far & ~no_near).sum()),
                "excess_with_near_NO_le_400km": int((ex & no_near).sum()),
                "excess_ref_snr_bins": {bb: int((ex & (b == bb)).sum()) for bb in LAB}}

os.makedirs(os.path.join(root, "results", "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(root, "results", "posthoc", "mechanism_extended.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
