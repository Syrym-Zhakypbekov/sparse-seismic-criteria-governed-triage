"""PLAN_PAPER1_HARMONISED_2026-11-09.md (post hoc, plan pushed before computing): one threshold procedure, P3-2t as the
primary comparator of Paper 1, and Holm over the Paper 1 primary family (E1, E3, K3, D1 x2).
Reads the frozen episode ledgers read-only. Output: results/paper1/harmonised.json."""
import os, json, glob, re
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(ROOT, "results")
TAB = json.load(open(os.path.join(R, "prereg", "detectability_tables_dev.json")))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
W_RANK = [0.25, 0.20, 0.15]; W_SNR = 0.40; DELTA, THETA_A, THETA_D = 0.45, 0.60, 0.16
NB, SEED, MARGIN = 2000, 7, 3.0


def load(dirs, dist_default=None):
    fr, av, dist = [], [], {}
    for d in dirs:
        e = pd.read_csv(os.path.join(d, "episodes.csv")); e["day"] = e.t_on_utc.str[:10]; fr.append(e)
        a = pd.read_csv(os.path.join(d, "availability.csv")); av.append(a)
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    ep = pd.concat(fr, ignore_index=True); av = pd.concat(av, ignore_index=True).drop_duplicates("day")
    if dist_default: dist = {**dist_default, **dist}
    return ep, av, dist


def actions(ep, av, dist, table_ref, p3_2t):
    NBR = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NBR, W_RANK))
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NBR}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NBR: yes |= S[k] == "YES"; no |= S[k] == "NO"
    act = {"P1": np.where(yes, "A", "D").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "A", "D").astype(object)}

    def two(td, ta):
        a = np.full(len(ep), "E", dtype=object); a[yes & ok & (snr >= ta)] = "A"; a[(~yes) & ok & (snr < td)] = "D"; return a
    act["P3"] = two(7.5, 7.5)
    if p3_2t: act["P3-2t"] = two(*p3_2t)
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()

    def cg(qno, td=THETA_D):
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NBR:
            q = np.isin(S[k], ["YES", "NO"]).astype(float); q = np.where(S[k] == "NO", qno(k), q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W_SNR * np.clip(snr / 30, 0, 1) * ok; den += W_SNR * ok
        dd = den >= DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "E", dtype=object); a[dd & (D >= THETA_A)] = "A"; a[dd & (D <= td)] = "D"; return a, D
    act["CG"], Dcg = cg(lambda k: 1.0)
    act["CG c=0.5"], _ = cg(lambda k: 0.5)
    if table_ref:
        act["CG-D"], _ = cg(lambda k: np.array([TAB[table_ref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b]))
    mk = av.set_index("day")["MK31_valid_share"]
    outage = ep.day.map(lambda x: mk.get(x, 0) < 0.1).to_numpy()
    return act, assoc, ep.day.to_numpy(), outage, yes, snr, ok, Dcg


def dayboot(days, assoc, a, b, sel=None, n=NB, seed=SEED, ndays=None):
    """paired day bootstrap (days with episodes). dism: difference in dismissed share of `sel` (default associated), pp.
    Also unassociated alerts per day and escalations per day differences (per calendar day: scaled by n_ep_days/ndays)."""
    sel = assoc if sel is None else sel
    ud, inv = np.unique(days, return_inverse=True)
    c = lambda w: np.bincount(inv, weights=w.astype(float), minlength=len(ud))
    m = {"n": c(sel), "Da": c((a == "D") & sel), "Db": c((b == "D") & sel), "Ua": c((a == "A") & ~assoc), "Ub": c((b == "A") & ~assoc),
         "Ea": c(a == "E"), "Eb": c(b == "E")}
    scale = len(ud) / ndays if ndays else 1.0

    def st(ix):
        n_ = m["n"][ix].sum()
        return ((m["Da"][ix].sum() - m["Db"][ix].sum()) / n_ * 100 if n_ else np.nan,
                (m["Ua"][ix].sum() - m["Ub"][ix].sum()) / len(ix) * scale, (m["Ea"][ix].sum() - m["Eb"][ix].sum()) / len(ix) * scale)
    rng = np.random.default_rng(seed); V = np.array([st(rng.integers(0, len(ud), len(ud))) for _ in range(n)]); o = st(np.arange(len(ud)))
    q = lambda i: [round(float(np.nanpercentile(V[:, i], 2.5)), 2), round(float(np.nanpercentile(V[:, i], 97.5)), 2)]
    vd = V[:, 0][np.isfinite(V[:, 0])]
    return {"dism_pp": round(float(o[0]), 2), "dism_ci": q(0), "p_ge_margin": round(float(((vd >= MARGIN).sum() + 1) / (len(vd) + 1)), 5),
            "ua_per_day": round(float(o[1]), 2), "ua_ci": q(1), "esc_per_day": round(float(o[2]), 2), "esc_ci": q(2)}


def published_boot(days, assoc, a, b, n=NB, seed=SEED):
    """identical to analysis/v2_networks.day_boot (published): returns draws too."""
    ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((a[ids] == "D").mean() - (b[ids] == "D").mean()) * 100)
    v = np.array(v); obs = ((a[assoc] == "D").mean() - (b[assoc] == "D").mean()) * 100
    return {"diff_pp": round(float(obs), 2), "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
            "p_one_sided": round(float(((v >= MARGIN).sum() + 1) / (len(v) + 1)), 5)}


