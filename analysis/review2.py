"""Post hoc analyses requested by the v33 internal reviews (plans pushed in 55104e4 before computing).

Subcommands (results in results/review2/):
  undefined_snr   PLAN_undefined_snr_2026-11-08.md
  margin_cost     PLAN_margin_cost_2026-11-08.md
  threshold_table PLAN_threshold_table_2026-11-08.md
  build_t1        cache of the training and T1 sets of Section 4.15 (results/review2/_t1.pkl, local)
  calendar_ctx    PLAN_calendar_ctx_2026-11-08.md
  holm_hires      PLAN_holm_hires_2026-11-08.md
  learned         PLAN_learned_rejectband_2026-11-08.md
Frozen decision rules throughout; no download.
"""
import os, sys, json, pickle, itertools, importlib.util, time
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "results", "review2"); os.makedirs(OUT, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


v2 = _load("v2r2", os.path.join(here, "v2_networks.py"))
POL = ["CG", "CG-D", "CG_c05"]


def dump(name, obj):
    json.dump(obj, open(os.path.join(OUT, name + ".json"), "w"), indent=1,
              default=lambda o: o.tolist() if hasattr(o, "tolist") else (bool(o) if isinstance(o, np.bool_) else str(o)))


def reviewed33():
    r = pickle.load(open(os.path.join(root, "results", "posthoc", "_collect_reviewed.pkl"), "rb"))
    return {k: v for k, v in sorted(r.items()) if v.get("included")}


def nets_of(R, act_key=None):
    return {k: (v["days"], np.asarray(v["assoc"], bool), v["act"] if act_key is None else act_key(v)) for k, v in R.items()}


KEEP = ["pooled_diff_pp", "pooled_ci95_pp", "pooled_noninferior", "ratio", "ratio_ci95", "ratio_criterion_holds"]


# ---------------------------------------------------------------- 2. undefined SNR escalated
def undefined_snr():
    R = reviewed33(); out = {"plan": "PLAN_undefined_snr_2026-11-08.md (55104e4)", "networks": len(R)}
    und = sum(int((~v["ok"]).sum()) for v in R.values())
    und_assoc = sum(int(((~v["ok"]) & np.asarray(v["assoc"], bool)).sum()) for v in R.values())
    out["episodes_undefined_snr"] = und; out["reviewed_associated_with_undefined_snr"] = und_assoc
    out["policies"] = {}
    for p in POL:
        fro = {k: v["act"][p] for k, v in R.items()}
        var = {k: np.where(~v["ok"], "E", v["act"][p]).astype(object) for k, v in R.items()}
        ch = {}
        for k, v in R.items():
            m = (~v["ok"]) & (fro[k] != "E")
            for a in ("A", "D"): ch[a] = ch.get(a, 0) + int((m & (fro[k] == a)).sum())
        dis_ch = sum(int(((~v["ok"]) & (fro[k] == "D") & np.asarray(v["assoc"], bool)).sum()) for k, v in R.items())
        acts = {k: {"X": var[k], "F": fro[k], "P3": v["act"]["P3"]} for k, v in R.items()}
        nets = {k: (v["days"], np.asarray(v["assoc"], bool), acts[k]) for k, v in R.items()}
        bf = v2.cluster_boot(nets, "F", "P3"); bv = v2.cluster_boot(nets, "X", "P3")
        out["policies"][p] = {"changed_decisions_from": ch, "reviewed_associated_dismissals_removed": dis_ch,
                              "frozen_minus_P3": {x: bf[x] for x in KEEP}, "variant_minus_P3": {x: bv[x] for x in KEEP},
                              "verdict_changed": bool(bf["pooled_noninferior"] != bv["pooled_noninferior"] or
                                                      bf["ratio_criterion_holds"] != bv["ratio_criterion_holds"])}
    dump("undefined_snr", out); print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- 5. margin from costs
def margin_cost():
    T = json.load(open(os.path.join(root, "results", "posthoc", "twothreshold.json")))
    it = T["analyst_items"]; R = reviewed33(); n_assoc = sum(int(np.asarray(v["assoc"], bool).sum()) for v in R.values())
    out = {"plan": "PLAN_margin_cost_2026-11-08.md (55104e4)", "source": "results/posthoc/twothreshold.json analyst_items",
           "reviewed_associated": n_assoc, "minutes_per_escalation": 2, "counts": {k: it[k] for k in ("P3", "CG_c05", "CG-D")}, "cells": []}
    obs = {k: (it[k]["dismissed_associated"] - it["P3"]["dismissed_associated"]) / n_assoc * 100 for k in ("CG_c05", "CG-D")}
    out["observed_extra_dismissed_pp"] = {k: round(v, 3) for k, v in obs.items()}
    for f in (0, 0.5, 1, 2):
        for k in (30, 60, 120, 240):
            row = {"f_min_per_false_alert": f, "k_min_per_dismissed_reviewed": k}
            for p in ("CG_c05", "CG-D"):
                sav = 2 * (it["P3"]["escalations"] - it[p]["escalations"]) + f * (it["P3"]["unassociated_alerts"] - it[p]["unassociated_alerts"])
                be = sav / k / n_assoc * 100
                row[p] = {"saving_minutes": round(sav, 1), "break_even_margin_pp": round(be, 3),
                          "observed_within_break_even": bool(obs[p] <= be), "margin_3pp_lenient": bool(3.0 > be)}
            out["cells"].append(row)
    dump("margin_cost", out); print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- 6. Table A2 check
def closed_form(pat, c, snr):
    """Action of CG with constant NO weight c for state pattern pat (len 3) and valid SNR array."""
    Y = sum(v2.W_RANK[r] for r, s in enumerate(pat) if s == "YES")
    Q = Y + sum(c[r] if isinstance(c, (list, tuple)) else c for r, s in enumerate(pat) if s == "NO") if False else None
    return Y


def threshold_table():
    rows = json.load(open(os.path.join(root, "results", "posthoc", "threshold_table.json")))
    out = {"plan": "PLAN_threshold_table_2026-11-08.md (55104e4)", "cells_checked": 0, "cell_mismatches": [], "episode_check": {}}
    W, WS = v2.W_RANK, v2.W_SNR

    def cf_thresholds(pat, qno):
        """qno: per-rank NO weight. Returns (dismiss_max_db or None, alert_min_db or None) on the 0.01 dB grid in [0, 40]."""
        Y = sum(W[r] for r, s in enumerate(pat) if s == "YES")
        Q = Y + sum(W[r] * qno[r] for r, s in enumerate(pat) if s == "NO")
        den = Q + WS
        if den < v2.DELTA: return None, None
        # D(snr) = (Y + WS*min(snr/30,1)) / den, nondecreasing in snr
        smax = (v2.THETA_D * den - Y) / WS * 30          # dismiss iff snr <= smax (if smax >= 0)
        smin = (v2.THETA_A * den - Y) / WS * 30          # alert iff snr >= smin (if <= 30)
        g = np.round(np.arange(0, 40.0001, 0.01), 2)
        D = (Y + WS * np.clip(g / 30, 0, 1)) / den
        d = g[D <= v2.THETA_D + 1e-12]; a = g[D >= v2.THETA_A - 1e-12]
        return (float(d.max()) if len(d) else None), (float(a.min()) if len(a) else None)

    for r in rows:
        pat = [{"Y": "YES", "N": "NO", "M": "MISSING"}[x] for x in r["pattern"].split("/")]
        for key, c in (("CG", 1.0), ("CG_c05", 0.5)):
            dm, am = cf_thresholds(pat, [c] * 3); out["cells_checked"] += 1
            t = r[key]
            if not ((dm is None and t["dismiss_max_db"] is None) or (dm is not None and t["dismiss_max_db"] is not None and abs(dm - t["dismiss_max_db"]) <= 0.011)) \
               or not ((am is None and t["alert_min_db"] is None) or (am is not None and t["alert_min_db"] is not None and abs(am - t["alert_min_db"]) <= 0.011)):
                out["cell_mismatches"].append({"pattern": r["pattern"], "policy": key, "table": [t["dismiss_max_db"], t["alert_min_db"]], "closed_form": [dm, am]})
        # CG-D: per SNR bin closed form (development-table NO weight of that bin), evaluated on the grid
        g = np.round(np.arange(0, 40.0001, 0.01), 2)
        bins = np.digitize(g, v2.BINS[1:-1], right=False)   # index into LAB, BINS edges are right-open in pd.cut? checked below
        import pandas as pd
        lab = pd.cut(pd.Series(g), v2.BINS, labels=v2.LAB).astype(str).to_numpy()
        act = np.full(len(g), "E", dtype=object)
        for i, x in enumerate(g):
            qno = []
            for rk in range(3):
                tab = v2.TAB.get("MAKZ", {}).get(v2.DEV_ROLE_BY_RANK[rk], {})
                qno.append(tab.get(lab[i], {"p": 0.5})["p"] if lab[i] in v2.LAB else 0.5)
            Y = sum(W[k] for k, s in enumerate(pat) if s == "YES"); Q = Y + sum(W[k] * qno[k] for k, s in enumerate(pat) if s == "NO")
            den = Q + WS
            if den < v2.DELTA: continue
            D = (Y + WS * min(x / 30, 1)) / den
            if D >= v2.THETA_A: act[i] = "A"
            elif D <= v2.THETA_D: act[i] = "D"
        d = g[act == "D"]; a = g[act == "A"]; dm = float(d.max()) if len(d) else None; am = float(a.min()) if len(a) else None
        t = r["CG-D"]; out["cells_checked"] += 1
        if (dm != t["dismiss_max_db"] and not (dm is not None and t["dismiss_max_db"] is not None and abs(dm - t["dismiss_max_db"]) <= 0.011)) or \
           (am != t["alert_min_db"] and not (am is not None and t["alert_min_db"] is not None and abs(am - t["alert_min_db"]) <= 0.011)):
            out["cell_mismatches"].append({"pattern": r["pattern"], "policy": "CG-D", "table": [t["dismiss_max_db"], t["alert_min_db"]], "closed_form": [dm, am]})
    # episode check: closed form for c = 1, 0.5 vs frozen actions (valid SNR episodes)
    R = reviewed33()
    for key, c in (("CG", 1.0), ("CG_c05", 0.5)):
        tot = mis = 0
        for k, v in R.items():
            S = [np.asarray(s, object) for s in v["S"][:3]]; snr = v["snr"]; ok = v["ok"]
            while len(S) < 3: S.append(np.full(len(snr), "MISSING", dtype=object))
            Y = sum(W[r] * (S[r] == "YES") for r in range(3)); Q = Y + sum(W[r] * c * (S[r] == "NO") for r in range(3))
            den = Q + WS; D = (Y + WS * np.clip(snr / 30, 0, 1)) / den
            pred = np.full(len(snr), "E", dtype=object); okd = den >= v2.DELTA
            pred[okd & (D >= v2.THETA_A)] = "A"; pred[okd & (D <= v2.THETA_D)] = "D"
            m = ok; tot += int(m.sum()); mis += int((pred[m] != v["act"][key][m]).sum())
        out["episode_check"][key] = {"valid_snr_episodes": tot, "mismatches": mis}
    dump("threshold_table", out); print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- T1 / training cache (Section 4.15 sets)
def build_t1():
    cc = _load("ctxc_r2", os.path.join(here, "context_c.py"))
    from sklearn.linear_model import LogisticRegression
    R = cc.R
    C = {c["network"]: c for f in ("networks.json", "networks_batchB.json") for c in json.load(open(os.path.join(R, "v2", f)))["networks"]}
    batchB = [c["network"] for c in json.load(open(os.path.join(R, "v2", "networks_batchB.json")))["networks"]]
    train = [cc.load_local("IU_dev")] + [x for x in (cc.load_v2(n, C[n]) for n in cc.TRAIN_V2) if x is not None]
    X, y = [], []
    for d in train:
        assoc = (d["ep"].assoc_event >= 0).to_numpy()
        for f in d["F"]:
            m = assoc & np.isin(f.state, ["YES", "NO"]); X.append(f[cc.FEATS].to_numpy()[m]); y.append((f.state[m] == "YES").astype(int))
    X = np.vstack(X); y = np.concatenate(y); mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit((X - mu) / sd, y)
    full = lambda Z: lr.predict_proba((Z - mu) / sd)[:, 1]
    rev = json.load(open(os.path.join(R, "v2_reviewed", "v2_eval_reviewed.json")))["networks"]
    t1 = [x for x in (cc.load_v2(n, C[n], reviewed=True) for n in batchB if n in rev and rev[n].get("batch") == "B") if x is not None]

    def pack(d, ctx=True):
        assoc = (d["ep"].assoc_event >= 0).to_numpy(); S, F, snr, ok = d["S"], d["F"], d["snr"], d["ok"]
        act = v2.policies(S, snr, ok)
        if ctx: act["CG-ctx"] = cc.cg_with_q(S, [np.clip(full(F[r][cc.FEATS].to_numpy()), *cc.CLIP) for r in range(len(S))], snr, ok)
        return {"net": d["net"], "day": d["ep"].day.to_numpy(), "assoc": assoc, "S": [np.asarray(s, object) for s in S[:3]],
                "snr": np.asarray(snr, float), "ok": np.asarray(ok, bool), "act": act}
    T = {"train": [pack(d, ctx=False) for d in train],
         "t1": [pack(d) for d in t1 if rev[d["net"]].get("included_in_pooled", False)]}
    pickle.dump(T, open(os.path.join(OUT, "_t1.pkl"), "wb"))
    tal = {k: int(sum(((x["act"][k] == "D") & x["assoc"]).sum() for x in T["t1"])) for k in ("CG-ctx", "CG_c05", "P3", "CG-D")}
    print("train sets", [x["net"] for x in T["train"]], "t1", len(T["t1"]), "dismissed_assoc", tal)


def t1():
    return pickle.load(open(os.path.join(OUT, "_t1.pkl"), "rb"))


# ---------------------------------------------------------------- 3. shared-calendar bootstrap for T1
def calendar_ctx(nrep=10000, seed=7):
    T = t1()["t1"]; pols = ["CG-ctx", "CG_c05", "P3"]
    alld = sorted(set(np.concatenate([x["day"] for x in T]))); d0 = np.datetime64(alld[0]); nd = int((np.datetime64(alld[-1]) - d0).astype(int)) + 1
    C = np.zeros((len(T), 1 + len(pols), nd))
    for i, x in enumerate(T):
        di = (np.array(x["day"], dtype="datetime64[D]") - d0).astype(int)
        np.add.at(C[i, 0], di[x["assoc"]], 1)
        for j, p in enumerate(pols): np.add.at(C[i, j + 1], di[x["assoc"] & (x["act"][p] == "D")], 1)
    tot = C.sum(axis=(0, 2))
    out = {"plan": "PLAN_calendar_ctx_2026-11-08.md (55104e4)", "networks": len(T), "calendar_days": nd, "replicates": nrep, "seed": seed,
           "observed": {"H1_ctx_minus_P3_pp": round((tot[1] - tot[3]) / tot[0] * 100, 3), "H1_ratio": round((tot[1] + .5) / (tot[3] + .5), 4),
                        "H2_ctx_minus_c05_pp": round((tot[1] - tot[2]) / tot[0] * 100, 3), "H2_ratio": round((tot[1] + .5) / (tot[2] + .5), 4)},
           "blocks": {}}
    nn = len(T)
    for L in (1, 7, 14, 28):
        rng = np.random.default_rng(seed); nb = int(np.ceil(nd / L)); h1, h1r, h2, h2r = [], [], [], []
        for start in range(0, nrep, 1000):
            m = min(1000, nrep - start); W = np.zeros((m, nd))
            st = rng.integers(0, nd, (m, nb)); idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(m, -1)[:, :nd] % nd
            for j in range(m): np.add.at(W[j], idx[j], 1)
            V = np.zeros((m, nn)); nets = rng.integers(0, nn, (m, nn))
            for j in range(m): np.add.at(V[j], nets[j], 1)
            Tt = np.einsum("rn,nkd,rd->rk", V, C, W)
            h1.append((Tt[:, 1] - Tt[:, 3]) / np.maximum(Tt[:, 0], 1) * 100); h1r.append((Tt[:, 1] + .5) / (Tt[:, 3] + .5))
            h2.append((Tt[:, 1] - Tt[:, 2]) / np.maximum(Tt[:, 0], 1) * 100); h2r.append((Tt[:, 1] + .5) / (Tt[:, 2] + .5))
        q = lambda v: [round(float(np.percentile(np.concatenate(v), 2.5)), 3), round(float(np.percentile(np.concatenate(v), 97.5)), 3)]
        b = {"H1_diff_ci95_pp": q(h1), "H1_ratio_ci95": q(h1r), "H2_diff_ci95_pp": q(h2), "H2_ratio_ci95": q(h2r)}
        b["H1_met_margin3"] = b["H1_diff_ci95_pp"][1] <= 3.0; b["H1_ratio_met"] = b["H1_ratio_ci95"][1] <= 1.5
        b["H2_fewer_than_c05"] = b["H2_diff_ci95_pp"][1] < 0
        out["blocks"][f"{L}d"] = b
    dump("calendar_ctx", out); print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- 4. high-resolution Holm / BY
def pboot(nets, pa, pb, h0, n, seed=7):
    names = sorted(nets); rng = np.random.default_rng(seed); per = {}
    for k in names:
        days, assoc, act = nets[k]; ud = np.array(sorted(set(days)))
        per[k] = (ud, {d: np.flatnonzero((days == d) & assoc) for d in ud}, np.asarray(act[pa]) == "D", np.asarray(act[pb]) == "D")
    v = []
    for _ in range(n):
        na = da = db = 0.0
        for k in rng.choice(names, len(names)):
            ud, idx, A, B = per[k]; sel = rng.choice(ud, len(ud)); ids = np.concatenate([idx[x] for x in sel])
            if len(ids): na += len(ids); da += A[ids].sum(); db += B[ids].sum()
        if na: v.append((da - db) / na * 100)
    v = np.array(v)
    return {"resamples": len(v), "ci95_pp": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)],
            "p_one_sided": float(((v >= h0).sum() + 1) / (len(v) + 1))}


