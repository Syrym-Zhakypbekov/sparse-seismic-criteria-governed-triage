"""PLAN_REVIEW4_2026-11-08.md (pushed a0ea136 before computing), post hoc, descriptive."""
import os, sys, json
import numpy as np
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); sys.path.insert(0, here)
from posthoc_collect import collect, _load
v2 = _load("v2r4", os.path.join(here, "v2_networks.py"))
OUT = os.path.join(root, "results", "review4"); os.makedirs(OUT, exist_ok=True)
A_NETS = [c["network"] for c in json.load(open(os.path.join(root, "results", "v2", "networks.json")))["networks"]]
B_NETS = [c["network"] for c in json.load(open(os.path.join(root, "results", "v2", "networks_batchB.json")))["networks"]]
POL = ("CG", "CG_c05", "CG-D")


def tot(rows, nets, A):
    r = {"dismissed_reviewed_associated": 0, "escalations": 0, "unassociated_alerts": 0, "all_dismissals": 0, "alerts": 0}
    for k in nets:
        a = A[k]; s = rows[k]["assoc"]
        r["dismissed_reviewed_associated"] += int(((a == "D") & s).sum()); r["escalations"] += int((a == "E").sum())
        r["unassociated_alerts"] += int(((a == "A") & ~s).sum()); r["all_dismissals"] += int((a == "D").sum()); r["alerts"] += int((a == "A").sum())
    r["alerts_plus_escalations"] = r["alerts"] + r["escalations"]; return r


def p3_2t(S, snr, ok, td, ta):
    y = np.zeros(len(snr), bool)
    for s in S[:3]: y |= s == "YES"
    a = np.full(len(snr), "E", dtype=object); a[y & ok & (snr >= ta)] = "A"; a[(~y) & ok & (snr < td)] = "D"; return a


def main():
    rows = {k: v for k, v in collect("reviewed").items() if v.get("included")}
    nets = sorted(rows)
    for k in nets:
        rows[k]["S"] = [np.asarray(s, object) for s in rows[k]["S"][:3]]
        act = v2.policies(rows[k]["S"], rows[k]["snr"], rows[k]["ok"])
        for p in POL + ("P3",): assert (act[p] == rows[k]["act"][p]).all(), (k, p)
    # 1. delta sweep
    frozen = {k: rows[k]["act"] for k in nets}; ds = {}
    for d in (0.45, 0.55, 0.60, 0.65, 0.75, 0.85, 0.95):
        v2.DELTA = d; A = {k: v2.policies(rows[k]["S"], rows[k]["snr"], rows[k]["ok"]) for k in nets}; rec = {}
        for p in POL:
            t = tot(rows, nets, {k: A[k][p] for k in nets})
            t["decisions_changed_vs_frozen"] = int(sum((A[k][p] != frozen[k][p]).sum() for k in nets))
            t["reviewed_associated_decisions_changed"] = int(sum(((A[k][p] != frozen[k][p]) & rows[k]["assoc"]).sum() for k in nets))
            rec[p] = t
        ds[f"{d:.2f}"] = rec
    v2.DELTA = 0.45
    json.dump({"plan": "PLAN_REVIEW4_2026-11-08.md (a0ea136)", "networks": len(nets),
               "episodes": int(sum(len(rows[k]["snr"]) for k in nets)), "by_delta": ds},
              open(os.path.join(OUT, "delta_sweep.json"), "w"), indent=1)
    # 2. development-chosen two-threshold P3
    trn = [k for k in nets if k in A_NETS]; tst = [k for k in nets if k in B_NETS]
    c05_tr = tot(rows, trn, {k: rows[k]["act"]["CG_c05"] for k in trn}); grid = []
    for td in np.arange(5.0, 12.01, 0.5):
        for ta in np.arange(td, 20.01, 0.5):
            t = tot(rows, trn, {k: p3_2t(rows[k]["S"], rows[k]["snr"], rows[k]["ok"], td, ta) for k in trn})
            grid.append({"tD": round(float(td), 1), "tA": round(float(ta), 1), **t})
    e = c05_tr["escalations"]
    ok = [g for g in grid if abs(g["escalations"] - e) <= 0.05 * e and g["dismissed_reviewed_associated"] <= c05_tr["dismissed_reviewed_associated"]]
    choice = min(ok, key=lambda g: g["unassociated_alerts"]) if ok else min(grid, key=lambda g: abs(g["escalations"] - e))
    res = {"plan": "PLAN_REVIEW4_2026-11-08.md (a0ea136)", "training_networks": trn, "test_networks": tst,
           "training_CG_c05": c05_tr, "candidates_meeting_rule": len(ok), "chosen": choice}
    for name, set_ in (("test_batchB", tst), ("all_33_secondary", nets)):
        act = {k: dict(rows[k]["act"], P3_2t_dev=p3_2t(rows[k]["S"], rows[k]["snr"], rows[k]["ok"], choice["tD"], choice["tA"])) for k in set_}
        days = {k: sum(1 for _ in [0]) for k in set_}
        out = {p: tot(rows, set_, {k: act[k][p] for k in set_}) for p in ("P3", "P3_2t_dev", "CG", "CG_c05", "CG-D")}
        nd = sum(rows[k]["calendar_days"] for k in set_)
        for p in out: out[p]["unassociated_alerts_per_network_day"] = round(out[p]["unassociated_alerts"] / nd, 3); out[p]["escalations_per_network_day"] = round(out[p]["escalations"] / nd, 3)
        data = {k: (rows[k]["days"], rows[k]["assoc"], act[k]) for k in set_}
        out["CG_c05_minus_P3_2t_dev"] = v2.cluster_boot(data, "CG_c05", "P3_2t_dev")
        out["CG-D_minus_P3_2t_dev"] = v2.cluster_boot(data, "CG-D", "P3_2t_dev")
        out["network_days"] = nd
        res[name] = out
    json.dump(res, open(os.path.join(OUT, "dev_two_threshold.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps({d: {p: (v[p]["reviewed_associated_decisions_changed"], v[p]["decisions_changed_vs_frozen"], v[p]["escalations"]) for p in POL} for d, v in ds.items()}))
    print("CHOICE", choice, "cands", len(ok))
    for n in ("test_batchB", "all_33_secondary"):
        print(n, json.dumps({p: res[n][p] for p in ("P3", "P3_2t_dev", "CG_c05", "CG-D")}))
        print(n, "diff c05", json.dumps(res[n]["CG_c05_minus_P3_2t_dev"])[:300]); print(n, "diff CGD", json.dumps(res[n]["CG-D_minus_P3_2t_dev"])[:300])


if __name__ == "__main__":
    main()
