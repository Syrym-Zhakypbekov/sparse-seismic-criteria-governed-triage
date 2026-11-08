"""Analyses of PLAN_GAP_REVIEWED_2026-11-08.md (post hoc, method fixed before computing; pushed 0cd7a45).

G1 overlap CG_c05 vs P3; G2 chance-corrected pooled difference with a network bootstrap; G3 margin 2/3/4 and
zero-discordance exclusion; G4 leave-one-network-out and without JP; G5 Holm and Benjamini-Yekutieli over the enlarged
family. Frozen decisions, frozen bootstrap (analysis/v2_networks.py: 2000 resamples, seed 7). No download.
"""
import os, sys, json, pickle, importlib.util, time
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
spec = importlib.util.spec_from_file_location("v2g", os.path.join(here, "v2_networks.py"))
v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
OUT = os.path.join(root, "results", "gap"); os.makedirs(OUT, exist_ok=True)
POL = ["CG", "CG-D", "CG_c05"]; NB, SEED = v2.NBOOT, v2.SEED


def load():
    r = pickle.load(open(os.path.join(root, "results", "posthoc", "_collect_reviewed.pkl"), "rb"))
    return {k: v for k, v in sorted(r.items()) if v.get("included")}


def nets_for(R, keep=None):
    return {k: (v["days"], v["assoc"], v["act"]) for k, v in R.items() if keep is None or k in keep}


# ---------------------------------------------------------------- G1
def g1(R):
    acts = ["A", "D", "E"]
    def table(mask_fn):
        T = np.zeros((3, 3), int); a_only = []; p_only = []
        for k, v in R.items():
            m = mask_fn(v); c, p = np.asarray(v["act"]["CG_c05"])[m], np.asarray(v["act"]["P3"])[m]
            for i, x in enumerate(acts):
                for j, y in enumerate(acts): T[i, j] += int(((c == x) & (p == y)).sum())
            S = np.stack([np.asarray(s)[m] for s in v["S"]], 1); snr = v["snr"][m]
            for sel, store in (((c == "D") & (p != "D"), a_only), ((p == "D") & (c != "D"), p_only)):
                for row, s in zip(S[sel], snr[sel]):
                    store.append(("NO_with_MISSING" if any(str(x) != "NO" and str(x) != "YES" for x in row) else
                                  ("all_NO" if all(str(x) == "NO" for x in row) else "has_YES"), float(s)))
        dc, dp = T[1, :].sum(), T[:, 1].sum(); both = T[1, 1]
        def comp(lst):
            if not lst: return {"n": 0}
            st = [x for x, _ in lst]; s = np.array([y for _, y in lst]); s = s[np.isfinite(s)]
            return {"n": len(lst), "states": {u: st.count(u) for u in sorted(set(st))},
                    "snr_db_median_q1_q3": [round(float(np.percentile(s, q)), 2) for q in (50, 25, 75)] if len(s) else None}
        return {"rows_CG_c05_cols_P3_order_A_D_E": T.tolist(), "dismissed_CG_c05": int(dc), "dismissed_P3": int(dp),
                "dismissed_both": int(both), "jaccard": round(float(both / (dc + dp - both)), 4) if dc + dp - both else None,
                "agreement_all_actions": round(float(np.trace(T) / T.sum()), 4),
                "CG_c05_only": comp(a_only), "P3_only": comp(p_only)}
    return {"all_episodes": table(lambda v: np.ones(len(v["assoc"]), bool)),
            "reviewed_associated": table(lambda v: np.asarray(v["assoc"], bool))}


# ---------------------------------------------------------------- G2
def g2():
    d = json.load(open(os.path.join(root, "results", "posthoc", "chance_by_policy.json")))["sets"]["reviewed"]["per_network"]
    names = sorted(d); rng = np.random.default_rng(SEED)
    def stat(ks, pol):
        num = den = 0.0
        for k in ks:
            x = d[k]; den += x["assoc"] - x["chance_assoc"]
            num += (x["dismissed"][pol] - x["chance_dismissed"][pol]) - (x["dismissed"]["P3"] - x["chance_dismissed"]["P3"])
        return num / den * 100
    out = {"networks": len(names)}
    draws = [rng.choice(names, len(names)) for _ in range(NB)]
    for pol in POL:
        v = np.array([stat(ks, pol) for ks in draws]); hi = float(np.percentile(v, 97.5))
        out[pol] = {"chance_corrected_diff_pp": round(stat(names, pol), 3),
                    "ci95_pp": [round(float(np.percentile(v, 2.5)), 3), round(hi, 3)], "noninferior_3pp": bool(hi <= 3.0)}
    return out


