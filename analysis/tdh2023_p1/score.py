"""PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md sections 6-8: scoring of the time-disjoint 2023 test (IU.MAKZ and AK networks).
Policies: analysis/paper1_harmonised.actions (copied verbatim below; that module runs its whole analysis on import).
Labels: analysis/v2_reviewed_bulletin (parse_isc, parse_usgs, label_rows); association: analysis/v2_networks.assoc_vec; per chunk,
because the pipeline associates each chunk with its own catalogue. Bootstrap: paper1_harmonised.published_boot / dayboot (copied).
Outputs: results/tdh2023_p1/tdh2023_p1_eval.json, chronology.json, RESULTS_tdh2023.md (every number written by this code)."""
import os, sys, re, glob, json, subprocess, importlib.util, datetime as dt
import numpy as np, pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(os.path.dirname(here)); R = os.path.join(root, "results")
OUT = os.path.join(R, "tdh2023_p1"); RUNS = os.path.join(OUT, "runs"); LAB_DIR = os.path.join(OUT, "labels")
sys.path.insert(0, os.path.join(root, "analysis"))
spec = importlib.util.spec_from_file_location("vr", os.path.join(root, "analysis", "v2_reviewed_bulletin.py"))
vr = importlib.util.module_from_spec(spec); sys.modules["vr"] = vr; spec.loader.exec_module(vr); v2 = vr.v2
CFG = json.load(open(os.path.join(OUT, "networks_tdh2023_p1.json"), encoding="utf-8"))
TAB = json.load(open(os.path.join(R, "prereg", "detectability_tables_dev.json")))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
W_RANK = [0.25, 0.20, 0.15]; W_SNR = 0.40; DELTA, THETA_A, THETA_D = 0.45, 0.60, 0.16
NB, SEED, MARGIN, ALPHA = 2000, 7, 3.0, 0.025
P3_2T = (8.0, 10.0); XS = ("CG", "CG c=0.5", "CG-D")
YEAR_S = 365 * 86400.0; Y0 = pd.Timestamp("2023-01-01", tz="UTC").timestamp(); Y1 = pd.Timestamp("2024-01-01", tz="UTC").timestamp()


# ---------------- copied verbatim from analysis/paper1_harmonised.py ----------------
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
    ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((a[ids] == "D").mean() - (b[ids] == "D").mean()) * 100)
    v = np.array(v); obs = ((a[assoc] == "D").mean() - (b[assoc] == "D").mean()) * 100
    return {"diff_pp": round(float(obs), 2), "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
            "p_one_sided": round(float(((v >= MARGIN).sum() + 1) / (len(v) + 1)), 5)}
# ---------------- end of copy ----------------


def corrected_boot(days, a_rev, p, a, b, n=NB, seed=SEED):
    """chance-corrected difference 100 * sum (Da - Db)(a - p) / sum (a - p), paired bootstrap over calendar days with episodes."""
    ud, inv = np.unique(days, return_inverse=True); w = a_rev.astype(float) - p
    c = lambda x: np.bincount(inv, weights=x, minlength=len(ud))
    num = c(((a == "D").astype(float) - (b == "D").astype(float)) * w); den = c(w)
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ix = rng.integers(0, len(ud), len(ud)); d = den[ix].sum()
        if d > 0: v.append(num[ix].sum() / d * 100)
    v = np.array(v); o = num.sum() / den.sum() * 100
    hi = float(np.percentile(v, 97.5))
    return {"diff_pp": round(float(o), 2), "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(hi, 2)],
            "p_one_sided": round(float(((v >= MARGIN).sum() + 1) / (len(v) + 1)), 5), "met_upper_le_3": bool(hi <= MARGIN)}