def holm_by(p):
    keys = sorted(p, key=lambda k: p[k]); m = len(keys); holm = {}; run = 0.0
    for i, k in enumerate(keys): run = max(run, min(1.0, (m - i) * p[k])); holm[k] = run
    c = sum(1.0 / i for i in range(1, m + 1)); by = {}; run = 1.0
    for i in range(m - 1, -1, -1):
        k = keys[i]; run = min(run, min(1.0, p[k] * m * c / (i + 1))); by[k] = run
    return holm, by


CHUNK = 1000


def _pooled_chunk(args):
    src, pa, pb, h0, seed = args
    if src == "r33":
        nets = nets_of(reviewed33())
    else:
        nets = {x["net"]: (x["day"], x["assoc"], x["act"]) for x in t1()["t1"]}
    names = sorted(nets); rng = np.random.default_rng(seed); per = {}
    for k in names:
        days, assoc, act = nets[k]; ud = np.array(sorted(set(days)))
        per[k] = (ud, {d: np.flatnonzero((days == d) & assoc) for d in ud}, np.asarray(act[pa]) == "D", np.asarray(act[pb]) == "D")
    v = []
    for _ in range(CHUNK):
        na = da = db = 0.0
        for k in rng.choice(names, len(names)):
            ud, idx, A, B = per[k]; sel = rng.choice(ud, len(ud)); ids = np.concatenate([idx[x] for x in sel])
            if len(ids): na += len(ids); da += A[ids].sum(); db += B[ids].sum()
        if na: v.append((da - db) / na * 100)
    return v


