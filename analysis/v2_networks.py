"""Scorer of PREREGISTRATION_V2_NETWORKS_2026-11-08.md (multi-network confirmatory test of rule v2). Written and pushed
BEFORE any waveform, event or detection of these networks was requested. Not executed on data at the time of the push.

Inputs (after the runs): results/v2/selection/chosen.json (networks, roles, sites) and, per network, the pipeline chunks
results/v2/runs/<NET>/out_* (episodes.csv, availability.csv, catalog.csv, summary.json, run.log), produced by the frozen
pipeline/extended_stalta_criteria.py (directly, or through pipeline/p10_v2_datacentre_wrapper.py outside EarthScope).
Roles in P10_STATIONS: reference "MAKZ"; neighbours "S<site>_<member>" (S1_1, S1_2, S2_1, ...), site 1 = nearest.

Rule v2 (merge_sites): a site is YES if any member is YES; NO if no member is YES and at least one member is NO (i.e. every
valid member NO); MISSING if every member is MISSING. One weight per site by site rank: 0.25 / 0.20 / 0.15, SNR 0.40.
Everything else frozen: theta_A 0.60, delta 0.45, theta_D 0.16, c = 1 for a valid NO (CG), c = 0.5 (CG c05), CG-D with the
IU.MAKZ development table mapped by site rank (1 -> MK31, 2 -> KURK, 3 -> WUS), P1, P1t 8.0 dB, P2 10.5 dB, P3 7.5 dB, P3 8.0 dB.
Output: results/v2/v2_eval.json
"""
import os, re, json, glob
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
W_RANK = [0.25, 0.20, 0.15]; W_SNR = 0.40
THETA_A, THETA_D, DELTA = 0.60, 0.16, 0.45
MARGIN_PP, RATIO_MAX = 3.0, 1.5
NBOOT, SEED = 2000, 7
DEV_ROLE_BY_RANK = ["MK31", "KURK", "WUS"]
MIN_ASSOC = 30           # a network enters the pooled analysis with >= 30 associated episodes
ASSOC = (-15.0, 0.0)


def _tab():
    for f in [os.path.join(R, "prereg", "detectability_tables_dev.json"), os.path.join(R, "detectability_tables_dev.json")]:
        if os.path.exists(f): return json.load(open(f))
    return {}


TAB = _tab()


# ------------------------------------------------------------------ rule v2
def merge_sites(states, sites):
    """states: {role: array of 'YES'/'NO'/'MISSING'}; sites: list (nearest first) of lists of member roles.
    Returns list of site-state arrays in the same order."""
    out = []
    for members in sites:
        M = np.vstack([np.asarray(states[m], dtype=object) for m in members])
        yes = (M == "YES").any(0); no = (M == "NO").any(0)
        out.append(np.where(yes, "YES", np.where(no, "NO", "MISSING")).astype(object))
    return out


def group_by_distance(dist_km_pairs, d_merge=50.0):
    """Greedy seed grouping of the selection rule: dist_km_pairs = [(role, distance_to_ref, (lat, lon))] in any order.
    A station joins the first site whose seed is within d_merge km; otherwise it seeds a new site. Returns lists of roles."""
    import math
    def km(a, b):
        la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))
    sites = []
    for role, d, pos in sorted(dist_km_pairs, key=lambda x: x[1]):
        for s in sites:
            if km(pos, s["seed"]) <= d_merge: s["m"].append(role); break
        else:
            sites.append({"seed": pos, "m": [role]})
    return [s["m"] for s in sites]


def policies(site_states, snr, ok, table_ref="MAKZ"):
    """Frozen policies on site states (list, nearest first, at most 3 used)."""
    S = site_states[:3]; n = len(snr)
    yes = np.zeros(n, bool); no = np.zeros(n, bool)
    for s in S: yes |= s == "YES"; no |= s == "NO"
    act = {"P1": np.where(yes, "A", "D").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "A", "D").astype(object)}
    for name, t, need_no in [("P3", 7.5, False), ("P3_8.0", 8.0, False), ("P2", 10.5, True)]:
        a = np.full(n, "E", dtype=object); a[yes & ok & (snr >= t)] = "A"
        d = (~yes) & ok & (snr < t)
        if need_no: d &= no
        a[d] = "D"; act[name] = a
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    for name in ["CG", "CG-D", "CG_c05"]:
        num = np.zeros(n); den = np.zeros(n)
        for r, s in enumerate(S):
            q = np.isin(s, ["YES", "NO"]).astype(float)
            if name == "CG-D":
                tab = TAB.get(table_ref, {}).get(DEV_ROLE_BY_RANK[r], {})
                p = np.array([tab.get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b])
                q = np.where(s == "NO", p, q)
            if name == "CG_c05": q = np.where(s == "NO", 0.5, q)
            num += W_RANK[r] * (s == "YES") * q; den += W_RANK[r] * q
        num += W_SNR * np.clip(snr / 30, 0, 1) * ok; den += W_SNR * ok
        dd = den >= DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(n, "E", dtype=object); a[dd & (D >= THETA_A)] = "A"; a[dd & (D <= THETA_D)] = "D"; act[name] = a
    return act