# ---------------------------------------------------------------- bootstrap with draws kept
def cboot(nets, pa, pb, n=NB, seed=SEED):
    names = sorted(nets); rng = np.random.default_rng(seed); per = {}
    for k in names:
        days, assoc, act = nets[k]; ud = np.array(sorted(set(days)))
        idx = {dd: np.flatnonzero((days == dd) & assoc) for dd in ud}
        per[k] = (ud, idx, np.asarray(act[pa]) == "D", np.asarray(act[pb]) == "D")
    def stat(draw):
        na = da = db = 0.0
        for k, sel in draw:
            ud, idx, A, B = per[k]; ids = np.concatenate([idx[x] for x in sel]) if len(sel) else np.array([], int)
            if len(ids): na += len(ids); da += A[ids].sum(); db += B[ids].sum()
        return ((da - db) / na * 100, (da + 0.5) / (db + 0.5)) if na else None
    obs = stat([(k, per[k][0]) for k in names]); v = []
    for _ in range(n):
        ks = rng.choice(names, len(names)); s = stat([(k, rng.choice(per[k][0], len(per[k][0]))) for k in ks])
        if s: v.append(s)
    return obs, np.array(v)


def zero_disc(v, pa, pb):
    a = np.asarray(v["act"][pa])[np.asarray(v["assoc"], bool)] == "D"; b = np.asarray(v["act"][pb])[np.asarray(v["assoc"], bool)] == "D"
    return bool((a == b).all())


def g3(R):
    out = {}
    for pol in POL:
        obs, v = cboot(nets_for(R), pol, "P3"); hi = float(np.percentile(v[:, 0], 97.5))
        zd = [k for k, x in R.items() if zero_disc(x, pol, "P3")]
        obs2, v2_ = cboot(nets_for(R, [k for k in R if k not in zd]), pol, "P3"); hi2 = float(np.percentile(v2_[:, 0], 97.5))
        out[pol] = {"pooled_diff_pp": round(obs[0], 3), "upper95_pp": round(hi, 3),
                    "verdict_by_margin": {str(m): bool(hi <= m) for m in (2, 3, 4)},
                    "ratio_upper95": round(float(np.percentile(v[:, 1], 97.5)), 3),
                    "zero_discordance_networks": zd, "n_zero_discordance": len(zd),
                    "without_zero_discordance": {"networks": len(R) - len(zd), "pooled_diff_pp": round(obs2[0], 3),
                                                 "ci95_pp": [round(float(np.percentile(v2_[:, 0], 2.5)), 3), round(hi2, 3)],
                                                 "noninferior_3pp": bool(hi2 <= 3.0),
                                                 "ratio_upper95": round(float(np.percentile(v2_[:, 1], 97.5)), 3)},
                    "p_one_sided_pooled": round(float(((v[:, 0] >= 3.0).sum() + 1) / (len(v) + 1)), 5)}
    return out


def g4(R, base):
    out = {}
    for pol in POL:
        rows = {}
        for k in R:
            obs, v = cboot(nets_for(R, [x for x in R if x != k]), pol, "P3")
            rows[k] = {"pooled_diff_pp": round(obs[0], 3), "upper95_pp": round(float(np.percentile(v[:, 0], 97.5)), 3)}
        ups = [x["upper95_pp"] for x in rows.values()]; diffs = [x["pooled_diff_pp"] for x in rows.values()]
        base_met = base[pol]["upper95_pp"] <= 3.0
        flips = [k for k, x in rows.items() if (x["upper95_pp"] <= 3.0) != base_met]
        out[pol] = {"diff_range_pp": [min(diffs), max(diffs)], "upper95_range_pp": [min(ups), max(ups)],
                    "verdict_full": base_met, "removals_changing_verdict": flips,
                    "without_JP": rows.get("JP"), "per_removed_network": rows}
        eq = v2.cluster_boot(nets_for(R), pol, "P3")
        out[pol]["equal_weight_diff_pp"] = eq["equal_weight_diff_pp"]; out[pol]["equal_weight_ci95_pp"] = eq["equal_weight_ci95_pp"]
        out[pol]["pooled_check_v2_cluster_boot"] = {"pooled_diff_pp": eq["pooled_diff_pp"], "ci95": eq["pooled_ci95_pp"]}
    return out