# ---------- development: one procedure and t_A ----------
DIST_DEV = {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}
dev, dav, ddist = load([os.path.join(R, "stage1_v3")], DIST_DEV)
act0, assoc0, days0, out0, yes0, snr0, ok0, D0 = actions(dev, dav, ddist, "MAKZ", None)
GRID = np.round(np.arange(0, 30.01, 0.5), 2); TH = np.round(np.arange(0, 0.5901, 0.01), 2)


def rule4(fn, grid):
    best = None
    for t in grid:
        a = fn(t)
        if ((a != "D") & assoc0).sum() / assoc0.sum() >= 0.95: best = float(t)
    return best


def snr_rule(name, t):
    a = np.full(len(dev), "E", dtype=object)
    if name == "P1t": a[:] = "D"; a[yes0 | (ok0 & (snr0 >= t))] = "A"; return a
    a[yes0 & ok0 & (snr0 >= t)] = "A"; d = (~yes0) & ok0 & (snr0 < t)
    if name == "P2":
        no0 = np.zeros(len(dev), bool)
        for k in ("MK31", "KURK", "WUS"): no0 |= dev[f"n_{k}"].astype(str).to_numpy() == "NO"
        d &= no0
    a[d] = "D"; return a


def cg_rule(td):
    a = np.full(len(dev), "E", dtype=object); f = ~np.isnan(D0); a[f & (D0 >= THETA_A)] = "A"; a[f & (D0 <= td)] = "D"; return a


thr = {n: rule4(lambda t, n=n: snr_rule(n, t), GRID) for n in ("P1t", "P2", "P3")}
thr["CG_theta_D"] = rule4(cg_rule, TH)
assert thr == {"P1t": 8.0, "P2": 10.5, "P3": 8.0, "CG_theta_D": 0.16}, thr
tD = thr["P3"]; esc_cg = int((cg_rule(THETA_D) == "E").sum()); cand = []
for tA in np.round(np.arange(tD, 30.01, 0.5), 2):
    a = np.full(len(dev), "E", dtype=object); a[yes0 & ok0 & (snr0 >= tA)] = "A"; a[(~yes0) & ok0 & (snr0 < tD)] = "D"
    cand.append((abs(int((a == "E").sum()) - esc_cg), float(tA), int((a == "E").sum()), int(((a == "A") & ~assoc0).sum())))
