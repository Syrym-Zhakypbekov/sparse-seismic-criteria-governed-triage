"""P10X-04 (registry v4-P10, 9063f88): chance confirmation per neighbour (G.WUS) and G.WUS-removed sensitivity.
The registered time-shift method is blocked (no neighbour trigger times on disk); the registered Poisson substitute and the
empirical companion are computed. Output: results/p10x/chanceyes.json, results/registry/P10X-04.json."""
import os, sys, glob, re, importlib.util
import numpy as np, pandas as pd
from scipy.stats import chi2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from onethreshold import load_dirs, feats, snr_act, cg_act   # noqa (module-level code of onethreshold runs; ~1 min)

R = os.path.join(P10, "results")
spec = importlib.util.spec_from_file_location("v2c", os.path.join(P10, "analysis", "v2_networks.py"))
v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
V_MIN, PICK_TOL = 5.5, 5.0
DIST = {"MAKZ": {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}, "KURK": {"MAKZ": 499.6, "MK31": 512.7, "WUS": 1058.6}}


def pois_ci(k):
    lo = 0.0 if k == 0 else chi2.ppf(0.025, 2 * k) / 2; hi = chi2.ppf(0.975, 2 * (k + 1)) / 2; return lo, hi


def wilson(x, n):
    if n == 0: return [None, None]
    z = 1.959964; p = x / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 5), round(c + h, 5)]


periods = {"dev 2026 (stage1_v3)": [os.path.join(R, "stage1_v3")]}
for q in sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))): periods["2024 " + os.path.basename(q)[11:]] = [q]
poisson = {}
for pname, dirs in periods.items():
    d = dirs[0]; summ = json.load(open(os.path.join(d, "summary.json"))); av = pd.read_csv(os.path.join(d, "availability.csv"))
    cnt = summ["episodes"]; poisson[pname] = {}
    for ref, nb in DIST.items():
        for st, dkm in nb.items():
            vs = float(av[f"{st}_valid_share"].sum() * 86400); k = int(cnt[st]); w = dkm / V_MIN + PICK_TOL
            lam = k / vs; lo, hi = pois_ci(k)
            f = lambda l: 1 - np.exp(-l * 2 * w)
            poisson[pname][f"{ref}<-{st}"] = {"triggers": k, "valid_days": round(vs / 86400, 2), "window_s_each_side": round(w, 1),
                                              "triggers_per_valid_day": round(lam * 86400, 2),
                                              "chance_yes": round(f(lam), 5), "ci95": [round(f(lo / vs), 5), round(f(hi / vs), 5)]}
print(json.dumps(poisson["dev 2026 (stage1_v3)"], indent=0)[:800])

# empirical companion: YES share among unassociated reference episodes with the neighbour valid
emp = {}
E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"dev 2026 IU.MAKZ": ([os.path.join(R, "stage1_v3")], "MAKZ"),
        "extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK")}
LOADED = {}
for sname, (dirs, ref) in SETS.items():
    ep, dist = load_dirs(dirs)
    if not dist: dist = DIST[ref]
    LOADED[sname] = (ep, dist, ref); un = (ep.assoc_event < 0).to_numpy(); emp[sname] = {}
    for c in [c for c in ep.columns if c.startswith("n_")]:
        s = ep[c].astype(str).to_numpy(); v = un & (s != "MISSING"); y = int((v & (s == "YES")).sum()); n = int(v.sum())
        emp[sname][c[2:]] = {"unassoc_valid": n, "yes": y, "yes_share": round(y / n, 5) if n else None, "ci95": wilson(y, n)}
print(json.dumps(emp, indent=0)[:1500])


def dayboot_rates(days, a, b, n=NB, seed=SEED):
    ud, inv = np.unique(days, return_inverse=True)
    m = {k: np.bincount(inv, weights=w, minlength=len(ud)) for k, w in
         {"Ea": a == "E", "Eb": b == "E", "Aa": a == "A", "Ab": b == "A"}.items()}
    rng = np.random.default_rng(seed); v = []
    st = lambda s: ((m["Ea"][s].sum() - m["Eb"][s].sum()) / len(s), (m["Aa"][s].sum() - m["Ab"][s].sum()) / len(s))
    for _ in range(n): v.append(st(rng.integers(0, len(ud), len(ud))))
    v = np.array(v); o = st(np.arange(len(ud)))
    q = lambda i: [round(float(np.percentile(v[:, i], 2.5)), 3), round(float(np.percentile(v[:, i], 97.5)), 3)]
    return {"esc_per_day_diff": round(float(o[0]), 3), "esc_ci95": q(0), "alerts_per_day_diff": round(float(o[1]), 3), "alerts_ci95": q(1)}