# ------------------------------------------------------------------ statistics
def day_boot(days, assoc, a, b, n=NBOOT, seed=SEED):
    """Published day bootstrap (days with episodes, 2000, seed 7): difference of dismissed share of associated, pp."""
    ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((a[ids] == "D").mean() - (b[ids] == "D").mean()) * 100)
    v = np.array(v); obs = ((a[assoc] == "D").mean() - (b[assoc] == "D").mean()) * 100
    return {"diff_pp": round(float(obs), 2), "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
            "p_one_sided_H0_ge_margin": round(float(((v >= MARGIN_PP).sum() + 1) / (len(v) + 1)), 5),
            "noninferior": bool(np.percentile(v, 97.5) <= MARGIN_PP)}


def cluster_boot(nets, pa, pb, n=NBOOT, seed=SEED):
    """Pooled primary: two-stage cluster bootstrap - networks resampled with replacement, then days within each drawn network.
    nets: {net: (days, assoc, actions dict)}. Returns episode-pooled difference (primary), equal-weight mean of per-network
    differences (secondary) and the pooled ratio of dismissed counts with +0.5 continuity (relative criterion)."""
    names = sorted(nets); rng = np.random.default_rng(seed)
    per = {}
    for k in names:
        days, assoc, act = nets[k]; ud = np.array(sorted(set(days)))
        idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
        per[k] = (ud, idx, act[pa] == "D", act[pb] == "D", assoc)

    def stat(draw):
        na = da = db = 0.0; diffs = []
        for k, sel in draw:
            ud, idx, A, B, assoc = per[k]
            ids = np.concatenate([idx[d] for d in sel]) if len(sel) else np.array([], int)
            if not len(ids): continue
            na += len(ids); da += A[ids].sum(); db += B[ids].sum(); diffs.append((A[ids].mean() - B[ids].mean()) * 100)
        if na == 0: return None
        return (da - db) / na * 100, float(np.mean(diffs)), (da + 0.5) / (db + 0.5)

    obs = stat([(k, per[k][0]) for k in names])
    v = []
    for _ in range(n):
        ks = rng.choice(names, len(names))
        s = stat([(k, rng.choice(per[k][0], len(per[k][0]))) for k in ks])
        if s: v.append(s)
    v = np.array(v)
    q = lambda c: [round(float(np.percentile(v[:, c], 2.5)), 3), round(float(np.percentile(v[:, c], 97.5)), 3)]
    return {"networks": len(names), "pooled_diff_pp": round(obs[0], 2), "pooled_ci95_pp": q(0),
            "pooled_noninferior": bool(np.percentile(v[:, 0], 97.5) <= MARGIN_PP),
            "equal_weight_diff_pp": round(obs[1], 2), "equal_weight_ci95_pp": q(1),
            "ratio": round(obs[2], 3), "ratio_ci95": q(2), "ratio_criterion_holds": bool(np.percentile(v[:, 2], 97.5) <= RATIO_MAX)}


def holm(pvals):
    keys = sorted(pvals, key=lambda k: pvals[k]); m = len(keys); out = {}; run = 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (m - i) * pvals[k])); out[k] = round(run, 5)
    return out


def assoc_vec(P, t_on, t_off):
    P = np.sort(P[np.isfinite(P)])
    if not len(P): return np.zeros(len(t_on), bool)
    i = np.searchsorted(P, t_on + ASSOC[0], side="left")
    return (i < len(P)) & (P[np.minimum(i, len(P) - 1)] <= t_off + ASSOC[1])


