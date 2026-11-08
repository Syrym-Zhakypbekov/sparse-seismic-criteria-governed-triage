"""Scorer of PREREGISTRATION_CONTEXT_C_2026-11-08.md (pushed d25b86c before fitting or scoring).

Context-dependent reliability of a non-confirming site, c_j(x) = P(site j confirms | catalogued event, x),
x = (SNR_ref, log distance, noise proxies from the tuning week, causal site history). Logistic regression fitted on the
IU.MAKZ development period + batch-A networks (AU AV C1 IV KR OH); tested on batch B (reviewed labels T1, catalogue labels
T2) and on the KZ network (T3). Only the weight of a valid NO changes; the rest of rule v2 is the frozen code path.
Output: results/context_c/context_c.json + calibration_T1.png, calibration_T2.png.
"""
import os, re, json, glob, math, importlib.util
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
R = os.path.join(root, "results"); OUT = os.path.join(R, "context_c")


def _mod(name, fn):
    s = importlib.util.spec_from_file_location(name, os.path.join(here, fn)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


v2 = _mod("v2", "v2_networks.py"); rb = _mod("rb", "v2_reviewed_bulletin.py")
TRAIN_V2 = ["AU", "AV", "C1", "IV", "KR", "OH"]
CLIP = (0.05, 1.0); NBOOT, SEED = 2000, 7
FEATS = ["snr", "snr_ok", "logd", "thr", "hist"]   # lrate dropped: deviation D1


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


# ------------------------------------------------------------------ inputs per network (no catalogue in the features)
def tune_summary(net):
    """Tuning-week thresholds of the frozen pipeline: the 'thresholds {...}' line every tune run.log starts with.
    (Tuning-week trigger counts are missing in most tune logs: deviation D1, lrate dropped before any fit.)"""
    import ast
    f = sorted(glob.glob(os.path.join(R, "v2", "runs", net, "tune_*", "run.log")))[0]
    for line in open(f, encoding="utf-8", errors="replace"):
        if line.startswith("thresholds "): return {"thresholds_q99.9": ast.literal_eval(line[len("thresholds "):].strip()), "episodes": {}}
    raise RuntimeError("no tuning thresholds: " + net)


def site_features(ep, sites, dists, thr, eps):
    """sites: list of member-role lists (nearest first); dists: site distance km; thr/eps: per-role tuning threshold and
    trigger count incl. 'MAKZ'. Returns merged site states and a per-site feature frame (one row per episode)."""
    states = {r: ep[f"n_{r}"].astype(str).to_numpy() for s in sites for r in s}
    S = v2.merge_sites(states, sites)[:3]
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    F = []
    for k, s in enumerate(S):
        valid = np.isin(s, ["YES", "NO"]); yes = s == "YES"
        cv = np.concatenate([[0], np.cumsum(valid)[:-1]]); cy = np.concatenate([[0], np.cumsum(yes & valid)[:-1]])
        h = (cy + 1) / (cv + 2)
        m = sites[k]
        F.append(pd.DataFrame({"snr": np.where(ok, np.clip(snr, 0, 40) / 40, 0.0), "snr_ok": ok.astype(float),
                               "logd": math.log10(max(dists[k], 1.0)),
                               "thr": float(np.mean([thr[r] for r in m])),
                               "lrate": float(np.mean([math.log((eps.get(r, 0) + 1) / (eps.get("MAKZ", 0) + 1)) for r in m])),
                               "hist": np.log(h / (1 - h)), "rank": k, "state": s,
                               "bin": pd.cut(pd.Series(np.where(ok, snr, np.nan)), v2.BINS, labels=v2.LAB).astype(str).to_numpy()}))
    return S, F, snr, ok


def load_v2(net, cfg, reviewed=False):
    if reviewed:
        got = reviewed_load(net, cfg)
    else:
        got = v2.load_network(net, cfg)
    if got is None or got == "incomplete": return None
    ep, av, cat, fails = got
    ep = ep.sort_values("t_on", kind="stable").reset_index(drop=True)
    sites = [[f"S{i + 1}_{j + 1}" for j in range(len(s["members"]))] for i, s in enumerate(cfg["sites"])]
    dists = [s["dist_km"] for s in cfg["sites"]]
    ts = tune_summary(net)
    S, F, snr, ok = site_features(ep, sites, dists, ts["thresholds_q99.9"], ts["episodes"])
    return dict(net=net, ep=ep, av=av, cat=cat, fails=fails, S=S, F=F, snr=snr, ok=ok, sites=sites, cfg=cfg)


def reviewed_load(net, cfg):
    """The reviewed relabelling of v2_reviewed_bulletin.score(), unchanged: catalogue rows matched to the ISC / ComCat
    bulletins, episodes re-associated on REVIEWED rows only."""
    tele = rb.arr([r for f in glob.glob(os.path.join(rb.LAB, "TELE_ALL_*.json")) for r in rb.parse_usgs(f)])
    isc = rb.arr([r for f in glob.glob(os.path.join(rb.LAB, f"ISC_{net}_*.xml")) for r in rb.parse_isc(f)])
    usg = rb.arr([r for f in glob.glob(os.path.join(rb.LAB, f"USGS_{net}_*.json")) for r in rb.parse_usgs(f)])
    got = v2.load_network(net, cfg)
    if got is None or got == "incomplete": return got
    ep, av, cat, fails = got
    cat = cat.reset_index(drop=True); rev = np.zeros(len(cat), bool)
    m = (cat.source == "ISC").to_numpy(); r, _ = rb.label_rows(cat[m], isc, "ISC"); rev[m] = r
    for kind, b in (("regional", usg), ("tele", tele)):
        mm = (cat.source == "USGS").to_numpy() & (cat.kind == kind).to_numpy(); r, _ = rb.label_rows(cat[mm], b, "USGS"); rev[mm] = r
    ra = v2.assoc_vec(cat.p_pred.to_numpy(float)[rev], ep.t_on.to_numpy(), ep.t_off.to_numpy())
    ep = ep.copy(); ep["assoc_event"] = np.where(ra, 0, -1)
    return ep, av, cat[rev].reset_index(drop=True), fails


def meta_coords():
    out = {}
    for s in json.load(open(os.path.join(R, "metadata", "station_comparison.json"))):
        out[s["stream"].split(".")[0] + "." + s["stream"].split(".")[1]] = (s["lat"], s["lon"])
    return out


def load_local(kind):
    """IU.MAKZ development (stage1_v3, training) or the KZ network (results/kz, test T3)."""
    C = meta_coords()
    if kind == "IU_dev":
        dirs = [os.path.join(R, "stage1_v3")]; summ = json.load(open(os.path.join(R, "stage1_v3", "summary.json")))
        st = {"MAKZ": "IU.MAKZ", "MK31": "IM.MK31", "KURK": "II.KURK", "WUS": "G.WUS"}
    else:
        dirs = sorted(d for d in glob.glob(os.path.join(R, "kz", "outKZ_*")) if not d.endswith("tune"))
        summ = json.load(open(os.path.join(R, "kz", "outKZ_tune", "summary.json")))
        st = {"MAKZ": "KZ.MAKZ", "MK31": "KZ.MKAR", "KURK": "KZ.KURK", "WUS": "KZ.PDGK"}
    ep = pd.concat([pd.read_csv(os.path.join(d, "episodes.csv")) for d in dirs], ignore_index=True)
    av = pd.concat([pd.read_csv(os.path.join(d, "availability.csv")) for d in dirs]).drop_duplicates("day").sort_values("day")
    cat = pd.concat([pd.read_csv(os.path.join(d, "catalog.csv")) for d in dirs], ignore_index=True)
    ep = ep.sort_values("t_on", kind="stable").reset_index(drop=True); ep["day"] = ep.t_on_utc.str[:10]
    roles = sorted(["MK31", "KURK", "WUS"], key=lambda r: km(C[st["MAKZ"]], C[st[r]]))
    sites = [[r] for r in roles]; dists = [km(C[st["MAKZ"]], C[st[r]]) for r in roles]
    S, F, snr, ok = site_features(ep, sites, dists, summ["thresholds_q99.9"], summ["episodes"])
    return dict(net=kind, ep=ep, av=av, cat=cat, fails=[], S=S, F=F, snr=snr, ok=ok, sites=sites, dists=dists)


# ------------------------------------------------------------------ rule v2 with a per-episode NO weight
def cg_with_q(S, qno, snr, ok):
    """Identical to the CG branch of v2.policies; qno[r] = weight of a valid NO at site rank r (array or scalar)."""
    n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for r, s in enumerate(S):
        q = np.isin(s, ["YES", "NO"]).astype(float); q = np.where(s == "NO", qno[r], q)
        num += v2.W_RANK[r] * (s == "YES") * q; den += v2.W_RANK[r] * q
    num += v2.W_SNR * np.clip(snr / 30, 0, 1) * ok; den += v2.W_SNR * ok
    dd = den >= v2.DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(n, "E", dtype=object); a[dd & (D >= v2.THETA_A)] = "A"; a[dd & (D <= v2.THETA_D)] = "D"
    return a


def tab_p(F, r):
    tab = v2.TAB.get("MAKZ", {}).get(v2.DEV_ROLE_BY_RANK[r], {})
    return np.array([tab.get(x, {"p": 0.5})["p"] if x in v2.LAB else 0.5 for x in F["bin"]])


def actions(d, model):
    S, F, snr, ok = d["S"], d["F"], d["snr"], d["ok"]
    act = v2.policies(S, snr, ok)
    ctx = [np.clip(model.predict_proba(F[r][FEATS].to_numpy())[:, 1], *CLIP) for r in range(len(S))]
    act["CG-ctx"] = cg_with_q(S, ctx, snr, ok)
    # self-check (plan section 3): the same code path reproduces CG_c05 and CG-D exactly
    chk = {"CG_c05": bool((cg_with_q(S, [0.5] * len(S), snr, ok) == act["CG_c05"]).all()),
           "CG-D": bool((cg_with_q(S, [tab_p(F[r], r) for r in range(len(S))], snr, ok) == act["CG-D"]).all())}
    return act, ctx, chk


def pairs(d, ctx, assoc):
    rows = []
    for r, f in enumerate(d["F"]):
        m = assoc & np.isin(f.state, ["YES", "NO"])
        rows.append(pd.DataFrame({"net": d["net"], "day": d["ep"].day.to_numpy()[m], "rank": r, "y": (f.state[m] == "YES").astype(int),
                                  "p_ctx": ctx[r][m], "p_tab": tab_p(f, r)[m]}))
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------ statistics
def brier_boot(P, n=NBOOT, seed=SEED):
    """Brier differences ctx - comparator, two-stage cluster bootstrap (networks, then days)."""
    P = P.copy(); P["c05"] = 0.5; P["c1"] = 1.0
    se = {k: (P[k] - P.y) ** 2 for k in ("p_ctx", "c05", "p_tab", "c1")}
    for k, v in se.items(): P["se_" + k] = v
    obs = {k: round(float(v.mean()), 4) for k, v in se.items()}
    nets = sorted(P.net.unique()); g = {k: {d: x.index.to_numpy() for d, x in P[P.net == k].groupby("day")} for k in nets}
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        ids = []
        for k in rng.choice(nets, len(nets)):
            days = list(g[k]); ids += [g[k][dd] for dd in rng.choice(days, len(days))]
        ids = np.concatenate(ids); X = P.loc[ids]
        v.append([X.se_p_ctx.mean() - X.se_c05.mean(), X.se_p_ctx.mean() - X.se_p_tab.mean(), X.se_p_ctx.mean() - X.se_c1.mean()])
    v = np.array(v); ci = lambda c: [round(float(np.percentile(v[:, c], 2.5)), 4), round(float(np.percentile(v[:, c], 97.5)), 4)]
    res = {"pairs": int(len(P)), "networks": len(nets), "confirm_rate": round(float(P.y.mean()), 4), "brier": obs,
           "ctx_minus_c05": {"diff": round(obs["p_ctx"] - obs["c05"], 4), "ci95": ci(0)},
           "ctx_minus_CGD_table": {"diff": round(obs["p_ctx"] - obs["p_tab"], 4), "ci95": ci(1)},
           "ctx_minus_c1": {"diff": round(obs["p_ctx"] - obs["c1"], 4), "ci95": ci(2)}}
    res["H3_holds"] = bool(res["ctx_minus_c05"]["ci95"][1] < 0 and res["ctx_minus_CGD_table"]["ci95"][1] < 0)
    bins = np.linspace(0, 1, 11); rel = []
    for k in ("p_ctx", "p_tab"):
        b = np.clip(np.digitize(P[k], bins) - 1, 0, 9)
        rel.append({"pred": k, "bins": [{"lo": round(bins[i], 1), "n": int((b == i).sum()), "mean_pred": round(float(P[k][b == i].mean()), 4),
                                         "obs_rate": round(float(P.y[b == i].mean()), 4)} for i in range(10) if (b == i).sum()]})
    res["reliability"] = rel
    return res


def decision_mix(d, act, assoc):
    nd = len(d["av"]); out = {}
    for k in ("CG", "CG_c05", "CG-D", "CG-ctx", "P3"):
        a = act[k]
        out[k] = {"alert_share": round(float((a == "A").mean()), 4), "dismiss_share": round(float((a == "D").mean()), 4),
                  "escalate_share": round(float((a == "E").mean()), 4), "esc_per_day": round(float((a == "E").sum()) / max(nd, 1), 2),
                  "dismissed_assoc": int(((a == "D") & assoc).sum()), "unassoc_alerts": int(((a == "A") & ~assoc).sum())}
    return out


def pool_mix(per):
    keys = ("CG", "CG_c05", "CG-D", "CG-ctx", "P3"); out = {}
    for k in keys:
        out[k] = {"dismissed_assoc": sum(p[k]["dismissed_assoc"] for p in per.values()),
                  "unassoc_alerts": sum(p[k]["unassoc_alerts"] for p in per.values()),
                  "mean_esc_per_day": round(float(np.mean([p[k]["esc_per_day"] for p in per.values()])), 2),
                  "mean_escalate_share": round(float(np.mean([p[k]["escalate_share"] for p in per.values()])), 4)}
    return out


def score_set(name, ds, model, include):
    data, P, mix, chk, nets = {}, [], {}, {}, {}
    for d in ds:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        act, ctx, c = actions(d, model); chk[d["net"]] = c
        mix[d["net"]] = decision_mix(d, act, assoc)
        nets[d["net"]] = {"episodes": int(len(d["ep"])), "associated": int(assoc.sum()), "included": bool(include(d, assoc)),
                          "CGctx_minus_P3": v2.day_boot(d["ep"].day.to_numpy(), assoc, act["CG-ctx"], act["P3"]),
                          "CGctx_minus_CGc05": v2.day_boot(d["ep"].day.to_numpy(), assoc, act["CG-ctx"], act["CG_c05"])}
        if nets[d["net"]]["included"]:
            data[d["net"]] = (d["ep"].day.to_numpy(), assoc, act); P.append(pairs(d, ctx, assoc))
    res = {"set": name, "networks_included": sorted(data), "selfcheck_all_ok": all(all(v.values()) for v in chk.values()), "selfcheck": chk}
    if len(data) >= 2:
        res["H1_CGctx_minus_P3"] = v2.cluster_boot(data, "CG-ctx", "P3")
        res["H1_holds"] = bool(res["H1_CGctx_minus_P3"]["pooled_noninferior"] and res["H1_CGctx_minus_P3"]["ratio_criterion_holds"])
        res["H2_CGctx_minus_CGc05"] = v2.cluster_boot(data, "CG-ctx", "CG_c05")
        res["H2_noninferior"] = bool(res["H2_CGctx_minus_CGc05"]["pooled_noninferior"])
        res["H2_no_more_dismissals"] = bool(res["H2_CGctx_minus_CGc05"]["pooled_diff_pp"] <= 0)
        res["ref_CGc05_minus_P3"] = v2.cluster_boot(data, "CG_c05", "P3")
        res["ref_CGD_minus_P3"] = v2.cluster_boot(data, "CG-D", "P3")
        res["ref_CG_minus_P3"] = v2.cluster_boot(data, "CG", "P3")
        res["H3_calibration"] = brier_boot(pd.concat(P, ignore_index=True))
    else:   # single network (T3): day bootstrap of that network
        d = ds[0]; assoc = (d["ep"].assoc_event >= 0).to_numpy(); act, ctx, _ = actions(d, model); days = d["ep"].day.to_numpy()
        res["H1_CGctx_minus_P3"] = v2.day_boot(days, assoc, act["CG-ctx"], act["P3"])
        res["H1_holds"] = bool(res["H1_CGctx_minus_P3"]["noninferior"])
        res["H2_CGctx_minus_CGc05"] = v2.day_boot(days, assoc, act["CG-ctx"], act["CG_c05"])
        res["H2_noninferior"] = bool(res["H2_CGctx_minus_CGc05"]["noninferior"])
        res["H2_no_more_dismissals"] = bool(res["H2_CGctx_minus_CGc05"]["diff_pp"] <= 0)
        res["ref_CGc05_minus_P3"] = v2.day_boot(days, assoc, act["CG_c05"], act["P3"])
        res["ref_CGD_minus_P3"] = v2.day_boot(days, assoc, act["CG-D"], act["P3"])
        res["ref_CG_minus_P3"] = v2.day_boot(days, assoc, act["CG"], act["P3"])
        pp = pairs(d, ctx, assoc); pp["day"] = pp["day"].astype(str)
        res["H3_calibration_descriptive"] = {"pairs": int(len(pp)), "brier_ctx": round(float(((pp.p_ctx - pp.y) ** 2).mean()), 4),
                                             "brier_c05": round(float(((0.5 - pp.y) ** 2).mean()), 4),
                                             "brier_tab": round(float(((pp.p_tab - pp.y) ** 2).mean()), 4),
                                             "brier_c1": round(float(((1 - pp.y) ** 2).mean()), 4)}
    inc = {k: v for k, v in mix.items() if k in data} or mix
    res["H4_decision_mix_pooled"] = pool_mix(inc); res["H4_decision_mix_per_network"] = mix; res["per_network"] = nets
    return res, (pd.concat(P, ignore_index=True) if P else None)


def plot_rel(P, title, fn):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 5)); bins = np.linspace(0, 1, 11)
    for k, lab, mk in (("p_ctx", "context c_j(x)", "o"), ("p_tab", "CG-D table", "s")):
        b = np.clip(np.digitize(P[k], bins) - 1, 0, 9); xs, ys, ns = [], [], []
        for i in range(10):
            m = b == i
            if m.sum() >= 20: xs.append(P[k][m].mean()); ys.append(P.y[m].mean()); ns.append(m.sum())
        ax.plot(xs, ys, marker=mk, label=lab)
    ax.axhline(P.y.mean(), ls=":", c="grey", label=f"observed base rate {P.y.mean():.2f}"); ax.plot([0.5], [P.y.mean()], "x", c="grey", ms=9, label="constant c = 0.5")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("predicted confirmation probability"); ax.set_ylabel("observed confirmation rate")
    ax.set_title(title, fontsize=9); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(fn, dpi=200); plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    C = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}
    batchB = [c["network"] for c in json.load(open(os.path.join(R, "v2", "networks_batchB.json")))["networks"]]
    # ---------------- training
    train = [load_local("IU_dev")] + [x for x in (load_v2(n, C[n]) for n in TRAIN_V2) if x is not None]
    X, y, src = [], [], []
    for d in train:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        for f in d["F"]:
            m = assoc & np.isin(f.state, ["YES", "NO"])
            X.append(f[FEATS].to_numpy()[m]); y.append((f.state[m] == "YES").astype(int)); src += [d["net"]] * int(m.sum())
    X = np.vstack(X); y = np.concatenate(y)
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1

    class M:   # standardisation on the training set + logistic regression (plan section 3)
        lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - mu) / sd, y)
        def predict_proba(self, Z): return self.lr.predict_proba((Z - mu) / sd)
    model = M()
    ptr = np.clip(model.predict_proba(X)[:, 1], *CLIP)
    out = {"preregistration": "PREREGISTRATION_CONTEXT_C_2026-11-08.md (d25b86c)",
           "training": {"sets": [d["net"] for d in train], "pairs": int(len(y)), "confirm_rate": round(float(y.mean()), 4),
                        "pairs_by_set": {k: int(v) for k, v in pd.Series(src).value_counts().items()},
                        "coef_standardised": dict(zip(FEATS, [round(float(c), 4) for c in M.lr.coef_[0]])),
                        "intercept": round(float(M.lr.intercept_[0]), 4), "feature_mean": dict(zip(FEATS, mu.round(4).tolist())),
                        "feature_sd": dict(zip(FEATS, sd.round(4).tolist())),
                        "brier_in_sample": {"ctx": round(float(((ptr - y) ** 2).mean()), 4), "c05": round(float(((0.5 - y) ** 2).mean()), 4)}}}
    print(json.dumps(out["training"], indent=1), flush=True)
    # ---------------- tests
    rev = json.load(open(os.path.join(R, "v2_reviewed", "v2_eval_reviewed.json")))["networks"]
    catB = json.load(open(os.path.join(R, "v2", "v2_eval_batchB.json")))["networks"]
    t1 = [x for x in (load_v2(n, C[n], reviewed=True) for n in batchB if n in rev and rev[n].get("batch") == "B") if x is not None]
    out["T1_reviewed_batchB"], P1 = score_set("T1", t1, model, lambda d, a: rev[d["net"]].get("included_in_pooled", False))
    print("T1 done", flush=True)
    t2 = [x for x in (load_v2(n, C[n]) for n in batchB if catB.get(n, {}).get("included_in_pooled")) if x is not None]
    out["T2_catalogue_batchB"], P2 = score_set("T2", t2, model, lambda d, a: catB[d["net"]].get("included_in_pooled", False))
    print("T2 done", flush=True)
    out["T3_KZ_network_catalogue"], _ = score_set("T3", [load_local("KZ")], model, lambda d, a: True)
    json.dump(out, open(os.path.join(OUT, "context_c.json"), "w"), indent=1, default=str)
    if P1 is not None: plot_rel(P1, "T1 batch B, reviewed-associated episodes", os.path.join(OUT, "calibration_T1.png"))
    if P2 is not None: plot_rel(P2, "T2 batch B, catalogue-associated episodes", os.path.join(OUT, "calibration_T2.png"))
    brief = {k: {kk: vv for kk, vv in v.items() if kk not in ("H4_decision_mix_per_network", "per_network", "selfcheck")}
             for k, v in out.items() if k.startswith("T")}
    print(json.dumps(brief, indent=1, default=str))


if __name__ == "__main__":
    main()
