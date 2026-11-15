"""P10X-06 (registry v4-P10, 9063f88): the evidence-sufficiency condition delta as a constraint, measured cost.
06a (exact): reviewed-associated episodes whose DISMISS status changes between delta = 0.45 and delta = 0 (0 = escalate only when
no evidence at all, as analysis/sufficiency_stress.py), for CG, c = 0.5, CG-D on the 33 reviewed networks, archive (no masking).
06b (descriptive): cost on the archive (cluster bootstrap) and under independent masking p = 0.5 (50 seeds, 7..56).
Output: results/p10x/delta_cost.json, results/registry/P10X-06.json."""
import os, sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

spec = importlib.util.spec_from_file_location("v2d", os.path.join(P10, "analysis", "v2_networks.py"))
v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
POLS = ["CG", "CG_c05", "CG-D"]; DELTAS = {"on": 0.45, "off": 0.0}


def scores(S, snr, ok, pol, bins):
    n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for r, s in enumerate(S[:3]):
        q = np.isin(s, ["YES", "NO"]).astype(float)
        if pol == "CG_c05": q = np.where(s == "NO", 0.5, q)
        if pol == "CG-D":
            tab = v2.TAB.get("MAKZ", {}).get(v2.DEV_ROLE_BY_RANK[r], {})
            p = np.array([tab.get(x, {"p": 0.5})["p"] if x in v2.LAB else 0.5 for x in bins]); q = np.where(s == "NO", p, q)
        num += W_RANK[r] * (s == "YES") * q; den += W_RANK[r] * q
    num += W_SNR * np.clip(snr / 30, 0, 1) * ok; den += W_SNR * ok
    return num, den


def act(num, den, delta):
    dd = den >= delta if delta > 0 else den > 0
    D = np.where(dd, num / np.where(den > 0, den, 1), np.nan); return act_from_D(D, THETA_D, THETA_A)


rows, nets, pkl_sha = load_reviewed()
BASE = {}
for k in nets:
    r = rows[k]; snr = np.asarray(r["snr"], float); ok = np.asarray(r["ok"], bool)
    bins = pd.cut(pd.Series(np.where(ok, snr, np.nan)), v2.BINS, labels=v2.LAB).astype(str).to_numpy()
    BASE[k] = (r["S"][:3], snr, ok, bins, np.asarray(r["assoc"], bool))
    for pol in POLS:
        nm, dn = scores(r["S"], snr, ok, pol, bins)
        assert (act(nm, dn, 0.45) == to_int(r["act"][pol])).all(), (k, pol)

# ---- archive
A = {}; changed = {}
for pol in POLS:
    changed[pol] = {"assoc_dismiss_status_changed": 0, "assoc_dismissed_on": 0, "assoc_dismissed_off": 0, "decisions_changed": 0}
    for d, dv in DELTAS.items():
        A[f"{pol}|{d}"] = {}
    for k in nets:
        S, snr, ok, bins, assoc = BASE[k]; nm, dn = scores(S, snr, ok, pol, bins)
        on, off = act(nm, dn, 0.45), act(nm, dn, 0.0); A[f"{pol}|on"][k] = on; A[f"{pol}|off"][k] = off
        c = changed[pol]; c["assoc_dismiss_status_changed"] += int((((on == -1) != (off == -1)) & assoc).sum())
        c["assoc_dismissed_on"] += int(((on == -1) & assoc).sum()); c["assoc_dismissed_off"] += int(((off == -1) & assoc).sum())
        c["decisions_changed"] += int((on != off).sum())
T = DayTable(rows, nets, A); full = T.full(); B = T.boot()
arch = {}
for pol in POLS:
    x, y = f"{pol}|on", f"{pol}|off"
    st = lambda t: {"added_esc_per_nd": (t[x + "|E"] - t[y + "|E"]) / t["days"], "removed_alerts_per_nd": (t[y + "|A"] - t[x + "|A"]) / t["days"],
                    "removed_dismissals_per_nd": (t[y + "|D"] - t[x + "|D"]) / t["days"],
                    "removed_unassoc_alerts_per_nd": (t[y + "|Au"] - t[x + "|Au"]) / t["days"]}
    o = st(full); bv = [st(b) for b in B]
    arch[pol] = {kk: {"est": round(float(o[kk]), 4), "ci": [round(float(np.percentile([b[kk] for b in bv], 2.5)), 4), round(float(np.percentile([b[kk] for b in bv], 97.5)), 4)]} for kk in o}
    arch[pol]["totals"] = {"added_escalations": int(full[x + "|E"] - full[y + "|E"]), "removed_alerts": int(full[y + "|A"] - full[x + "|A"]),
                           "removed_dismissals": int(full[y + "|D"] - full[x + "|D"]), "network_days_with_episodes": int(full["days"])}