cand.sort(key=lambda r: (r[0], r[1])); tA = cand[0][1]
res = {"plan": "PLAN_PAPER1_HARMONISED_2026-11-09.md", "thresholds_one_procedure": thr,
       "P3_2t": {"tD": tD, "tA": tA, "dev_escalations": cand[0][2], "dev_CG_escalations": esc_cg, "dev_unassoc_alerts": cand[0][3],
                 "dev_CG_unassoc_alerts": int(((cg_rule(THETA_D) == "A") & ~assoc0).sum())}}
print("thresholds", thr, "P3-2t", res["P3_2t"])

# ---------- test sets ----------
E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
SETS = {
    "extended IU.MAKZ": ([rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")], "MAKZ"),
    "extended II.KURK": (sorted(glob.glob(os.path.join(R, "kurk_ext", "outK_*"))), "KURK"),
    "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
    "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
    "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ"),
    "AK network": (sorted(glob.glob(os.path.join(R, "ak", "outAK_20*"))), "MAKZ")}
EXPECT = {  # published frozen counts: (dismissed assoc, unassoc alerts) for P3 7.5, CG, CG-D
    "extended IU.MAKZ": {"P3": (38, 6350), "CG": (98, 2870), "CG-D": (38, 3390)},
    "extended II.KURK": {"P3": (49, 7444), "CG": (228, 3511)},
    "2024 IU.MAKZ": {"P3": (11, 5619), "CG": (34, 1765), "CG-D": (17, 2507)},
    "2024 II.KURK": {"P3": (13, 5235), "CG": (101, 1799), "CG-D": (30, 2015)},
    "KZ network": {"P3": (17, 5541), "CG": (102, 2442), "CG-D": (36, 3037)},
    "AK network": {"P3": (3, 3671), "CG": (33, 520), "CG-D": (5, 768), "CG c=0.5": (6, 1160)}}
res["sets"] = {}; KEEP = {}
for name, (dirs, tref) in SETS.items():
    ep, av, dist = load(dirs)
    act, assoc, days, outage, *_ = actions(ep, av, dist, tref, (tD, tA))
    ndays = int(av.day.nunique()); nout = int((av.MK31_valid_share < 0.1).sum())
    for p, (da, ua) in EXPECT[name].items():
        got = (int(((act[p] == "D") & assoc).sum()), int(((act[p] == "A") & ~assoc).sum()))
        assert got == (da, ua), (name, p, got, (da, ua))
    lv = {p: {"dismissed_assoc": int(((a == "D") & assoc).sum()), "dismissed_assoc_outage": int(((a == "D") & assoc & outage).sum()),
              "unassoc_alerts": int(((a == "A") & ~assoc).sum()), "escalations": int((a == "E").sum()),
              "esc_per_day": round(float((a == "E").sum()) / ndays, 2)} for p, a in act.items()}
    con = {f"{x} - P3-2t": dayboot(days, assoc, act[x], act["P3-2t"], ndays=ndays) for x in ("CG", "CG c=0.5", "CG-D") if x in act}
    con["P3 7.5 - P3-2t"] = dayboot(days, assoc, act["P3"], act["P3-2t"], ndays=ndays)
    res["sets"][name] = {"calendar_days": ndays, "outage_days": nout, "episodes": int(len(ep)), "assoc": int(assoc.sum()),
                         "assoc_outage": int((assoc & outage).sum()), "levels": lv, "contrasts_vs_P3_2t": con}
    KEEP[name] = (act, assoc, days, outage)
    print(name, {p: (v["dismissed_assoc"], v["unassoc_alerts"], v["esc_per_day"]) for p, v in lv.items()})

# AK analyst labels (G1, G3 analogues vs P3-2t)
g = pd.read_csv(os.path.join(R, "ground_truth", "episodes_labelled.csv.gz")); g["day"] = g.t_on_utc.str[:10]
gav = pd.concat([pd.read_csv(os.path.join(d, "availability.csv")) for d in SETS["AK network"][0]]).drop_duplicates("day")
ga, gassoc, gdays, _, *_ = actions(g, gav, {"MK31": 29.4, "KURK": 537.6, "WUS": 642.7}, "MAKZ", (tD, tA))
conf = (g["gt"] == "CONFIRMED").to_numpy(); rej = (g["gt"] == "REJECTED").to_numpy()
assert int(((ga["CG"] == "D") & conf).sum()) == 169 and int(((ga["P3"] == "D") & conf).sum()) == 21
lab = {"n_confirmed": int(conf.sum()), "n_rejected": int(rej.sum())}
for p, a in ga.items():
    lab[p] = {"dismissed_confirmed": int(((a == "D") & conf).sum()), "alerted_rejected": int(((a == "A") & rej).sum()),
              "escalated_confirmed": int(((a == "E") & conf).sum())}
lab["contrasts_confirmed_dismissed_vs_P3_2t"] = {x: dayboot(gdays, conf, ga[x], ga["P3-2t"], sel=conf) for x in ("CG", "CG c=0.5", "CG-D")}


def alert_share_boot(days, sel, a, b, n=NB, seed=SEED):
    ud, inv = np.unique(days, return_inverse=True); c = lambda w: np.bincount(inv, weights=w.astype(float), minlength=len(ud))
    m = (c(sel), c((a == "A") & sel), c((b == "A") & sel)); rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ix = rng.integers(0, len(ud), len(ud)); s = m[0][ix].sum()
        if s: v.append((m[1][ix].sum() - m[2][ix].sum()) / s * 100)
    o = (m[1].sum() - m[2].sum()) / m[0].sum() * 100
    return {"alert_share_pp": round(float(o), 2), "ci": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]}