def chance_control(ep, cat, av, act, n=100, seed=SEED):
    """Shifted-catalogue control of analysis/review_posthoc.py block 1 (fixed here): predicted P arrivals shifted by
    uniform 1..7 days with random sign (100 shifts, seed 7), wrapped circularly in the calendar span, re-associated with the
    pipeline rule; expected chance-associated episodes and chance CG - P3 excess dismissals."""
    rng = np.random.default_rng(seed); offs = rng.uniform(1, 7, n) * 86400 * rng.choice([-1, 1], n)
    t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy(); pp = cat.p_pred.to_numpy(dtype=float)
    t0 = pd.Timestamp(av.day.min()).timestamp(); span = pd.Timestamp(av.day.max()).timestamp() + 86400 - t0
    rows = []
    for o in offs:
        s = assoc_vec(t0 + np.mod(pp + o - t0, span), t_on, t_off)
        rows.append((s.sum(), ((act["CG"] == "D") & s).sum() - ((act["P3"] == "D") & s).sum()))
    rows = np.array(rows, float); assoc = (ep.assoc_event >= 0).to_numpy()
    real = ((act["CG"] == "D") & assoc).sum() - ((act["P3"] == "D") & assoc).sum()
    corr = (real - rows[:, 1].mean()) / max(assoc.sum() - rows[:, 0].mean(), 1) * 100
    return {"chance_associated_mean": round(float(rows[:, 0].mean()), 2), "chance_CG_minus_P3_excess_mean": round(float(rows[:, 1].mean()), 2),
            "real_CG_minus_P3_excess": int(real), "chance_corrected_CG_minus_P3_pp": round(float(corr), 2)}


# ------------------------------------------------------------------ per network
RUN_DIRS = ["runs"]      # run-list/directory mode only (EXT: runs_ext12; AEXT: runs + runs_ext12 concatenated by date)


def load_network(net, cfg):
    dirs = sorted(glob.glob(os.path.join(R, "v2", RUN_DIRS[0], net, "out_*")))
    for extra in RUN_DIRS[1:]:
        more = sorted(glob.glob(os.path.join(R, "v2", extra, net, "out_*")))
        if not more: return None      # combined modes: the extension itself must exist, never score the base alone
        dirs += more
    if not dirs: return None
    # 08.11 (FLEET_DEVIATIONS): a chunk without outputs = run not completed -> excluded, never partially scored
    if any(not os.path.exists(os.path.join(d, "episodes.csv")) for d in dirs): return "incomplete"
    ep = pd.concat([pd.read_csv(os.path.join(d, "episodes.csv")) for d in dirs], ignore_index=True)
    av = pd.concat([pd.read_csv(os.path.join(d, "availability.csv")) for d in dirs]).drop_duplicates("day").sort_values("day")
    cat = pd.concat([pd.read_csv(os.path.join(d, "catalog.csv")) for d in dirs], ignore_index=True)
    fails = sorted({f for d in dirs for f in json.load(open(os.path.join(d, "summary.json"))).get("catalog_failures", [])})
    ep["day"] = ep.t_on_utc.str[:10]
    return ep, av, cat, fails


def evaluate_network(net, cfg):
    got = load_network(net, cfg)
    if got is None: return {"status": "no run outputs"}
    if got == "incomplete": return {"status": "not completed (chunk without outputs)"}
    ep, av, cat, fails = got
    sites = [[f"S{i + 1}_{j + 1}" for j in range(len(s["members"]))] for i, s in enumerate(cfg["sites"])]
    states = {r: ep[f"n_{r}"].astype(str).to_numpy() for s in sites for r in s}
    S = merge_sites(states, sites)
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    act = policies(S, snr, ok)
    # comparator: the frozen v1 rule (every neighbour station separate, three nearest stations by distance)
    v1_roles = sorted([r for s in sites for r in s], key=lambda r: [m["dist_km"] for si, s in enumerate(cfg["sites"]) for mi, m in enumerate(s["members"]) if f"S{si + 1}_{mi + 1}" == r][0])[:3]
    act["CG_v1"] = policies([states[r] for r in v1_roles], snr, ok)["CG"]
    assoc = (ep.assoc_event >= 0).to_numpy(); days = ep.day.to_numpy(); nd = len(av)
    site_share = []
    for s in sites:
        site_share.append(av[[f"{r}_valid_share" for r in s]].max(axis=1).to_numpy())
    outage_days = set(av.day.to_numpy()[site_share[0] < 0.10]); outage = ep.day.isin(outage_days).to_numpy()
    summ = lambda a, m, n: {"assoc": int((assoc & m).sum()), "dismissed_assoc": int(((a == "D") & assoc & m).sum()),
                            "unassoc_alerts": int(((a == "A") & ~assoc & m).sum()), "esc_per_day": round(float(((a == "E") & m).sum()) / max(n, 1), 2)}
    allm = np.ones(len(ep), bool); allmiss = np.all([s == "MISSING" for s in S], axis=0)
    res = {"calendar_days": int(nd), "episodes": int(len(ep)), "associated": int(assoc.sum()), "catalogue_failures": fails,
           "included_in_pooled": bool(assoc.sum() >= MIN_ASSOC and not fails),
           "sites": sites, "site_with_two_members": any(len(s) == 2 for s in sites),
           "pair_members_disagree_episodes": int(sum((states[s[0]] != states[s[1]]).sum() for s in sites if len(s) == 2)),
           "all": {k: summ(a, allm, nd) for k, a in act.items()},
           "outage_nearest_site": {"days": len(outage_days), **{k: summ(a, outage, len(outage_days)) for k, a in act.items()}},
           "H_noninferiority": {f"{k}-P3": day_boot(days, assoc, act[k], act["P3"]) for k in ["CG", "CG-D", "CG_c05"]},
           "H_noninferiority_vs_P3_8.0": {f"{k}-P3_8.0": day_boot(days, assoc, act[k], act["P3_8.0"]) for k in ["CG", "CG-D", "CG_c05"]},
           "H_v2_vs_v1": {"CG_v2": int(((act["CG"] == "D") & assoc).sum()), "CG_v1": int(((act["CG_v1"] == "D") & assoc).sum())},
           "H_unassoc_alerts": {"CG": int(((act["CG"] == "A") & ~assoc).sum()), "P3": int(((act["P3"] == "A") & ~assoc).sum()),
                                "P1t": int(((act["P1t"] == "A") & ~assoc).sum())},
           "H_all_missing_escalated": {"episodes": int(allmiss.sum()), "CG_escalated": int((act["CG"][allmiss] == "E").sum())},
           "chance_control": chance_control(ep, cat, av, act)}
    return res, (days, assoc, act), outage


