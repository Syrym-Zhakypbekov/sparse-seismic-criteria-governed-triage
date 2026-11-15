"""POST HOC (08.11.2026), analyses requested by the internal review on manuscript v21/v22
(internal review).
Nothing here was pre-specified; no frozen parameter is changed; the pre-specified results stay as published.
Only data already in results/ are used (episodes.csv, catalog.csv, availability.csv, run logs, detector_coverage.json).

Blocks (each labelled post hoc in the output):
 1 chance association: catalogue P arrivals shifted by random offsets (+-1..7 days, 100 shifts, seed 7; and +-10..60 min,
   20 shifts, the control of Appendix B), re-associated with the pipeline's own rule (stage1_pipeline.py: an episode is
   associated when some predicted P lies in [t_on - 15 s, t_off]); expected chance-associated episodes and their
   dismissals per frozen policy, against the real CG-P3 and CG-D-P3 excess.
 2 catalogue density per month (regional events within 15 deg per calendar day) and associated episodes per day, with the
   per-month CG-P3 dismissed-share difference, for development, held-out and every test set.
 3 G.WUS availability per period, and CG with the G.WUS role forced MISSING on every set where that role is G.WUS.
 4 II.KURK reference: IU.MAKZ and IM.MK31 (24 km apart) merged into one site (YES if either YES, NO if either NO and none
   YES, MISSING if both MISSING), weighted once; CG-P3 with the published day bootstrap.
 5 Alaska: episodes with AK.L22K (role MK31) MISSING among associated episodes; CG, CG-D and P3 dismissals there.
 6 Alaska added to the out-of-sample operating-point comparison (selection on development only, as in
   analysis/oos_operating_points.py, whose selection code is executed unchanged).
 7 multiplicity: one-sided bootstrap p-value of H0 "difference >= 3 pp" for each primary margin contrast, from the
   published day bootstrap (days with episodes, 2000 resamples, seed 7) recomputed here, then Holm across the family.
 8 detector miss rate (from results/stage1_v3/detector_coverage.json) and what can and cannot be said about Pn.
Output: results/posthoc/cold_panel_posthoc.json
"""
import os, json, glob, re
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
src = open(os.path.join(root, "analysis", "r12_checks.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(root, "analysis", "r12_checks.py")}
exec(compile(src[:src.index("E = os.path.join(R, \"extended\")")], "r12_helpers", "exec"), ns)
load, policies = ns["load"], ns["policies"]
LABEL = "post hoc (internal review, 08.11.2026); not pre-specified"
ASSOC = (-15.0, 0.0)          # pipeline/stage1_pipeline.py line 40 and extended_stalta_criteria.py line 43
MARGIN = 3.0

E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {"extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
        "extended II.KURK": (sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
        "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
        "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
        "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
        "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}
DEV_DIST = {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}
EXTRA = {"development (IU.MAKZ)": os.path.join(R, "stage1_v3"), "held-out (IU.MAKZ)": os.path.join(R, "heldout")}
# sets whose "WUS" role column is G.WUS (KZ: role WUS = KZ.PDGK; AK: role WUS = an AK station)
GWUS_SETS = ["development (IU.MAKZ)", "held-out (IU.MAKZ)", "extended IU.MAKZ", "extended II.KURK", "2024 IU.MAKZ", "2024 II.KURK"]


def load_any(name):
    if name in EXTRA:
        d = EXTRA[name]; ep = pd.read_csv(os.path.join(d, "episodes.csv")); ep["day"] = ep.t_on_utc.str[:10]
        av = pd.read_csv(os.path.join(d, "availability.csv")); cat = pd.read_csv(os.path.join(d, "catalog.csv"))
        return ep, av, dict(DEV_DIST), cat, "MAKZ"
    dirs, ref = SETS[name]; ep, av, dist = load(dirs)
    cat = pd.concat([pd.read_csv(os.path.join(d, "catalog.csv")) for d in dirs if os.path.exists(os.path.join(d, "catalog.csv"))], ignore_index=True)
    cat = cat.drop_duplicates(subset=["time", "lat", "lon"]).reset_index(drop=True)
    return ep, av, dist, cat, ref


def frozen_actions(ep, dist, ref):
    P = policies(ep, dist, ref)
    NB = [k[2:] for k in ep.columns if k.startswith("n_")]
    yes = np.zeros(len(ep), bool)
    for k in NB: yes |= ep[f"n_{k}"].astype(str).to_numpy() == "YES"
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    P["P1t"] = np.where(yes | (ok & (snr >= 8.0)), "A", "D").astype(object)
    return P


def cg_custom(S, W, snr, ok, thd=0.16, tha=0.60, delta=0.45):
    """Frozen CG (c = 1) for an arbitrary neighbour-state dict S and weight dict W (same formula as r12_checks.policies)."""
    n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for k in S:
        q = np.isin(S[k], ["YES", "NO"]).astype(float); num += W[k] * (S[k] == "YES") * q; den += W[k] * q
    num += 0.40 * np.clip(snr / 30, 0, 1) * ok; den += 0.40 * ok
    dd = den >= delta; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(n, "E", dtype=object); a[dd & (D >= tha)] = "A"; a[dd & (D <= thd)] = "D"; return a


def p3_custom(S, snr, ok, tau=7.5):
    yes = np.zeros(len(snr), bool)
    for k in S: yes |= S[k] == "YES"
    a = np.full(len(snr), "E", dtype=object); a[yes & ok & (snr >= tau)] = "A"; a[(~yes) & ok & (snr < tau)] = "D"; return a


def pub_boot(days, assoc, a, b, n=2000, seed=7, keep=False):
    """Day bootstrap exactly as in cgd_2024.evaluate / extended_eval / kurk_extended: days with episodes, 2000, seed 7."""
    ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((a[ids] == "D").mean() - (b[ids] == "D").mean()) * 100)
    v = np.array(v); obs = ((a[assoc] == "D").mean() - (b[assoc] == "D").mean()) * 100
    r = {"diff_pp": round(float(obs), 2), "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]}
    if keep: r["_draws"] = v
    return r


def summ(a, assoc, ndays):
    return {"dismissed_assoc": int(((a == "D") & assoc).sum()), "unassoc_alerts": int(((a == "A") & ~assoc).sum()),
            "esc_per_day": round(float((a == "E").sum()) / max(ndays, 1), 2)}


def assoc_vec(P, t_on, t_off):
    """Pipeline rule vectorised: associated iff some predicted P lies in [t_on + ASSOC0, t_off + ASSOC1]."""
    P = np.sort(P[np.isfinite(P)]); i = np.searchsorted(P, t_on + ASSOC[0], side="left")
    return (i < len(P)) & (P[np.minimum(i, len(P) - 1)] <= t_off + ASSOC[1])


out = {"status": LABEL, "sources": "results/* only; frozen policies P1t 8.0 dB, P3 7.5 dB, CG theta_D 0.16 theta_A 0.60 delta 0.45, CG-D development tables"}
DATA = {n: load_any(n) for n in list(EXTRA) + list(SETS)}

# ---------------------------------------------------------------- block 1: chance association
B1 = {"label": LABEL, "rule": "episode associated iff a predicted P (catalogue p_pred, any kind) lies in [t_on - 15 s, t_off]; shifted p_pred wrapped circularly inside the set's calendar span",
      "shifts": {"days": "100 offsets, uniform 1..7 days, random sign, seed 7", "minutes": "20 offsets, uniform 10..60 min, random sign, seed 7"}, "sets": {}}
rng_master = np.random.default_rng(7)
offs_days = rng_master.uniform(1, 7, 100) * 86400 * rng_master.choice([-1, 1], 100)
offs_min = rng_master.uniform(10, 60, 20) * 60 * rng_master.choice([-1, 1], 20)
for name in list(EXTRA) + list(SETS):
    ep, av, dist, cat, ref = DATA[name]
    if name.startswith("development"):          # frozen CG in development uses theta_D 0.16 (Table B1 setting)
        pass
    P = frozen_actions(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy()
    t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy()
    pp = cat.p_pred.to_numpy(dtype=float)
    rec = assoc_vec(pp, t_on, t_off)
    t0 = pd.Timestamp(av.day.min()).timestamp(); t1 = pd.Timestamp(av.day.max()).timestamp() + 86400; span = t1 - t0
    pols = ["P1t", "P3", "CG", "CG-D"]
    excess_cg = ((P["CG"] == "D") & (P["P3"] != "D")); excess_cgd = ((P["CG-D"] == "D") & (P["P3"] != "D"))
    real = {"associated": int(assoc.sum()), "rule_reproduces_pipeline": int((rec == assoc).sum()), "of_episodes": int(len(ep)),
            **{f"dismissed_assoc_{p}": int(((P[p] == "D") & assoc).sum()) for p in pols}}
    real["CG_minus_P3_excess"] = real["dismissed_assoc_CG"] - real["dismissed_assoc_P3"]
    real["CGD_minus_P3_excess"] = real["dismissed_assoc_CG-D"] - real["dismissed_assoc_P3"]
    real["CG_only_dismissed_episodes(CG=D,P3!=D)"] = int(excess_cg.sum())
    real["CG_only_dismissed_associated"] = int((excess_cg & assoc).sum())
    res = {"real": real}
    for lab, offs in [("days", offs_days), ("minutes", offs_min)]:
        rows = []
        for o in offs:
            sp = t0 + np.mod(pp + o - t0, span); s = assoc_vec(sp, t_on, t_off)
            r = {"assoc": int(s.sum()), **{p: int(((P[p] == "D") & s).sum()) for p in pols},
                 "in_CG_only_set": int((excess_cg & s).sum()), "in_CGD_only_set": int((excess_cgd & s).sum())}
            rows.append(r)
        df = pd.DataFrame(rows); q = lambda c: [round(float(df[c].mean()), 2), round(float(df[c].quantile(0.025)), 1), round(float(df[c].quantile(0.975)), 1)]
        d = {"chance_associated_mean_lo_hi": q("assoc"),
             "chance_share_of_real_associated_pct": round(float(df.assoc.mean()) / max(assoc.sum(), 1) * 100, 2),
             **{f"chance_dismissed_{p}_mean_lo_hi": q(p) for p in pols},
             "chance_CG_minus_P3_excess_mean": round(float((df["CG"] - df["P3"]).mean()), 2),
             "chance_CGD_minus_P3_excess_mean": round(float((df["CG-D"] - df["P3"]).mean()), 2),
             "chance_rate_in_CG_only_dismissed_set_pct": round(float(df.in_CG_only_set.mean()) / max(excess_cg.sum(), 1) * 100, 2),
             "real_rate_in_CG_only_dismissed_set_pct": round(float((excess_cg & assoc).sum()) / max(excess_cg.sum(), 1) * 100, 2)}
        # chance-corrected CG-P3 point difference (approximation: subtract expected chance counts from numerator and denominator)
        num = real["CG_minus_P3_excess"] - d["chance_CG_minus_P3_excess_mean"]; den = assoc.sum() - df.assoc.mean()
        d["chance_corrected_CG_minus_P3_excess"] = round(float(num), 1)
        d["chance_corrected_CG_minus_P3_pp_approx"] = round(float(num / den * 100), 2)
        d["real_CG_minus_P3_pp"] = round(float(real["CG_minus_P3_excess"] / max(assoc.sum(), 1) * 100), 2)
        res[f"shift_{lab}"] = d
    B1["sets"][name] = res
    print("block1", name, real["CG_minus_P3_excess"], res["shift_days"]["chance_CG_minus_P3_excess_mean"], flush=True)
out["1_chance_association"] = B1

# ---------------------------------------------------------------- block 2: catalogue density
B2 = {"label": LABEL, "definition": "regional = catalogue kind 'regional' (<= 15 deg of the reference, ISC + USGS de-duplicated); per calendar day of the month in the set's availability; associated episodes per day; CG-P3 = difference of dismissed share of associated episodes in that month", "sets": {}}
for name in list(EXTRA) + list(SETS):
    ep, av, dist, cat, ref = DATA[name]
    P = frozen_actions(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy()
    cat = cat.copy(); cat["day"] = pd.to_datetime(cat.time, unit="s").dt.strftime("%Y-%m-%d")
    days = set(av.day); cat = cat[cat.day.isin(days)]; cat["month"] = cat.day.str[:7]
    ep_m = ep.day.str[:7].to_numpy(); avm = av.day.str[:7]
    rows = {}
    for m in sorted(avm.unique()):
        nd = int((avm == m).sum()); msk = ep_m == m; am = assoc & msk
        cgd = ((P["CG"] == "D") & am).sum(); p3d = ((P["P3"] == "D") & am).sum()
        rows[m] = {"days": nd, "regional_events_per_day": round(float(((cat.month == m) & (cat.kind == "regional")).sum()) / nd, 2),
                   "tele_events_per_day": round(float(((cat.month == m) & (cat.kind == "tele")).sum()) / nd, 2),
                   "episodes_per_day": round(float(msk.sum()) / nd, 2), "associated_episodes_per_day": round(float(am.sum()) / nd, 2),
                   "associated_share_pct": round(float(am.sum()) / max(msk.sum(), 1) * 100, 2),
                   "CG_minus_P3_pp": round(float((cgd - p3d) / max(am.sum(), 1) * 100), 2) if am.sum() else None,
                   "CG_minus_P3_excess": int(cgd - p3d)}
    rpd = [v["regional_events_per_day"] for v in rows.values()]
    B2["sets"][name] = {"months": rows, "regional_per_day_median": round(float(np.median(rpd)), 2),
                        "regional_per_day_min": round(float(min(rpd)), 2), "regional_per_day_max": round(float(max(rpd)), 2)}
B2["truncated_before_2026-03"] = {"note": "sensitivity: extended sets without 2026-03..2026-06, the months whose regional catalogue density fell to 4-9 per day",
                                  "sets": {}}
for name in ["extended IU.MAKZ", "extended II.KURK"]:
    ep, av, dist, cat, ref = DATA[name]; P = frozen_actions(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy()
    keep = (ep.day < "2026-03-01").to_numpy(); e2 = ep[keep]; a2 = assoc[keep]; nd = int((av.day < "2026-03-01").sum())
    B2["truncated_before_2026-03"]["sets"][name] = {"calendar_days": nd, "associated": int(a2.sum()),
        **{p: summ(np.asarray(P[p])[keep], a2, nd) for p in ["P3", "CG", "CG-D"]},
        "CG_minus_P3": pub_boot(e2.day.to_numpy(), a2, np.asarray(P["CG"])[keep], np.asarray(P["P3"])[keep])}
out["2_catalogue_density"] = B2

# ---------------------------------------------------------------- block 3: G.WUS availability and ablation
B3 = {"label": LABEL, "note": "role WUS = G.WUS on these sets; on the KZ set it is KZ.PDGK and on the AK set an AK station, so those are not ablated",
      "sets": {}}
for name in GWUS_SETS:
    ep, av, dist, cat, ref = DATA[name]
    assoc = (ep.assoc_event >= 0).to_numpy(); nd = len(av)
    NB = sorted([k[2:] for k in ep.columns if k.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15]))
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy(); days = ep.day.to_numpy()
    w = av.WUS_valid_share.to_numpy(); sw = S["WUS"]
    avail = {"calendar_days": int(nd), "mean_daily_valid_share": round(float(w.mean()), 3), "days_valid_ge_90pct": int((w >= 0.9).sum()),
             "days_valid_lt_10pct": int((w < 0.1).sum()), "episodes": int(len(ep)),
             "episodes_WUS_valid": int(np.isin(sw, ["YES", "NO"]).sum()), "WUS_YES": int((sw == "YES").sum()), "WUS_NO": int((sw == "NO").sum()),
             "associated_WUS_YES": int(((sw == "YES") & assoc).sum()), "associated_WUS_NO": int(((sw == "NO") & assoc).sum()),
             "WUS_weight_by_rank": W["WUS"]}
    cg = cg_custom(S, W, snr, ok); p3 = p3_custom(S, snr, ok)
    S0 = dict(S); S0["WUS"] = np.full(len(ep), "MISSING", dtype=object)
    cg0 = cg_custom(S0, W, snr, ok); p30 = p3_custom(S0, snr, ok)
    abl = {"CG": summ(cg, assoc, nd), "CG_WUS_missing": summ(cg0, assoc, nd), "P3": summ(p3, assoc, nd), "P3_WUS_missing": summ(p30, assoc, nd)}
    if not name.startswith("development"):
        abl["CG_minus_P3"] = pub_boot(days, assoc, cg, p3)
        abl["CG_WUS_missing_minus_P3_frozen"] = pub_boot(days, assoc, cg0, p3)
        abl["CG_WUS_missing_minus_P3_WUS_missing"] = pub_boot(days, assoc, cg0, p30)
    else:
        abl["note"] = "development: CG at the fixed theta_D 0.16 of Table B1 (the main development table uses fold thresholds 0.16-0.21)"
    exc = (cg == "D") & (p3 != "D") & assoc
    abl["CG_excess_dismissals_with_WUS_NO"] = int((exc & (sw == "NO")).sum()); abl["CG_excess_dismissals_total"] = int(exc.sum())
    B3["sets"][name] = {"availability": avail, "ablation": abl}
    print("block3", name, abl["CG"]["dismissed_assoc"], abl["CG_WUS_missing"]["dismissed_assoc"], flush=True)
out["3_GWUS"] = B3

# ---------------------------------------------------------------- block 4: II.KURK reference, MAKZ + MK31 as one site
B4 = {"label": LABEL, "merge": "state YES if either YES; NO if either NO and none YES; MISSING if both MISSING",
      "variants": {"a": "merged site 0.25, G.WUS 0.20 (weights re-assigned by distance rank, two neighbours)",
                   "b": "merged site 0.25, G.WUS 0.15 (G.WUS keeps its original weight)"}, "sets": {}}
for name in ["extended II.KURK", "2024 II.KURK"]:
    ep, av, dist, cat, ref = DATA[name]
    assoc = (ep.assoc_event >= 0).to_numpy(); nd = len(av); days = ep.day.to_numpy()
    NB = sorted([k[2:] for k in ep.columns if k.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    a_, b_ = S["MAKZ"], S["MK31"]
    m = np.where((a_ == "YES") | (b_ == "YES"), "YES", np.where((a_ == "NO") | (b_ == "NO"), "NO", "MISSING")).astype(object)
    W0 = dict(zip(NB, [0.25, 0.20, 0.15]))
    cg = cg_custom(S, W0, snr, ok); p3 = p3_custom(S, snr, ok)
    Sm = {"SITE": m, "WUS": S["WUS"]}
    cga = cg_custom(Sm, {"SITE": 0.25, "WUS": 0.20}, snr, ok); cgb = cg_custom(Sm, {"SITE": 0.25, "WUS": 0.15}, snr, ok)
    exc = (cg == "D") & (p3 != "D") & assoc
    B4["sets"][name] = {"neighbours_km": {k: dist.get(k) for k in NB},
                        "same_state_MAKZ_MK31_pct_all": round(float((a_ == b_).mean() * 100), 1),
                        "same_state_MAKZ_MK31_pct_associated": round(float((a_[assoc] == b_[assoc]).mean() * 100), 1),
                        "CG_excess_dismissals": int(exc.sum()), "of_which_NO_from_both_MAKZ_and_MK31": int((exc & (a_ == "NO") & (b_ == "NO")).sum()),
                        "P3": summ(p3, assoc, nd), "CG_frozen": summ(cg, assoc, nd),
                        "CG_merged_a": summ(cga, assoc, nd), "CG_merged_b": summ(cgb, assoc, nd),
                        "CG_frozen_minus_P3": pub_boot(days, assoc, cg, p3),
                        "CG_merged_a_minus_P3": pub_boot(days, assoc, cga, p3),
                        "CG_merged_b_minus_P3": pub_boot(days, assoc, cgb, p3),
                        "note": "P3 is unchanged by the merge (it only asks whether any neighbour said YES); CG-D not computed: no development detectability table exists for a merged site"}
    print("block4", name, B4["sets"][name]["CG_merged_a_minus_P3"], flush=True)
out["4_KURK_merged_site"] = B4

# ---------------------------------------------------------------- block 5: Alaska, AK.L22K missing per episode
ep, av, dist, cat, ref = DATA["AK network"]
P = frozen_actions(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy(); l22 = ep.n_MK31.astype(str).to_numpy()
mk = av.set_index("day")["MK31_valid_share"]; part = ep.day.map(lambda x: 0.1 <= mk.get(x, 0) < 0.9).to_numpy()
sub = assoc & (l22 == "MISSING")
B5 = {"label": LABEL, "station": "AK.L22K (role MK31, 29.4 km)", "associated": int(assoc.sum()),
      "associated_L22K_missing": int(sub.sum()), "associated_L22K_missing_on_partial_days": int((sub & part).sum()),
      "partial_days(10-90% valid)": int(((av.MK31_valid_share >= 0.1) & (av.MK31_valid_share < 0.9)).sum()), "calendar_days": int(len(av)),
      "dismissed_in_subset": {p: int(((P[p] == "D") & sub).sum()) for p in ["P1t", "P3", "CG", "CG-D", "CG(c=0.5)"]},
      "escalated_in_subset": {p: int(((P[p] == "E") & sub).sum()) for p in ["P3", "CG", "CG-D"]},
      "dismissed_associated_L22K_valid": {p: int(((P[p] == "D") & assoc & (l22 != "MISSING")).sum()) for p in ["P3", "CG", "CG-D"]},
      "all_associated_dismissed": {p: int(((P[p] == "D") & assoc).sum()) for p in ["P3", "CG", "CG-D"]}}
B5["share_of_CG_dismissals_in_L22K_missing_subset_pct"] = round(B5["dismissed_in_subset"]["CG"] / max(B5["all_associated_dismissed"]["CG"], 1) * 100, 1)
out["5_AK_L22K_missing"] = B5

# ---------------------------------------------------------------- block 6: Alaska in the out-of-sample comparison
osrc = open(os.path.join(root, "analysis", "oos_operating_points.py"), encoding="utf-8").read()
ons = {"__file__": os.path.join(root, "analysis", "oos_operating_points.py")}
exec(compile(osrc[:osrc.index("out = {\"status\"")], "oos_selection", "exec"), ons)     # development selection, unchanged
sel = ons["sel"]; ep6, dist6 = ons["load_dirs"](SETS["AK network"][0]); F = ons["features"](ep6, dist6, "MAKZ")
res6 = {"constraint": {}, "cost": {}}
for kind in ("constraint", "cost"):
    for key, v in sel[kind].items():
        x = ons["metrics"](F, ons["act"](F, key.split("|")[1], tuple(v["params"])))
        if kind == "cost":
            rm, re_ = [float(t[2:]) for t in key.split("|")[0].split("_")]
            x["cost_per_ep"] = (rm * x["dismissed_assoc"] + x["unassoc_alerts"] + re_ * x["escalations"]) / x["episodes"]
        else:
            m_, e_ = [float(t[1:]) for t in key.split("|")[0].split("_")]
            x["constraints_held"] = bool(x["dismissed_assoc_share"] <= m_ and x["escalated_share"] <= e_)
        res6[kind][key] = x
cost_rank = {}
for ck in sorted({k.split("|")[0] for k in res6["cost"]}):
    c = sorted([(k.split("|")[1], v["cost_per_ep"]) for k, v in res6["cost"].items() if k.startswith(ck + "|")], key=lambda t: t[1])
    best_cg = min(v for f, v in c if f.startswith("CG")); best_p3 = min(v for f, v in c if f in ("P3", "P2"))
    cost_rank[ck] = {"lowest": c[0][0], "order": [f"{f} {v:.4f}" for f, v in c], "best_CG_vs_best_P3_pct": round((best_cg / best_p3 - 1) * 100, 2)}
held = {}
for ck in sorted({k.split("|")[0] for k in res6["constraint"]}):
    held[ck] = sorted([k.split("|")[1] for k, v in res6["constraint"].items() if k.startswith(ck + "|") and v["constraints_held"]])
fam_low = pd.Series([v["lowest"] for v in cost_rank.values()]).value_counts().to_dict()
out["6_AK_out_of_sample"] = {"label": LABEL, "method": "operating points selected on IU.MAKZ development by analysis/oos_operating_points.py (selection code executed unchanged), applied to the AK episodes; CG-D uses the IU.MAKZ development table by role, as in the AK plan",
                             "cost_lowest_family_counts_of_9": {k: int(v) for k, v in fam_low.items()}, "cost": cost_rank,
                             "constraints_met_out_of_sample": held, "raw": res6}

# ---------------------------------------------------------------- block 7: multiplicity (Holm)
fam = [("E3", "extended IU.MAKZ", "CG", "results/extended/extended_eval.json", ["E3"]),
       ("K3", "extended II.KURK", "CG", "results/kurk_ext/kurk_ext_eval.json", ["K3"]),
       ("D1 IU.MAKZ", "2024 IU.MAKZ", "CG-D", "results/y2024/cgd_2024_eval.json", ["MAKZ", "D1"]),
       ("D1 II.KURK", "2024 II.KURK", "CG-D", "results/y2024/cgd_2024_eval.json", ["KURK", "D1"]),
       ("N3", "KZ network", "CG", "results/kz/kz_eval.json", ["N3_CG_noninferiority"]),
       ("N5", "KZ network", "CG-D", "results/kz/kz_eval.json", ["N5_CGD_noninferiority"]),
       ("R3", "AK network", "CG", "results/ak/ak_eval.json", ["R3_CG_noninferiority"]),
       ("R5", "AK network", "CG-D", "results/ak/ak_eval.json", ["R5_CGD_noninferiority"]),
       ("R6", "AK network", "CG(c=0.5)", "results/ak/ak_eval.json", ["R6_constant_c05_noninferiority"])]
rows = []
for lab, sname, pol, jf, path in fam:
    ep, av, dist, cat, ref = DATA[sname]; P = frozen_actions(ep, dist, ref); assoc = (ep.assoc_event >= 0).to_numpy()
    b = pub_boot(ep.day.to_numpy(), assoc, P[pol], P["P3"], keep=True); v = b.pop("_draws")
    pub = json.load(open(os.path.join(root, jf)))
    for k in path: pub = pub[k]
    k_ = int((v >= MARGIN).sum())
    rows.append({"test": lab, "contrast": f"{pol} - P3", "published": {"diff_pp": pub["diff_pp"], "ci95_pp": pub["ci95_pp"]},
                 "recomputed": b, "reproduced": b["ci95_pp"] == pub["ci95_pp"] and b["diff_pp"] == pub["diff_pp"],
                 "draws": int(len(v)), "draws_at_or_above_margin": k_, "p_one_sided": (k_ + 1) / (len(v) + 1)})
order = sorted(range(len(rows)), key=lambda i: rows[i]["p_one_sided"]); m_ = len(rows); stop = False
for rank, i in enumerate(order):
    adj = min(1.0, (m_ - rank) * rows[i]["p_one_sided"]); rows[i]["holm_adjusted_p"] = adj
for rank, i in enumerate(order):                     # monotone Holm
    rows[i]["holm_adjusted_p"] = round(max(rows[j]["holm_adjusted_p"] for j in order[:rank + 1]), 5)
for r in rows:
    r["p_one_sided"] = round(r["p_one_sided"], 5)
    r["unadjusted_noninferior_at_0.025"] = r["p_one_sided"] <= 0.025
    r["holm_noninferior_at_0.025"] = r["holm_adjusted_p"] <= 0.025
out["7_multiplicity"] = {"label": LABEL, "family": "the nine pre-specified margin contrasts (E3, K3, D1 x2, N3, N5, R3, R5, R6)",
                         "test": "H0: difference >= 3 pp; p = (draws >= 3 + 1)/(draws + 1) from the published day bootstrap (days with episodes, 2000, seed 7) recomputed here; one-sided alpha 0.025, which is the 95 % two-sided interval rule of the plans; Holm step-down over the nine",
                         "rows": rows}

# ---------------------------------------------------------------- block 8: detector miss rate, Pn
dc = json.load(open(os.path.join(R, "stage1_v3", "detector_coverage.json")))
miss = {k: {"events": v["events"], "with_episode": v["with_episode"], "miss_rate_pct": round((1 - v["share"]) * 100, 1)}
        for k, v in [("regional_all", dc["regional_all"])] + [(f"magnitude {a}", b) for a, b in dc["regional_by_magnitude"].items()]
        + [(f"distance {a}", b) for a, b in dc["regional_by_distance"].items()] + [("teleseismic", dc["teleseismic"])]}
out["8_detector_and_Pn"] = {"label": LABEL, "source": "results/stage1_v3/detector_coverage.json (development, IU.MAKZ, 85 days)",
                            "detector_miss_rate": miss,
                            "Pn_travel_time_check": "not derivable from detector_coverage.json: it holds counts only, no arrival-time residuals by distance or phase. Two facts from the code (not data): catalogue association uses the TauP iasp91 first arrival (pipeline/stage1_pipeline.py, min over arrivals), which is Pn beyond the crossover distance, not 5.5 km/s; the 5.5 km/s figure only sets the neighbour coincidence half-width d/5.5 + 5 s, and since the arrival-time difference between two stations for a phase of apparent velocity v is at most d/v, a Pn moveout (v ~ 8 km/s) fits inside a window built for 5.5 km/s (the window is wider than Pn needs, which admits more chance coincidences rather than missing Pn confirmations)."}

os.makedirs(os.path.join(R, "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(R, "posthoc", "cold_panel_posthoc.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(out["7_multiplicity"]["rows"], indent=0)[:3000])