lab["contrasts_rejected_alerted_vs_P3_2t"] = {x: alert_share_boot(gdays, rej, ga[x], ga["P3-2t"]) for x in ("CG", "CG c=0.5", "CG-D")}
res["AK_analyst_labels"] = lab

# ---------- primary family (registered comparators) + Holm ----------
fam = {}
a, assoc, days, outage = KEEP["extended IU.MAKZ"]
fam["E3"] = published_boot(days, assoc, a["CG"], a["P3"])
# E1: outage days, CG - P1 dismissed share of associated, H0: >= 0
sel = assoc & outage; ud = np.array(sorted(set(days[outage]))); idx = {d: np.flatnonzero((days == d) & sel) for d in ud}
rng = np.random.default_rng(SEED); v = []
for _ in range(NB):
    ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
    if len(ids): v.append(((a["CG"][ids] == "D").mean() - (a["P1"][ids] == "D").mean()) * 100)
v = np.array(v)
fam["E1"] = {"diff_pp": round(float(((a["CG"][sel] == "D").mean() - (a["P1"][sel] == "D").mean()) * 100), 2),
             "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
             "p_one_sided": round(float(((v >= 0).sum() + 1) / (len(v) + 1)), 5), "counts": [int(((a["CG"] == "D") & sel).sum()), int(((a["P1"] == "D") & sel).sum()), int(sel.sum())]}
a, assoc, days, _ = KEEP["extended II.KURK"]; fam["K3"] = published_boot(days, assoc, a["CG"], a["P3"])
a, assoc, days, _ = KEEP["2024 IU.MAKZ"]; fam["D1 IU.MAKZ"] = published_boot(days, assoc, a["CG-D"], a["P3"])
a, assoc, days, _ = KEEP["2024 II.KURK"]; fam["D1 II.KURK"] = published_boot(days, assoc, a["CG-D"], a["P3"])
ks = sorted(fam, key=lambda k: fam[k]["p_one_sided"]); run = 0.0
for i, k in enumerate(ks):
    run = max(run, min(1.0, (len(ks) - i) * fam[k]["p_one_sided"])); fam[k]["p_holm"] = round(run, 5)
    fam[k]["met_after_holm"] = bool(fam[k]["p_holm"] <= 0.025)
res["primary_family_holm"] = fam
print(json.dumps(fam, indent=0))
os.makedirs(os.path.join(R, "paper1"), exist_ok=True)
json.dump(res, open(os.path.join(R, "paper1", "harmonised.json"), "w", encoding="utf-8"), indent=1)
print("written results/paper1/harmonised.json")