def run_list(batch):
    """Network configurations to score. Default (no argument): chosen.json as pushed with the batch-A plan.
    'B': results/v2/networks_batchB.json -> v2_eval_batchB.json (PREREGISTRATION_V2_BATCHB_2026-11-08.md, primary of batch B).
    'AB': results/v2/networks.json + networks_batchB.json -> v2_eval_AB.json (combined A+B, secondary).
    Added 08.11.2026 before any v2 output was scored, run list/directory only, no computation changed:
    'A': results/v2/networks.json (amendment A1, 10 networks) -> v2_eval_batchA.json. The default reads chosen.json, i.e. the
         24 networks chosen BEFORE amendment A1 (12 of them are batch-B networks, 2 are never run); kept as pushed.
    'EXT': networks_ext12.json, outputs results/v2/runs_ext12/<NET>/ -> v2_eval_ext12.json (PREREGISTRATION_V2_EXT12).
    'AEXT': same networks, runs/<NET>/out_* and runs_ext12/<NET>/out_* concatenated by date -> v2_eval_A_ext12.json; pooled set =
         networks included in both v2_eval_batchA.json and v2_eval_ext12.json (ext12 plan section 4); run A and EXT first."""
    V = os.path.join(R, "v2")
    if batch == "A":   # amendment A1 run list (10 networks); chosen.json holds the 24 chosen before A1 (incl. batch-B networks)
        return json.load(open(os.path.join(V, "networks.json")))["networks"], "v2_eval_batchA.json", "PREREGISTRATION_V2_NETWORKS_2026-11-08.md (batch A, amendment A1 run list networks.json)"
    if batch in ("EXTB", "BEXTB"):   # PREREGISTRATION_V2_EXT12_B: run-list/directory mode only, no computation changed
        RUN_DIRS[:] = ["runs_ext12B"] if batch == "EXTB" else ["runs", "runs_ext12B"]
        return (json.load(open(os.path.join(V, "networks_ext12B.json")))["networks"],
                "v2_eval_ext12B.json" if batch == "EXTB" else "v2_eval_B_ext12B.json",
                "PREREGISTRATION_V2_EXT12_B_2026-11-08.md (" + ("ext period alone" if batch == "EXTB" else "batch-B period + ext period, combined") + ")")
    if batch in ("EXT", "AEXT"):
        RUN_DIRS[:] = ["runs_ext12"] if batch == "EXT" else ["runs", "runs_ext12"]
        return (json.load(open(os.path.join(V, "networks_ext12.json")))["networks"],
                "v2_eval_ext12.json" if batch == "EXT" else "v2_eval_A_ext12.json",
                "PREREGISTRATION_V2_EXT12_2026-11-08.md (" + ("ext period alone" if batch == "EXT" else "batch-A period + ext period, combined") + ")")
    if batch == "C":   # PREREGISTRATION_V2_BATCHC_2026-11-08.md: run list only, no computation changed
        return json.load(open(os.path.join(V, "networks_batchC.json")))["networks"], "v2_eval_batchC.json", "PREREGISTRATION_V2_BATCHC_2026-11-08.md (batch C)"
    if batch == "ABC":
        return (sum((json.load(open(os.path.join(V, f)))["networks"] for f in ("networks.json", "networks_batchB.json", "networks_batchC.json")), []),
                "v2_eval_ABC.json", "PREREGISTRATION_V2_BATCHC_2026-11-08.md (combined A+B+C, secondary)")
    if batch == "B":
        return json.load(open(os.path.join(V, "networks_batchB.json")))["networks"], "v2_eval_batchB.json", "PREREGISTRATION_V2_BATCHB_2026-11-08.md (batch B)"
    if batch == "AB":
        return (json.load(open(os.path.join(V, "networks.json")))["networks"] + json.load(open(os.path.join(V, "networks_batchB.json")))["networks"],
                "v2_eval_AB.json", "PREREGISTRATION_V2_BATCHB_2026-11-08.md (combined A+B, secondary)")
    return json.load(open(os.path.join(V, "selection", "chosen.json")))["chosen"], "v2_eval.json", "PREREGISTRATION_V2_NETWORKS_2026-11-08.md"


