"""Evidence-sufficiency stress test. Plan: PLAN_SUFFICIENCY_STRESS_2026-11-08.md (pushed e30842d before computing).

A. Neighbour-site states are masked to MISSING at rate p (independent per episode x site, or correlated as whole-day
   site outages); every rule is re-evaluated on the masked states. B. The real thin subset (>= 2 of 3 sites MISSING).
Input: results/posthoc/_collect_reviewed.pkl (33 reviewed-label networks). Nothing in pipeline/ is used or changed.
Outputs: results/sufficiency/stress.json, results/sufficiency/thin_subset.json.
Usage: python analysis/sufficiency_stress.py [--workers 8] [--seeds 50]
"""
import os, sys, json, time, pickle, argparse
import numpy as np, pandas as pd
from multiprocessing import Pool

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "results", "sufficiency"); os.makedirs(OUT, exist_ok=True)
PKL = os.path.join(root, "results", "posthoc", "_collect_reviewed.pkl")
DEV_TAB = os.path.join(root, "results", "prereg", "detectability_tables_dev.json")
if not os.path.exists(DEV_TAB): DEV_TAB = os.path.join(root, "results", "detectability_tables_dev.json")
TAB = json.load(open(DEV_TAB))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
W = [0.25, 0.20, 0.15]; W_SNR = 0.40; TA, TD = 0.60, 0.16
DEV_ROLE_BY_RANK = ["MK31", "KURK", "WUS"]
PS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
DELTAS = [0.0, 0.45, 0.55]
CGS = ["CG", "CG_c05", "CG-D"]
RULES = ["P1", "P3", "P3_2t"] + [f"{c}|{d}" for c in CGS for d in DELTAS]
NREP, SEED = 500, 7

NETS = None; BOOT = None


def load():
    rows = pickle.load(open(PKL, "rb"))
    nets = {}
    for k in sorted(rows):
        v = rows[k]
        if not v.get("included"): continue
        S = np.vstack([np.asarray(s, object) for s in v["S"][:3]])
        snr = np.asarray(v["snr"], float); ok = np.asarray(v["ok"], bool)
        b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
        pv = []
        for r in range(3):
            tab = TAB.get("MAKZ", {}).get(DEV_ROLE_BY_RANK[r], {})
            pv.append(np.array([tab.get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]))
        ud, inv = np.unique(np.asarray(v["days"]), return_inverse=True)
        nets[k] = dict(S=S, snr=snr, ok=ok, pv=pv, assoc=np.asarray(v["assoc"], bool), act=v["act"], nd=len(ud), inv=inv)
    return nets


def actions(N, S):
    snr, ok = N["snr"], N["ok"]; n = len(snr)
    yes = (S == "YES"); no = (S == "NO"); valid = yes | no
    anyyes = yes.any(0)
    out = {"P1": np.where(anyyes, "A", "D").astype(object)}
    for name, td, ta in (("P3", 7.5, 7.5), ("P3_2t", 8.0, 13.5)):
        a = np.full(n, "E", dtype=object); a[anyyes & ok & (snr >= ta)] = "A"; a[(~anyyes) & ok & (snr < td)] = "D"; out[name] = a
    snrterm = np.clip(snr / 30, 0, 1) * ok
    for c in CGS:
        num = np.zeros(n); den = np.zeros(n)
        for r in range(3):
            q = valid[r].astype(float)
            if c == "CG-D": q = np.where(no[r], N["pv"][r], q)
            if c == "CG_c05": q = np.where(no[r], 0.5, q)
            num += W[r] * yes[r] * q; den += W[r] * q
        num = num + W_SNR * snrterm; den = den + W_SNR * ok
        for d in DELTAS:
            dd = den >= d if d > 0 else den > 0
            D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
            a = np.full(n, "E", dtype=object); a[dd & (D >= TA)] = "A"; a[dd & (D <= TD)] = "D"; out[f"{c}|{d}"] = a
    nsrc = ok.astype(int) + valid.sum(0)
    return out, nsrc


def boot_mats(nets, nrep, seed):
    """Per network: matrix (nrep x days) of total day multiplicity in each two-stage cluster draw."""
    names = sorted(nets); K = len(names); rng = np.random.default_rng(seed)
    M = {k: np.zeros((nrep, nets[k]["nd"])) for k in names}
    for r in range(nrep):
        for ki in rng.choice(K, K):
            k = names[ki]; nd = nets[k]["nd"]
            M[k][r] += np.bincount(rng.choice(nd, nd), minlength=nd)
    return M


def dayvec(N, mask):
    return np.bincount(N["inv"][mask], minlength=N["nd"]).astype(float)