def outage_boot(days, sel, a, b, n=NB, seed=SEED):
    ud = np.array(sorted(set(days[sel]))); idx = {d: np.flatnonzero((days == d) & sel) for d in ud}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
        if len(ids): v.append(((a[ids] == "D").mean() - (b[ids] == "D").mean()) * 100)
    v = np.array(v)
    return {"diff_pp": round(float(((a[sel] == "D").mean() - (b[sel] == "D").mean()) * 100), 2),
            "ci95_pp": [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)],
            "p_one_sided": round(float(((v >= 0).sum() + 1) / (len(v) + 1)), 5), "outage_days_with_episodes": int(len(ud)),
            "counts_CG_P1_n": [int(((a == "D") & sel).sum()), int(((b == "D") & sel).sum()), int(sel.sum())]}


def arr(rows):
    a = np.array(rows, float) if rows else np.zeros((0, 4)); return a[np.argsort(a[:, 0])] if len(a) else a


def load_net(net):
    tele = arr([r for f in glob.glob(os.path.join(LAB_DIR, "TELE_ALL_*.json")) for r in vr.parse_usgs(f)])
    isc = arr([r for f in glob.glob(os.path.join(LAB_DIR, f"ISC_{net}_*.xml")) for r in vr.parse_isc(f)])
    usg = arr([r for f in glob.glob(os.path.join(LAB_DIR, f"USGS_{net}_*.json")) for r in vr.parse_usgs(f)])
    eps, avs, chunks, dist = [], [], {}, {}
    rev_p = []; cat_rows = {"all": 0, "reviewed": 0, "matched": 0, "ISC": [0, 0], "USGS": [0, 0]}; agree = []
    fetch_fail = 0
    for t0 in CFG["chunks"][:-1]:
        d = os.path.join(RUNS, net, f"out_{t0}")
        if not os.path.exists(os.path.join(d, "episodes.csv")):
            lg = os.path.join(d, "run.log"); ex = [l for l in open(lg, encoding="utf-8", errors="ignore").read().splitlines() if l.startswith("Exception")] if os.path.exists(lg) else []
            chunks[t0] = "not completed (data): " + (ex[-1][:160] if ex else "no episodes.csv"); continue
        chunks[t0] = "completed"
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); cat = pd.read_csv(os.path.join(d, "catalog.csv")).reset_index(drop=True)
        av = pd.read_csv(os.path.join(d, "availability.csv")); sm = json.load(open(os.path.join(d, "summary.json")))
        fetch_fail += len(sm.get("fetch_failures", []))
        log = open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read()
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
        rev = np.zeros(len(cat), bool); hit = np.zeros(len(cat), bool)
        if len(cat):
            for src, bull in (("ISC", isc), ("USGS", None)):
                m = (cat.source == src).to_numpy()
                if src == "USGS":
                    for kind, b in (("regional", usg), ("tele", tele)):
                        mm = m & (cat.kind == kind).to_numpy(); r_, h_ = vr.label_rows(cat[mm], b, src); rev[mm] = r_; hit[mm] = h_
                else:
                    r_, h_ = vr.label_rows(cat[m], bull, src); rev[m] = r_; hit[m] = h_
            for s in ("ISC", "USGS"):
                cat_rows[s][0] += int(((cat.source == s).to_numpy() & rev).sum()); cat_rows[s][1] += int((cat.source == s).sum())
        cat_rows["all"] += len(cat); cat_rows["reviewed"] += int(rev.sum()); cat_rows["matched"] += int(hit.sum())
        P = cat.p_pred.to_numpy(float) if len(cat) else np.array([])
        t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy()
        stored = (ep.assoc_event >= 0).to_numpy(); agree.append(((stored == v2.assoc_vec(P, t_on, t_off)).sum(), len(ep)))
        ep["rev_assoc"] = v2.assoc_vec(P[rev], t_on, t_off) if len(cat) else np.zeros(len(ep), bool)
        rev_p += list(P[rev])
        eps.append(ep); avs.append(av)
    ep = pd.concat(eps, ignore_index=True); av = pd.concat(avs, ignore_index=True).drop_duplicates("day")
    ep["day"] = ep.t_on_utc.str[:10]
    rp = np.array(rev_p); lam = float(((rp >= Y0) & (rp < Y1)).sum()) / YEAR_S
    ag = sum(a for a, _ in agree) / max(1, sum(n for _, n in agree))
    return ep, av, dist, {"chunks": chunks, "catalogue_rows": cat_rows, "selfcheck_assoc_agreement": round(ag, 5),
                          "selfcheck_pass": ag >= 0.995, "lambda_reviewed_per_s": lam, "fetch_failures": fetch_fail}


