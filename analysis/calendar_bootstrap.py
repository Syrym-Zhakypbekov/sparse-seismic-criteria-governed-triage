"""Post hoc (08.11.2026, internal review v30).

Two analyses of the pooled multi-network sets (reviewed-bulletin test, batch A, batch B, A+B), frozen decision rules:

1. Calendar-dependence bootstrap. The pre-specified two-stage bootstrap resamples networks and then days independently within
   each network. Networks share events and the calendar (all evaluate 2024-01-08 .. 2024-07-07), so here every replicate
   draws networks with replacement and ONE common sequence of calendar-day blocks (circular, block length 1, 7, 14, 28 days)
   that is applied to every drawn network. 10,000 replicates, seed 7. Statistics as pre-specified: pooled difference of
   dismissed associated shares (CG, CG-D, CG c=0.5 minus P3, percentage points) and ratio (D_k + 0.5) / (D_P3 + 0.5).

2. Chance-corrected pooled differences, per policy. The pre-specified shifted-catalogue control (100 shifts of 1-7 days,
   random sign, seed 7, circular in the network's calendar span; analysis/v2_networks.py chance_control) is extended to
   record, for every shift, the chance-associated episodes and the chance-associated dismissals of EACH policy. Pooled
   chance-corrected difference = (sum_n [D_k - D_P3] - sum_n chance[D_k - D_P3]) / (sum_n assoc - sum_n chance assoc).
   Also reported: chance shares among each policy's dismissals.

Usage:  python analysis/calendar_bootstrap.py extract   -> results/posthoc/calendar_bootstrap_inputs.npz + chance_by_policy.json
        python analysis/calendar_bootstrap.py boot      -> results/posthoc/calendar_bootstrap.json (needs only the .npz)
Never writes into results/v2 or results/v2_reviewed.
"""
import os, sys, json, time, importlib.util, platform
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
P = os.path.join(root, "results", "posthoc"); os.makedirs(P, exist_ok=True)
POL = ["CG", "CG-D", "CG_c05", "P3"]
DAY0 = np.datetime64("2024-01-08"); NDAYS = 182
SETS = ["reviewed", "A", "B"]