def _net_day(args):
    k, p, n = args
    v = reviewed33()[k]
    return k, p, v2.day_boot(v["days"], np.asarray(v["assoc"], bool), np.asarray(v["act"][p]), np.asarray(v["act"]["P3"]), n=n)["p_one_sided_H0_ge_margin"]


def holm_hires(n=20000):
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time(); R = reviewed33(); fam, detail = {}, {}
    pooled = [("reviewed_pooled:" + p, "r33", p, "P3", 3.0) for p in POL] + \
             [("ctx_T1:H1_vs_P3", "t1", "CG-ctx", "P3", 3.0), ("ctx_T1:H2_vs_c05", "t1", "CG-ctx", "CG_c05", 0.0)]
    nch = n // CHUNK
    with ProcessPoolExecutor(max_workers=min(30, os.cpu_count() or 4)) as ex:
        futs = {key: [ex.submit(_pooled_chunk, (src, pa, pb, h0, 7 + i)) for i in range(nch)] for key, src, pa, pb, h0 in pooled}
        nf = [ex.submit(_net_day, (k, p, n)) for k in R for p in POL]
        for key, src, pa, pb, h0 in pooled:
            v = np.concatenate([f.result() for f in futs[key]])
            r = {"resamples": int(len(v)), "seeds": f"7..{7 + nch - 1} ({CHUNK} each)",
                 "ci95_pp": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)],
                 "p_one_sided": float(((v >= h0).sum() + 1) / (len(v) + 1)), "H0": f"difference >= {h0}"}
            fam[key] = r["p_one_sided"]; detail[key] = r; print(key, r, round(time.time() - t0), flush=True)
        for f in nf:
            k, p, pv = f.result(); fam[f"reviewed_net:{k}:{p}"] = pv
    print("per-network done", round(time.time() - t0), flush=True)
    cp = json.load(open(os.path.join(root, "results", "posthoc", "review_posthoc.json")))["7_multiplicity"]["rows"]
    for row in cp: fam["earlier9:" + row["test"]] = row["p_one_sided"]
    holm, by = holm_by(fam); met = [k for k, x in fam.items() if x <= 0.025]
    out = {"plan": "PLAN_holm_hires_2026-11-08.md (55104e4)", "resamples": n, "alpha_one_sided": 0.025, "family_size": len(fam),
           "min_resolvable_p": round(1 / (n + 1), 6), "holm_first_threshold": round(0.025 / len(fam), 6),
           "met_unadjusted": len(met), "met_after_holm": sum(holm[k] <= 0.025 for k in met), "met_after_BY": sum(by[k] <= 0.025 for k in met),
           "key": {k: {**detail[k], "holm": round(holm[k], 5), "BY": round(by[k], 5)} for k in detail},
           "earlier9": {k: {"p": fam[k], "holm": round(holm[k], 5), "BY": round(by[k], 5)} for k in fam if k.startswith("earlier9:")},
           "per_network_met_after_holm": sorted(k for k in fam if k.startswith("reviewed_net:") and holm[k] <= 0.025),
           "wall_seconds": round(time.time() - t0), "machine": __import__("platform").node(),
           "processes": min(30, os.cpu_count() or 4)}
    dump("holm_hires", out); print(json.dumps({k: out[k] for k in out if k not in ("earlier9",)}, indent=1))