def score_net(net):
    ep, av, dist, info = load_net(net)
    act, cat_assoc, days, outage, *_ = actions(ep, av, dist, "MAKZ", P3_2T)
    rev = ep.rev_assoc.to_numpy(bool); ndays = int(av.day.nunique())
    w = (ep.t_off - ep.t_on).to_numpy() + 15.0; p = 1 - np.exp(-info["lambda_reviewed_per_s"] * w)
    res = {**info, "calendar_days": ndays, "outage_days": int((av.MK31_valid_share < 0.1).sum()), "episodes": int(len(ep)),
           "episodes_per_day": round(len(ep) / ndays, 2), "reviewed_associated": int(rev.sum()), "catalogue_associated": int(cat_assoc.sum()),
           "reviewed_associated_outage": int((rev & outage).sum()), "outage_days_with_rev_assoc": int(len(set(days[rev & outage]))),
           "sum_p_all_episodes": round(float(p.sum()), 2), "distances_km": dist,
           "window_w_s": {"median": round(float(np.median(w)), 1), "p10": round(float(np.percentile(w, 10)), 1),
                          "p90": round(float(np.percentile(w, 90)), 1), "mean": round(float(w.mean()), 1)}}
    res["levels"] = {k: {"dismissed_rev_assoc": int(((a == "D") & rev).sum()), "dismissed_cat_assoc": int(((a == "D") & cat_assoc).sum()),
                         "dismissed_rev_assoc_outage": int(((a == "D") & rev & outage).sum()),
                         "expected_chance_among_dismissed": round(float(p[a == "D"].sum()), 2),
                         "alerts": int((a == "A").sum()), "unassoc_alerts_rev": int(((a == "A") & ~rev).sum()),
                         "unassoc_alerts_cat": int(((a == "A") & ~cat_assoc).sum()), "escalations": int((a == "E").sum()),
                         "esc_per_day": round(float((a == "E").sum()) / ndays, 2),
                         "unassoc_alerts_rev_per_day": round(float(((a == "A") & ~rev).sum()) / ndays, 2)} for k, a in act.items()}
    A = res["levels"]["P3-2t"]["dismissed_rev_assoc"]
    res["chance_share_P3_2t"] = round(res["levels"]["P3-2t"]["expected_chance_among_dismissed"] / max(A, 1), 3)
    ex = rev.sum() >= 30
    res["T1"] = {x: ({**published_boot(days, rev, act[x], act["P3-2t"]), "exercised": True} if ex else {"exercised": False}) for x in XS}
    exo = (rev & outage).sum() >= 10 and res["outage_days_with_rev_assoc"] >= 5
    res["T2"] = {**outage_boot(days, rev & outage, act["CG"], act["P1"]), "exercised": True} if exo else \
        {"exercised": False, "rev_assoc_outage": int((rev & outage).sum()), "outage_days_with_rev_assoc": res["outage_days_with_rev_assoc"]}
    res["S1_corrected"] = {x: corrected_boot(days, rev, p, act[x], act["P3-2t"]) for x in XS}
    res["S2_workload_rev"] = {x: dayboot(days, rev, act[x], act["P3-2t"], ndays=ndays) for x in XS}
    res["S3_vs_P3_7.5"] = {f"{x} reviewed": published_boot(days, rev, act[x], act["P3"]) for x in ("CG", "CG-D")}
    res["S3_vs_P3_7.5"].update({f"{x} catalogue": published_boot(days, cat_assoc, act[x], act["P3"]) for x in ("CG", "CG-D")})
    res["S4_catalogue_vs_P3_2t"] = {x: {**published_boot(days, cat_assoc, act[x], act["P3-2t"]),
                                         **{k: v for k, v in dayboot(days, cat_assoc, act[x], act["P3-2t"], ndays=ndays).items() if k.startswith(("ua", "esc"))}}
                                    for x in XS}
    return res