def extract():
    spec = importlib.util.spec_from_file_location("v2", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
    cur = {}
    orig_cc = v2.chance_control

    def cc(ep, cat, av, act, n=100, seed=v2.SEED):
        r = orig_cc(ep, cat, av, act, n, seed)
        rng = np.random.default_rng(seed); offs = rng.uniform(1, 7, n) * 86400 * rng.choice([-1, 1], n)
        t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy(); pp = cat.p_pred.to_numpy(dtype=float)
        import pandas as pd
        t0 = pd.Timestamp(av.day.min()).timestamp(); span = pd.Timestamp(av.day.max()).timestamp() + 86400 - t0
        rows = []
        for o in offs:
            s = v2.assoc_vec(t0 + np.mod(pp + o - t0, span), t_on, t_off)
            rows.append([s.sum()] + [((act[k] == "D") & s).sum() for k in POL])
        rows = np.array(rows, float).mean(axis=0)
        cur["chance"] = {"assoc": float(rows[0]), **{k: float(rows[i + 1]) for i, k in enumerate(POL)}}
        return r
    v2.chance_control = cc
    store = {s: {} for s in SETS}
    orig_eval = v2.evaluate_network
    target = {"set": None}

    def ev(n, cfg):
        cur.clear()
        r = orig_eval(n, cfg)
        if not isinstance(r, dict) and r[0]["included_in_pooled"]:
            days, assoc, act = r[1]
            di = ((np.array(days, dtype="datetime64[D]") - DAY0).astype(int))
            ok = (di >= 0) & (di < NDAYS)
            C = np.zeros((1 + len(POL), NDAYS))
            np.add.at(C[0], di[ok & assoc], 1)
            for i, k in enumerate(POL):
                np.add.at(C[i + 1], di[ok & assoc & (act[k] == "D")], 1)
            store[target["set"]][n] = {"C": C, "chance": dict(cur.get("chance", {})),
                                       "real": {k: int(((act[k] == "D") & assoc).sum()) for k in POL}, "assoc": int(assoc.sum()),
                                       "outside_period": int((~ok & assoc).sum())}
        return r
    v2.evaluate_network = ev
    for b in ["A", "B"]:
        target["set"] = b; v2.RUN_DIRS[:] = ["runs"]
        cfgs, _, _ = v2.run_list(b)
        for cfg in cfgs: v2.evaluate_network(cfg["network"], cfg)
        print(b, len(store[b]), flush=True)
    target["set"] = "reviewed"; v2.RUN_DIRS[:] = ["runs"]
    spec = importlib.util.spec_from_file_location("vr", os.path.join(here, "v2_reviewed_bulletin.py")); vr = importlib.util.module_from_spec(spec)
    sys.modules["vr"] = vr; spec.loader.exec_module(vr); vr.v2 = v2
    vr.OUT = os.path.join(P, "calendar_bootstrap_reviewed_tmp")
    vr.score()
    print("reviewed", len(store["reviewed"]), flush=True)
    arrays, meta = {}, {}
    for s in SETS:
        names = sorted(store[s]); meta[s] = names
        arrays[s] = np.stack([store[s][n]["C"] for n in names])
    np.savez_compressed(os.path.join(P, "calendar_bootstrap_inputs.npz"), **arrays, meta=json.dumps(meta))
    # chance-corrected pooled differences per policy
    ch = {}
    for s, names in list(meta.items()) + [("A+B", sorted(set(meta["A"]) | set(meta["B"])))]:
        src = {n: (store["A"].get(n) or store["B"].get(n)) if s == "A+B" else store[s][n] for n in names}
        tot_a = sum(v["assoc"] for v in src.values()); tot_ca = sum(v["chance"]["assoc"] for v in src.values())
        o = {"networks": len(names), "assoc": tot_a, "chance_assoc_mean": round(tot_ca, 2), "chance_share_assoc": round(tot_ca / tot_a, 4)}
        for k in ["CG", "CG-D", "CG_c05"]:
            real = sum(v["real"][k] - v["real"]["P3"] for v in src.values())
            chx = sum(v["chance"][k] - v["chance"]["P3"] for v in src.values())
            o[k] = {"raw_pooled_minus_P3_pp": round(real / tot_a * 100, 3),
                    "chance_corrected_pooled_minus_P3_pp": round((real - chx) / max(tot_a - tot_ca, 1) * 100, 3),
                    "dismissed": sum(v["real"][k] for v in src.values()),
                    "chance_dismissed_mean": round(sum(v["chance"][k] for v in src.values()), 2)}
        o["P3"] = {"dismissed": sum(v["real"]["P3"] for v in src.values()),
                   "chance_dismissed_mean": round(sum(v["chance"]["P3"] for v in src.values()), 2)}
        o["per_network"] = {n: {"assoc": v["assoc"], "chance_assoc": round(v["chance"]["assoc"], 2), "dismissed": v["real"],
                                "chance_dismissed": {k: round(v["chance"][k], 2) for k in POL}} for n, v in src.items()}
        ch[s] = o
    json.dump({"status": "post hoc (internal review v30); pre-specified control extended per policy", "sets": ch},
              open(os.path.join(P, "chance_by_policy.json"), "w"), indent=1)
    print(json.dumps({s: {k: ch[s][k] for k in ("networks", "chance_share_assoc", "CG", "CG-D", "CG_c05")} for s in ch}, indent=1))


def boot(nrep=10000, seed=7):
    t = time.time()
    Z = np.load(os.path.join(P, "calendar_bootstrap_inputs.npz")); meta = json.loads(str(Z["meta"]))
    sets = {s: Z[s] for s in SETS}; sets["A+B"] = np.concatenate([Z["A"], Z["B"]])
    out = {"status": "post hoc (internal review v30)", "replicates": nrep, "seed": seed,
           "machine": platform.node(), "python": platform.python_version(), "sets": {}}
    for s, C in sets.items():
        nn = C.shape[0]; tot = C.sum(axis=(0, 2))
        obs = {k: {"diff_pp": round((tot[i + 1] - tot[4]) / tot[0] * 100, 3), "ratio": round((tot[i + 1] + 0.5) / (tot[4] + 0.5), 4)}
               for i, k in enumerate(POL[:3])}
        res = {"networks": int(nn), "assoc": int(tot[0]), "observed": obs, "calendar_joint": {}}
        # small-sample alternative: t-interval over per-network differences (equal network weight)
        T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 12: 2.179,
                15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021}
        tq = T975[max(k for k in T975 if k <= nn - 1)] if nn > 1 else float("nan")
        per = C.sum(axis=2)
        res["equal_weight_t_interval"] = {}
        for i, k in enumerate(POL[:3]):
            d = (per[:, i + 1] - per[:, 4]) / np.maximum(per[:, 0], 1) * 100; m = float(d.mean()); se = float(d.std(ddof=1) / np.sqrt(nn))
            res["equal_weight_t_interval"][k] = {"mean_pp": round(m, 3), "ci95_pp": [round(m - tq * se, 3), round(m + tq * se, 3)], "clusters": int(nn)}
        for L in (1, 7, 14, 28):
            rng = np.random.default_rng(seed)
            nb = int(np.ceil(NDAYS / L)); acc = {k: {"d": [], "r": []} for k in POL[:3]}
            for start in range(0, nrep, 1000):
                m = min(1000, nrep - start)
                W = np.zeros((m, NDAYS))
                st = rng.integers(0, NDAYS, (m, nb))
                idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(m, -1)[:, :NDAYS] % NDAYS
                for j in range(m): np.add.at(W[j], idx[j], 1)
                V = np.zeros((m, nn)); nets = rng.integers(0, nn, (m, nn))
                for j in range(m): np.add.at(V[j], nets[j], 1)
                T = np.einsum("rn,nkd,rd->rk", V, C, W)
                for i, k in enumerate(POL[:3]):
                    acc[k]["d"].append((T[:, i + 1] - T[:, 4]) / np.maximum(T[:, 0], 1) * 100)
                    acc[k]["r"].append((T[:, i + 1] + 0.5) / (T[:, 4] + 0.5))
            res["calendar_joint"][f"block_{L}d"] = {
                k: {"diff_ci95_pp": [round(float(np.percentile(np.concatenate(acc[k]["d"]), 2.5)), 3), round(float(np.percentile(np.concatenate(acc[k]["d"]), 97.5)), 3)],
                    "ratio_ci95": [round(float(np.percentile(np.concatenate(acc[k]["r"]), 2.5)), 4), round(float(np.percentile(np.concatenate(acc[k]["r"]), 97.5)), 4)],
                    "diff_criterion_met": bool(np.percentile(np.concatenate(acc[k]["d"]), 97.5) <= 3.0),
                    "ratio_criterion_met": bool(np.percentile(np.concatenate(acc[k]["r"]), 97.5) <= 1.5)} for k in POL[:3]}
        out["sets"][s] = res
        print(s, json.dumps(res["calendar_joint"]["block_1d"]), flush=True)
    out["wall_seconds"] = round(time.time() - t, 1)
    json.dump(out, open(os.path.join(P, "calendar_bootstrap.json"), "w"), indent=1)
    print("wall", out["wall_seconds"], "s on", out["machine"])


if __name__ == "__main__":
    {"extract": extract, "boot": boot}[sys.argv[1]]()