def summarise(nets, A, nsrc, sub=None):
    """Point outcomes per rule. sub: optional {net: bool mask} restricting episodes."""
    res = {}
    for rule in RULES:
        t = dict(assoc_dismissed=0, assoc=0, unassoc_alerts=0, escalations=0, auto=0, auto_thin=0, dismissals=0)
        for k in nets:
            a = A[k][rule]; s = nets[k]["assoc"]; m = np.ones(len(a), bool) if sub is None else sub[k]
            t["assoc"] += int((s & m).sum()); t["assoc_dismissed"] += int(((a == "D") & s & m).sum())
            t["unassoc_alerts"] += int(((a == "A") & ~s & m).sum()); t["escalations"] += int(((a == "E") & m).sum())
            au = ((a == "A") | (a == "D")) & m; t["auto"] += int(au.sum()); t["auto_thin"] += int((au & (nsrc[k] < 2)).sum())
            t["dismissals"] += int(((a == "D") & m).sum())
        t["assoc_dismissed_pct"] = round(100 * t["assoc_dismissed"] / max(t["assoc"], 1), 3)
        t["auto_thin_pct"] = round(100 * t["auto_thin"] / max(t["auto"], 1), 3)
        res[rule] = t
    return res


def stat_boot(nets, M, terms, sub=None):
    """terms: list of (coef, {net: day-vector of reviewed-associated dismissals}); returns obs and nrep values (pp)."""
    num = 0; den = 0; onum = 0.0; oden = 0.0
    for k in nets:
        s = nets[k]["assoc"] if sub is None else nets[k]["assoc"] & sub[k]
        na = dayvec(nets[k], s); v = sum(c * d[k] for c, d in terms)
        num = num + M[k] @ v; den = den + M[k] @ na; onum += v.sum(); oden += na.sum()
    return 100 * onum / oden, 100 * num / np.where(den > 0, den, np.nan)


def comparisons():
    """name -> (rule A, rule B, kind) ; kind diff = A - B ; rise = (A_p - A_0) - (B_p - B_0)."""
    return {"S1_P1_minus_CGc05": ("P1", "CG_c05|0.45", "diff"), "S1_P1_minus_CG": ("P1", "CG|0.45", "diff"),
            "S1_P1_minus_CGD": ("P1", "CG-D|0.45", "diff"),
            "S2_CGc05_delta0_minus_045": ("CG_c05|0.0", "CG_c05|0.45", "diff"),
            "S2_CG_delta0_minus_045": ("CG|0.0", "CG|0.45", "diff"), "S2_CGD_delta0_minus_045": ("CG-D|0.0", "CG-D|0.45", "diff"),
            "S2b_CGc05_delta055_minus_045": ("CG_c05|0.55", "CG_c05|0.45", "diff"),
            "S3_rise_CGc05_minus_P3_2t": ("CG_c05|0.45", "P3_2t", "rise"), "S3_rise_CGc05_minus_P3": ("CG_c05|0.45", "P3", "rise"),
            "CGc05_minus_P3_2t": ("CG_c05|0.45", "P3_2t", "diff")}


def masked_states(N, u, p):
    S = N["S"].copy(); m = (u < p) & (S != "MISSING"); S[m] = "MISSING"; return S


def worker(job):
    mode, seed = job
    nets, M = NETS, BOOT
    rng = np.random.default_rng([seed, 0 if mode == "independent" else 1])
    U = {}
    for k in nets:
        N = nets[k]
        if mode == "independent": U[k] = rng.random(N["S"].shape)
        else: U[k] = rng.random((3, N["nd"]))[:, N["inv"]]
    base = {k: actions(nets[k], nets[k]["S"])[0] for k in nets}
    base_d = {rule: {k: dayvec(nets[k], (base[k][rule] == "D") & nets[k]["assoc"]) for k in nets} for rule in RULES}
    out = {}
    for p in PS:
        A = {}; nsrc = {}
        for k in nets:
            A[k], nsrc[k] = actions(nets[k], masked_states(nets[k], U[k], p))
        summ = summarise(nets, A, nsrc)
        d = {rule: {k: dayvec(nets[k], (A[k][rule] == "D") & nets[k]["assoc"]) for k in nets} for rule in RULES}
        cmp_ = {}
        for name, (a, b, kind) in comparisons().items():
            terms = [(1, d[a]), (-1, d[b])] if kind == "diff" else [(1, d[a]), (-1, base_d[a]), (-1, d[b]), (1, base_d[b])]
            obs, v = stat_boot(nets, M, terms)
            cmp_[name] = (float(obs), v.astype(np.float32))
        out[p] = (summ, cmp_)
    return mode, seed, out