def holm_by(p, alpha=0.025):
    keys = sorted(p, key=lambda k: p[k]); m = len(keys); holm = {}; run = 0.0
    for i, k in enumerate(keys): run = max(run, min(1.0, (m - i) * p[k])); holm[k] = run
    c = sum(1.0 / i for i in range(1, m + 1)); by = {}; run = 1.0
    for i in range(m - 1, -1, -1):
        k = keys[i]; run = min(run, min(1.0, p[k] * m * c / (i + 1))); by[k] = run
    return holm, by


def g5(R, g3r):
    fam = {}
    cp = json.load(open(os.path.join(root, "results", "posthoc", "review_posthoc.json")))["7_multiplicity"]["rows"]
    for row in cp: fam["earlier9:" + row["test"]] = row["p_one_sided"]
    for pol in POL: fam["reviewed_pooled:" + pol] = g3r[pol]["p_one_sided_pooled"]
    for k, v in R.items():
        for pol in POL:
            r = v2.day_boot(v["days"], np.asarray(v["assoc"], bool), np.asarray(v["act"][pol]), np.asarray(v["act"]["P3"]))
            fam[f"reviewed_net:{k}:{pol}"] = r["p_one_sided_H0_ge_margin"]
    holm, by = holm_by(fam)
    met_raw = [k for k, x in fam.items() if x <= 0.025]
    return {"family_size": len(fam), "alpha_one_sided": 0.025, "met_unadjusted": len(met_raw),
            "met_after_holm": sum(holm[k] <= 0.025 for k in met_raw), "met_after_BY": sum(by[k] <= 0.025 for k in met_raw),
            "pooled_and_earlier": {k: {"p": fam[k], "holm": round(holm[k], 5), "BY": round(by[k], 5)}
                                   for k in fam if not k.startswith("reviewed_net:")},
            "per_network": {k: {"p": fam[k], "holm": round(holm[k], 5), "BY": round(by[k], 5)} for k in fam if k.startswith("reviewed_net:")}}


def figure(res):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    a = res["G1_overlap"]["reviewed_associated"]
    lab = ["both dismiss", "CG c=0.5 only", "P3 only"]
    vals = [a["dismissed_both"], a["CG_c05_only"]["n"], a["P3_only"]["n"]]
    ax[0].bar(lab, vals, color=["#595959", "#A42421", "#BABABA"]); ax[0].set_title("Reviewed-associated alarms dismissed (33 networks)")
    for i, x in enumerate(vals): ax[0].text(i, x, str(x), ha="center", va="bottom")
    for j, pol in enumerate(POL):
        u = sorted(x["upper95_pp"] for x in res["G4_leave_one_out"][pol]["per_removed_network"].values())
        ax[1].plot(range(len(u)), u, "o-", ms=3, label=pol.replace("_c05", " c=0.5"))
    ax[1].axhline(3.0, color="k", ls="--", lw=1); ax[1].set_xlabel("removed network (sorted)"); ax[1].set_ylabel("upper 95% bound, points")
    ax[1].set_title("Leave-one-network-out, difference vs P3"); ax[1].legend()
    fig.tight_layout(); p = os.path.join(root, "figures", "fig_gap_overlap_loo.png"); fig.savefig(p, dpi=600); return p


if __name__ == "__main__":
    t = time.time(); R = load(); res = {"plan": "PLAN_GAP_REVIEWED_2026-11-08.md (0cd7a45), post hoc", "networks": sorted(R)}
    res["G1_overlap"] = g1(R); res["G2_chance_corrected"] = g2(); res["G3_margin_zero_discordance"] = g3(R)
    res["G4_leave_one_out"] = g4(R, res["G3_margin_zero_discordance"]); res["G5_multiplicity"] = g5(R, res["G3_margin_zero_discordance"])
    res["figure"] = os.path.relpath(figure(res), root).replace("\\", "/"); res["seconds"] = round(time.time() - t, 1)
    json.dump(res, open(os.path.join(OUT, "gap_reviewed.json"), "w"), indent=1)
    print("done", res["seconds"])