def main(batch=None):
    cfgs, fname, prereg = run_list(batch)
    out = {"preregistration": prereg, "networks": {}}
    pooled, outage_pool = {}, {"assoc": 0, "CG": 0, "P1": 0, "networks": 0}
    for cfg in cfgs:
        net = cfg["network"]; r = evaluate_network(net, cfg)
        if isinstance(r, dict): out["networks"][net] = r; continue
        res, data, outage = r; out["networks"][net] = res
        if batch == "BEXTB":   # ext12B plan: combined set = networks included in BOTH the batch-B and the ext12B-alone analysis
            inc = [json.load(open(os.path.join(R, "v2", f)))["networks"].get(net, {}).get("included_in_pooled", False)
                   for f in ("v2_eval_batchB.json", "v2_eval_ext12B.json")]
            res["included_batchB"], res["included_ext_alone"] = inc
            res["included_in_pooled"] = bool(res["included_in_pooled"] and all(inc))
        if batch == "AEXT":   # ext12 plan s.4: combined set = networks included in BOTH the batch-A and the ext-alone analysis
            inc = [json.load(open(os.path.join(R, "v2", f)))["networks"].get(net, {}).get("included_in_pooled", False)
                   for f in ("v2_eval_batchA.json", "v2_eval_ext12.json")]
            res["included_batchA"], res["included_ext_alone"] = inc
            res["included_in_pooled"] = bool(res["included_in_pooled"] and all(inc))
        if res["included_in_pooled"]: pooled[net] = data
        o = res["outage_nearest_site"]
        if o["CG"]["assoc"]:
            outage_pool["networks"] += 1; outage_pool["assoc"] += o["CG"]["assoc"]
            outage_pool["CG"] += o["CG"]["dismissed_assoc"]; outage_pool["P1"] += o["P1"]["dismissed_assoc"]
    if pooled:
        out["PRIMARY_pooled_CG_minus_P3"] = cluster_boot(pooled, "CG", "P3")
        out["pooled_CGD_minus_P3"] = cluster_boot(pooled, "CG-D", "P3")
        out["pooled_CGc05_minus_P3"] = cluster_boot(pooled, "CG_c05", "P3")
        out["pooled_CG_minus_P3_8.0"] = cluster_boot(pooled, "CG", "P3_8.0")
        out["pooled_CG_v2_minus_CG_v1"] = cluster_boot(pooled, "CG", "CG_v1")
        out["per_network_holm_CG_minus_P3"] = holm({k: out["networks"][k]["H_noninferiority"]["CG-P3"]["p_one_sided_H0_ge_margin"] for k in pooled})
    out["outage_hypothesis"] = {**outage_pool, "exercised": outage_pool["assoc"] >= 10 and outage_pool["networks"] >= 2,
                                "holds": (outage_pool["CG"] < outage_pool["P1"]) if outage_pool["assoc"] >= 10 and outage_pool["networks"] >= 2 else None}
    os.makedirs(os.path.join(R, "v2"), exist_ok=True)
    json.dump(out, open(os.path.join(R, "v2", fname), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "networks"}, indent=1, default=str))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