def init(nets, M):
    global NETS, BOOT
    NETS, BOOT = nets, M


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args(); t0 = time.time()
    nets = load(); print("networks", len(nets), "episodes", sum(len(n["snr"]) for n in nets.values()), flush=True)
    # reproduction of the frozen actions at p = 0, delta = 0.45
    mism = {}
    for k, N in nets.items():
        A, _ = actions(N, N["S"])
        for fr, mine in (("P1", "P1"), ("P3", "P3"), ("CG", "CG|0.45"), ("CG_c05", "CG_c05|0.45"), ("CG-D", "CG-D|0.45")):
            mism[fr] = mism.get(fr, 0) + int((A[mine] != np.asarray(N["act"][fr], object)).sum())
    print("reproduction mismatches", mism, flush=True); assert all(v == 0 for v in mism.values()), mism
    M = boot_mats(nets, NREP, SEED)
    jobs = [(m, s) for m in ("independent", "correlated") for s in range(7, 7 + a.seeds)]
    res = {}
    with Pool(a.workers, initializer=init, initargs=(nets, M)) as pool:
        for i, (mode, seed, out) in enumerate(pool.imap_unordered(worker, jobs)):
            res[(mode, seed)] = out
            if i % 10 == 0: print(i + 1, "/", len(jobs), round(time.time() - t0), "s", flush=True)
    report = {"plan": "PLAN_SUFFICIENCY_STRESS_2026-11-08.md (e30842d)", "networks": len(nets),
              "episodes": int(sum(len(n["snr"]) for n in nets.values())),
              "reviewed_associated": int(sum(n["assoc"].sum() for n in nets.values())),
              "seeds": list(range(7, 7 + a.seeds)), "boot_draws_per_seed": NREP, "boot_seed": SEED,
              "reproduction_mismatches": mism, "modes": {}}
    for mode in ("independent", "correlated"):
        R = {}
        for p in PS:
            seeds = [s for (m, s) in res if m == mode]
            rows = {}
            for rule in RULES:
                vals = {f: [res[(mode, s)][p][0][rule][f] for s in seeds] for f in res[(mode, seeds[0])][p][0][rule]}
                rows[rule] = {f: round(float(np.mean(v)), 3) for f, v in vals.items()}
            cmps = {}
            for name in comparisons():
                obs = [res[(mode, s)][p][1][name][0] for s in seeds]
                pooled = np.concatenate([res[(mode, s)][p][1][name][1] for s in seeds]); pooled = pooled[np.isfinite(pooled)]
                cmps[name] = {"mean_pp": round(float(np.mean(obs)), 3), "seed_range_pp": [round(float(min(obs)), 3), round(float(max(obs)), 3)],
                              "ci95_pp": [round(float(np.percentile(pooled, 2.5)), 3), round(float(np.percentile(pooled, 97.5)), 3)]}
            R[f"{p:.1f}"] = {"rules": rows, "comparisons": cmps}
        report["modes"][mode] = R
    h = report["modes"]["independent"]["0.5"]["comparisons"]
    report["hypotheses_independent_p05"] = {
        "S1_holds": h["S1_P1_minus_CGc05"]["ci95_pp"][0] > 0, "S2_holds": h["S2_CGc05_delta0_minus_045"]["ci95_pp"][0] > 0,
        "S3_holds": h["S3_rise_CGc05_minus_P3_2t"]["ci95_pp"][1] < 0,
        "S1": h["S1_P1_minus_CGc05"], "S2": h["S2_CGc05_delta0_minus_045"], "S3": h["S3_rise_CGc05_minus_P3_2t"]}
    hc = report["modes"]["correlated"]["0.5"]["comparisons"]
    report["hypotheses_correlated_p05"] = {
        "S1_holds": hc["S1_P1_minus_CGc05"]["ci95_pp"][0] > 0, "S2_holds": hc["S2_CGc05_delta0_minus_045"]["ci95_pp"][0] > 0,
        "S3_holds": hc["S3_rise_CGc05_minus_P3_2t"]["ci95_pp"][1] < 0}
    report["seconds"] = round(time.time() - t0, 1)
    json.dump(report, open(os.path.join(OUT, "stress.json"), "w"), indent=1)
    # B. real thin subset
    sub = {k: (N["S"] == "MISSING").sum(0) >= 2 for k, N in nets.items()}
    A = {}; nsrc = {}
    for k, N in nets.items(): A[k], nsrc[k] = actions(N, N["S"])
    summ = summarise(nets, A, nsrc, sub)
    d = {rule: {k: dayvec(nets[k], (A[k][rule] == "D") & nets[k]["assoc"] & sub[k]) for k in nets} for rule in RULES}
    M2 = boot_mats(nets, 2000, SEED); cmpB = {}
    for name, (ra, rb, kind) in comparisons().items():
        if kind != "diff": continue
        obs, v = stat_boot(nets, M2, [(1, d[ra]), (-1, d[rb])], sub); v = v[np.isfinite(v)]
        cmpB[name] = {"diff_pp": round(float(obs), 3), "ci95_pp": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]}
    json.dump({"plan": "PLAN_SUFFICIENCY_STRESS_2026-11-08.md (e30842d)", "episodes": int(sum(m.sum() for m in sub.values())),
               "networks_with_thin": int(sum(m.any() for m in sub.values())), "rules": summ, "comparisons": cmpB},
              open(os.path.join(OUT, "thin_subset.json"), "w"), indent=1)
    print(json.dumps(report["hypotheses_independent_p05"])); print(json.dumps(report["hypotheses_correlated_p05"]))
    print("thin", json.dumps(cmpB)[:600]); print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