sens = {}
for sname in ("extended IU.MAKZ", "extended II.KURK", "2024 IU.MAKZ", "2024 II.KURK"):
    ep, dist, ref = LOADED[sname]
    for mode in ("frozen", "WUS_missing"):
        e2 = ep.copy()
        if mode == "WUS_missing": e2["n_WUS"] = "MISSING"
        f = feats(e2, dist); a = cg_act(f, THETA_D); b = snr_act("P3", 7.5, f)
        r = v2.day_boot(f["days"], f["assoc"], a, b)
        r["unassoc_alerts"] = {"CG": int(((a == "A") & ~f["assoc"]).sum()), "P3": int(((b == "A") & ~f["assoc"]).sum())}
        r["escalations"] = {"CG": int((a == "E").sum()), "P3": int((b == "E").sum())}
        r["dismissed_assoc"] = {"CG": int(((a == "D") & f["assoc"]).sum()), "P3": int(((b == "D") & f["assoc"]).sum())}
        r.update(dayboot_rates(f["days"], a, b))
        sens.setdefault(sname, {})[mode] = r
    print(sname, sens[sname])

res = {"registered_method_time_shift": "BLOCKED: neighbour trigger times are not stored (episodes.csv keeps only n_<station> state); "
                                       "regenerating them requires the raw waveforms (not downloaded by rule)",
       "poisson_substitute": poisson, "empirical_yes_share_unassociated": emp, "wus_removed_sensitivity": sens}
dump(os.path.join(OUT, "chanceyes.json"), res)
wq = [v["MAKZ<-WUS"]["chance_yes"] for k, v in poisson.items() if k.startswith("2024")]
oth = [v[x]["chance_yes"] for k, v in poisson.items() if k.startswith("2024") for x in ("MAKZ<-MK31", "MAKZ<-KURK")]
dv = poisson["dev 2026 (stage1_v3)"]["MAKZ<-WUS"]
dump(os.path.join(REG, "P10X-04.json"), {
    "family": "descriptive (not in Holm)", "id": "P10X-04", "chain": "B",
    "data": "IU.MAKZ/II.KURK ledgers: development 2026, 2024 quarters, extended 2025-26 (P10 a97d376); trigger counts from summary.json",
    "metric": "chance-YES of G.WUS seen from IU.MAKZ, Poisson substitute (registered), 2024 Q1; plus G.WUS-removed CG-P3 sensitivity",
    "est": poisson["2024 2024-01-01"]["MAKZ<-WUS"]["chance_yes"], "ci": poisson["2024 2024-01-01"]["MAKZ<-WUS"]["ci95"], "p": None,
    "verdict": "inconclusive",
    "summary": {"WUS_from_MAKZ_2024_quarters": wq, "MK31_KURK_from_MAKZ_2024_quarters": oth, "WUS_from_MAKZ_dev2026": dv,
                "WUS_from_KURK_2024_Q1": poisson["2024 2024-01-01"]["KURK<-WUS"],
                "empirical_WUS_yes_share_unassoc": {k: v.get("WUS") for k, v in emp.items()},
                "E3_K3_wus_missing": {k: {m: [v[m]["diff_pp"], v[m]["ci95_pp"], v[m]["esc_per_day_diff"], v[m]["esc_ci95"], v[m]["alerts_per_day_diff"], v[m]["alerts_ci95"]] for m in v} for k, v in sens.items()}},
    "note": "Descriptive row. The registered time-shifted trigger method is BLOCKED (see plan/BLOCKERS_P10X.md); the Poisson value assumes "
            "triggers uniform in valid time (clustering would change it) and is a deviation from the requested method. "
            "Lists: [diff_pp, ci, esc/day diff, ci, alerts/day diff, ci] for CG - P3."})