# ---------------------------------------------------------------- 1. learned baselines with a reject band
def feats(x):
    cols = []
    for r in range(3):
        s = x["S"][r] if r < len(x["S"]) else np.full(len(x["snr"]), "MISSING", dtype=object)
        cols += [(s == "YES").astype(float), (s == "NO").astype(float)]
    cols += [np.where(x["ok"], np.clip(x["snr"], 0, 40) / 40, 0.0), x["ok"].astype(float)]
    return np.column_stack(cols)


def learned():
    import warnings; warnings.filterwarnings("ignore")
    bm = _load("bml_r2", os.path.join(here, "baselines_ml_llm.py")); M = bm.make_models()
    D = t1(); tr = D["train"]; T = D["t1"]
    X = np.vstack([feats(x) for x in tr]); y = np.concatenate([x["assoc"] for x in tr]); src = np.concatenate([[x["net"]] * len(x["snr"]) for x in tr])
    c05 = np.concatenate([x["act"]["CG_c05"] for x in tr])
    tgt_dis = float(((c05 == "D") & y).sum() / y.sum()); tgt_esc = float((c05 == "E").mean())
    out = {"plan": "PLAN_learned_rejectband_2026-11-08.md (55104e4)", "training": {"sets": sorted(set(src)), "episodes": int(len(y)),
           "associated": int(y.sum()), "CG_c05_dismissed_assoc_share": round(tgt_dis, 4), "CG_c05_escalation_share": round(tgt_esc, 4)},
           "models": {}}
    data = {x["net"]: (x["day"], x["assoc"], dict(x["act"])) for x in T}
    for name, mk in M.items():
        oof = np.zeros(len(y))
        for s in np.unique(src):
            m = src == s; oof[m] = mk().fit(X[~m], y[~m]).predict_proba(X[m])[:, 1]
        pa = np.sort(oof[y]); tD = float(np.quantile(oof[y], tgt_dis)) if tgt_dis > 0 else -1.0
        # tA: escalation share (tD < p < tA) on training equals CG c = 0.5's
        cand = np.unique(np.round(oof, 6)); best = None
        for t in cand[cand > tD]:
            e = float(((oof > tD) & (oof < t)).mean())
            if best is None or abs(e - tgt_esc) < abs(best[1] - tgt_esc): best = (float(t), e)
        tA = best[0]
        tr_act = np.full(len(y), "E", dtype=object); tr_act[oof <= tD] = "D"; tr_act[oof >= tA] = "A"
        fit = mk().fit(X, y)
        for x in T:
            p = fit.predict_proba(feats(x))[:, 1]; a = np.full(len(p), "E", dtype=object); a[p <= tD] = "D"; a[p >= tA] = "A"
            data[x["net"]][2][name] = a
        out["models"][name] = {"theta_D": round(tD, 6), "theta_A": round(tA, 6),
                               "training_oof": {"dismissed_assoc_share": round(float(((tr_act == "D") & y).sum() / y.sum()), 4),
                                                "escalation_share": round(float((tr_act == "E").mean()), 4)}}
    days = sum(len(set(x["day"])) for x in T)
    tally = {}
    for k in ("P3", "CG_c05", "CG-D", "CG-ctx", "LR", "GB", "MLP"):
        tally[k] = {"dismissed_assoc": int(sum(((v[2][k] == "D") & v[1]).sum() for v in data.values())),
                    "unassoc_alerts": int(sum(((v[2][k] == "A") & ~v[1]).sum() for v in data.values())),
                    "escalations": int(sum((v[2][k] == "E").sum() for v in data.values()))}
        tally[k]["escalations_per_network_day"] = round(tally[k]["escalations"] / days, 2)
        tally[k]["unassoc_alerts_per_network_day"] = round(tally[k]["unassoc_alerts"] / days, 3)
    out["T1"] = {"networks": len(T), "network_days_with_episodes": days, "associated": int(sum(v[1].sum() for v in data.values())), "counts": tally}
    for name in ("LR", "GB", "MLP"):
        out["models"][name]["minus_P3"] = {x: v2.cluster_boot(data, name, "P3")[x] for x in KEEP}
        out["models"][name]["minus_CG_c05"] = {x: v2.cluster_boot(data, name, "CG_c05")[x] for x in KEEP}
    dump("learned_rejectband", out); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"undefined_snr": undefined_snr, "margin_cost": margin_cost, "threshold_table": threshold_table, "build_t1": build_t1,
     "calendar_ctx": calendar_ctx, "holm_hires": holm_hires, "learned": learned}[sys.argv[1]]()