def git(*a): return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True).stdout.strip()


def chronology():
    ch = {"plan_commit": git("log", "--format=%H %cI", "--diff-filter=A", "--", "PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md").splitlines()[-1:],
          "code_commits": {f: git("log", "--format=%h %cI", "--diff-filter=A", "--", f"analysis/tdh2023_p1/{f}") for f in
                           ("verify_disjoint.py", "download.py", "labels.py", "run.py", "score.py")}}
    try:
        act = json.loads(subprocess.run(["gh", "api", "repos/Syrym-Zhakypbekov/criteria-governed-seismic-alarm-decisions/activity?per_page=100"],
                                        capture_output=True, text=True).stdout)
        sha = ch["plan_commit"][0].split()[0] if ch["plan_commit"] else ""
        ch["plan_push_github_activity"] = [x["timestamp"] for x in act if x.get("after") == sha]
    except Exception as e:
        ch["plan_push_github_activity"] = f"error {e}"
    fr = []
    for f in glob.glob(os.path.join(OUT, "download", "*.json")):
        fr += [v["requested_utc"] for v in json.load(open(f))["days"].values() if v.get("requested_utc")]
    ch["first_waveform_request_utc"] = min(fr) if fr else None
    lf = glob.glob(os.path.join(LAB_DIR, "*.*"))
    ch["first_label_file_mtime_utc"] = min(dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc).isoformat(timespec="seconds") for f in lf) if lf else None
    ch["scored_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return ch


def write_md(res):
    L = ["# RESULTS — time-disjoint validation 2023 (Paper 1 rule, IU.MAKZ and AK networks)", "",
         f"Pre-registration: PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md, commit {res['chronology']['plan_commit']}, GitHub push "
         f"{res['chronology']['plan_push_github_activity']}; first waveform request {res['chronology']['first_waveform_request_utc']}. "
         "Every number below is written by analysis/tdh2023_p1/score.py from results/tdh2023_p1/tdh2023_p1_eval.json. "
         "Frozen rule and thresholds (no re-tuning); comparator P3-2t (8.0 / 10.0 dB); margin 3 points; paired day bootstrap, 2000, seed 7.", "",
         "## Confirmatory family (Holm, one-sided alpha 0.025)", "",
         "| hypothesis | difference pp [95% CI] | p one-sided | p Holm | verdict |", "|---|---|---|---|---|"]
    for k, h in res["family"].items():
        if not h.get("exercised"): L.append(f"| {k} | not exercised | | | not exercised |"); continue
        L.append(f"| {k} | {h['diff_pp']} [{h['ci95_pp'][0]}, {h['ci95_pp'][1]}] | {h['p_one_sided']} | {h['p_holm']} | "
                 f"{'HELD' if h['met_after_holm'] else 'NOT HELD'} |")
    for net, r in res["networks"].items():
        L += ["", f"## {net}", "",
              f"Chunks: {r['chunks']}; calendar days {r['calendar_days']} (outage days of the nearest neighbour {r['outage_days']}); "
              f"episodes {r['episodes']} ({r['episodes_per_day']}/day); reviewed-associated {r['reviewed_associated']} "
              f"(catalogue-associated {r['catalogue_associated']}); catalogue rows reviewed / all {r['catalogue_rows']['reviewed']} / "
              f"{r['catalogue_rows']['all']}; association self-check {r['selfcheck_assoc_agreement']}; fetch failures {r['fetch_failures']}; "
              f"expected chance share among P3-2t reviewed-associated dismissals {r['chance_share_P3_2t']}.", "",
              "| policy | dismissed rev-assoc | dismissed on outage days | unassoc. alerts/day | escalations/day | expected chance among dismissed |",
              "|---|---|---|---|---|---|"]
        for p, v in r["levels"].items():
            L.append(f"| {p} | {v['dismissed_rev_assoc']} | {v['dismissed_rev_assoc_outage']} | {v['unassoc_alerts_rev_per_day']} | {v['esc_per_day']} | {v['expected_chance_among_dismissed']} |")
        L += ["", "| X − P3-2t | raw pp [95%] | chance-corrected pp [95%] (upper ≤ 3?) | unassoc. alerts/day [95%] | escalations/day [95%] |",
              "|---|---|---|---|---|"]
        for x in XS:
            t = r["T1"][x]; c = r["S1_corrected"][x]; s = r["S2_workload_rev"][x]
            raw = f"{t['diff_pp']} [{t['ci95_pp'][0]}, {t['ci95_pp'][1]}]" if t.get("exercised") else "not exercised"
            L.append(f"| {x} | {raw} | {c['diff_pp']} [{c['ci95_pp'][0]}, {c['ci95_pp'][1]}] ({'met' if c['met_upper_le_3'] else 'not met'}) | "
                     f"{s['ua_per_day']} [{s['ua_ci'][0]}, {s['ua_ci'][1]}] | {s['esc_per_day']} [{s['esc_ci'][0]}, {s['esc_ci'][1]}] |")
        L += ["", "Registered comparator P3 7.5 dB (S3): " + "; ".join(f"{k}: {v['diff_pp']} [{v['ci95_pp'][0]}, {v['ci95_pp'][1]}]" for k, v in r["S3_vs_P3_7.5"].items()),
              "", "Catalogue association vs P3-2t (S4): " + "; ".join(f"{k}: {v['diff_pp']} [{v['ci95_pp'][0]}, {v['ci95_pp'][1]}]" for k, v in r["S4_catalogue_vs_P3_2t"].items())]
    L += ["", "## Notes (generated)", ""]
    for net, r in res["networks"].items():
        cr = r["catalogue_rows"]; nc = [k for k, v in r["chunks"].items() if v != "completed"]
        L.append(f"- {net}: REVIEWED share of catalogue rows {round(cr['reviewed'] / max(cr['all'], 1), 3)} (ISC {cr['ISC'][0]}/{cr['ISC'][1]}, "
                 f"USGS {cr['USGS'][0]}/{cr['USGS'][1]}); P3-2t dismissed {r['levels']['P3-2t']['dismissed_rev_assoc']} of "
                 f"{r['reviewed_associated']} reviewed-associated episodes, CG {r['levels']['CG']['dismissed_rev_assoc']}: the margin tests rest on few "
                 f"dismissals; outage days {r['outage_days']} (T2 {'exercised' if r['T2'].get('exercised') else 'not exercised'})"
                 + (f"; quarters not completed (plan section 9, scored on the completed quarters, nothing replaced): {', '.join(nc)} — {r['chunks'][nc[0]]}" if nc else "") + ".")
    open(os.path.join(root, "RESULTS_tdh2023.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    res = {"preregistration": "PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md", "networks": {}}
    for net in CFG["networks"]:
        res["networks"][net] = score_net(net); print(net, "done", flush=True)
    fam = {}
    lab = {"IU_MAKZ": "IU.MAKZ", "AK": "AK"}
    for net, r in res["networks"].items():
        for x in XS: fam[f"T1-{lab[net]}-{x}"] = dict(r["T1"][x])
        fam[f"T2-{lab[net]}"] = dict(r["T2"])
    exk = sorted([k for k, v in fam.items() if v.get("exercised")], key=lambda k: fam[k]["p_one_sided"]); run = 0.0
    for i, k in enumerate(exk):
        run = max(run, min(1.0, (len(exk) - i) * fam[k]["p_one_sided"])); fam[k]["p_holm"] = round(run, 5)
        fam[k]["met_after_holm"] = bool(run <= ALPHA)
    res["family"] = fam; res["family_m"] = len(exk); res["chronology"] = chronology()
    json.dump(res, open(os.path.join(OUT, "tdh2023_p1_eval.json"), "w"), indent=1, default=str)
    json.dump(res["chronology"], open(os.path.join(OUT, "chronology.json"), "w"), indent=1)
    write_md(res); print(json.dumps(fam, indent=1))


if __name__ == "__main__":
    main()