print("06a", changed); print("archive", json.dumps(arch)[:800])

# ---- masking p = 0.5, independent per site-episode, 50 seeds
SEEDS = list(range(7, 57)); per = {pol: {k: [] for k in nets} for pol in POLS}
for sd in SEEDS:
    rng = np.random.default_rng([sd, 0])
    for k in nets:
        S, snr, ok, bins, assoc = BASE[k]; U = rng.random((3, len(snr)))
        Sm = [np.where(U[r] < 0.5, "MISSING", S[r]).astype(object) for r in range(3)]
        for pol in POLS:
            nm, dn = scores(Sm, snr, ok, pol, bins); on, off = act(nm, dn, 0.45), act(nm, dn, 0.0)
            per[pol][k].append([((off == -1) & assoc).sum() - ((on == -1) & assoc).sum(), (on == 0).sum() - (off == 0).sum(),
                                (off == 1).sum() - (on == 1).sum(), ((off == 1) & ~assoc).sum() - ((on == 1) & ~assoc).sum(), (on == 0).sum()])
mask = {}
rng = np.random.default_rng(SEED); draws = [rng.choice(nets, len(nets)) for _ in range(NB)]
for pol in POLS:
    M = {k: np.mean(np.array(per[pol][k], float), axis=0) for k in nets}
    tot = lambda ks: np.sum([M[k] for k in ks], axis=0)
    o = tot(nets); bv = np.array([tot(ks) for ks in draws])
    ratio_b = np.where(bv[:, 0] > 0, bv[:, 1] / np.where(bv[:, 0] > 0, bv[:, 0], 1), np.nan); okr = np.isfinite(ratio_b)
    seedtot = np.array([np.sum([per[pol][k][i] for k in nets], axis=0) for i in range(len(SEEDS))], float)
    mask[pol] = {"avoided_assoc_dismissals_mean": round(float(o[0]), 2),
                 "avoided_ci95_network_boot": [round(float(np.percentile(bv[:, 0], 2.5)), 2), round(float(np.percentile(bv[:, 0], 97.5)), 2)],
                 "added_escalations_mean": round(float(o[1]), 1), "added_esc_pct": round(float(100 * o[1] / (o[4] - o[1])), 2),
                 "removed_alerts_mean": round(float(o[2]), 1), "removed_unassoc_alerts_mean": round(float(o[3]), 1),
                 "esc_per_avoided_dismissal": round(float(o[1] / o[0]), 1) if o[0] > 0 else None,
                 "esc_per_avoided_ci95": [round(float(np.percentile(ratio_b[okr], 2.5)), 1), round(float(np.percentile(ratio_b[okr], 97.5)), 1)] if okr.any() else None,
                 "ratio_undefined_resamples": int((~okr).sum()),
                 "avoided_seed_range": [float(seedtot[:, 0].min()), float(seedtot[:, 0].max())]}
print("mask", json.dumps(mask))
res = {"pickle_sha256": pkl_sha, "delta_off_definition": "delta = 0: escalate only when the evidence mass is 0 (analysis/sufficiency_stress.py)",
       "06a_archive_exact": changed, "06b_archive_cost": arch, "06b_masked_p05_independent": mask,
       "masking": "independent per site-episode, p = 0.5, seeds 7..56 (rng [seed, 0]); per-network seed means, network bootstrap 2000 seed 7"}
dump(os.path.join(OUT, "delta_cost.json"), res)
zero = all(changed[p]["assoc_dismiss_status_changed"] == 0 for p in POLS)
c = mask["CG_c05"]
dump(os.path.join(REG, "P10X-06.json"), {
    "family": "F-P10X (06a) + descriptive (06b)", "id": "P10X-06", "chain": "C",
    "data": "33 reviewed-bulletin networks, frozen thresholds (P10 a97d376)",
    "metric": "06a: count of reviewed-associated episodes whose DISMISS status changes, delta 0.45 vs 0 (CG, c=0.5, CG-D); 06b: escalations per avoided dismissal under p=0.5 masking (c=0.5)",
    "est": sum(changed[p]["assoc_dismiss_status_changed"] for p in POLS), "ci": [None, None], "p": 0.0 if zero else 1.0,
    "verdict_unadjusted": "HELD" if zero else "not held", "verdict": None,
    "06a": changed, "06b_archive": arch, "06b_masked": mask,
    "06b_headline_c05": {"esc_per_avoided": c["esc_per_avoided_dismissal"], "ci": c["esc_per_avoided_ci95"], "avoided": c["avoided_assoc_dismissals_mean"], "avoided_ci": c["avoided_ci95_network_boot"]},
    "note": "06a is an exact count (no sampling); for c=0.5 and CG-D the zero on the real thin subset was already published (sufficiency/cost.json). 06b descriptive."})
