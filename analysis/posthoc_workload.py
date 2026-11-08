"""PLAN_WORKLOAD_2026-11-08.md (pushed 5e1863c before computing): analyst workload and cost-matched comparison, post hoc.

Frozen operating points (P1, P3, CG, CG-D, CG c = 0.5): escalations per day, analyst minutes per day (2 min/escalation),
automatic alerts per day and their associated share, dismissed associated episodes - per network and pooled
(totals / network-days), for the 33 reviewed-included networks (reviewed labels) and the 38 catalogue-included networks.
Sweep: CG family with c in 0..1 step 0.1, P3 family with SNR threshold 5..12 dB step 0.5 (decision rules otherwise frozen,
recomputed here and self-checked against the frozen CG, CG c = 0.5 and P3 actions). Matched pairs: P3 threshold with the
closest pooled escalations per network-day to CG c = 0.5 and to CG-D; difference by v2_networks.cluster_boot.
Output: results/posthoc/workload.json, figures/fig6_workload.png (600 dpi).
"""
import os, sys, json
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); sys.path.insert(0, here)
from posthoc_collect import collect, _load
v2 = _load("v2w", os.path.join(here, "v2_networks.py"))
POL = ["P1", "P3", "CG", "CG-D", "CG_c05"]; MIN_PER_ESC = 2.0
C_GRID = [round(0.1 * i, 1) for i in range(11)]; T_GRID = [5.0 + 0.5 * i for i in range(15)]


def cg_c(S, snr, ok, c):
    S = S[:3]; n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for r, s in enumerate(S):
        q = np.isin(s, ["YES", "NO"]).astype(float); q = np.where(s == "NO", c, q)
        num += v2.W_RANK[r] * (s == "YES") * q; den += v2.W_RANK[r] * q
    num += v2.W_SNR * np.clip(snr / 30, 0, 1) * ok; den += v2.W_SNR * ok
    dd = den >= v2.DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(n, "E", dtype=object); a[dd & (D >= v2.THETA_A)] = "A"; a[dd & (D <= v2.THETA_D)] = "D"; return a


def p3_t(S, snr, ok, t):
    yes = np.zeros(len(snr), bool)
    for s in S[:3]: yes |= s == "YES"
    a = np.full(len(snr), "E", dtype=object); a[yes & ok & (snr >= t)] = "A"; a[(~yes) & ok & (snr < t)] = "D"; return a


def rates(rows, nets, acts):
    """acts: {net: action array}. Pooled over nets."""
    days = sum(rows[k]["calendar_days"] for k in nets)
    E = sum(int((acts[k] == "E").sum()) for k in nets); A = sum(int((acts[k] == "A").sum()) for k in nets)
    Aa = sum(int(((acts[k] == "A") & rows[k]["assoc"]).sum()) for k in nets)
    na = sum(int(rows[k]["assoc"].sum()) for k in nets); Da = sum(int(((acts[k] == "D") & rows[k]["assoc"]).sum()) for k in nets)
    Ua = A - Aa
    return {"escalations": E, "escalations_per_network_day": round(E / days, 2), "analyst_min_per_network_day": round(MIN_PER_ESC * E / days, 1),
            "alerts": A, "alerts_per_network_day": round(A / days, 2), "alert_associated_share_pct": round(100 * Aa / max(A, 1), 1),
            "unassociated_alerts_per_network_day": round(Ua / days, 2),
            "dismissed_associated": Da, "dismissed_associated_share_pct": round(100 * Da / max(na, 1), 2)}


def frozen(rows, nets):
    per = {}
    for k in nets:
        r = rows[k]; nd = r["calendar_days"]
        per[k] = {"calendar_days": nd, "associated": int(r["assoc"].sum()),
                  **{p: {"escalations_per_day": round(float((r["act"][p] == "E").sum()) / nd, 2),
                         "analyst_min_per_day": round(MIN_PER_ESC * float((r["act"][p] == "E").sum()) / nd, 1),
                         "alerts_per_day": round(float((r["act"][p] == "A").sum()) / nd, 2),
                         "dismissed_associated": int(((r["act"][p] == "D") & r["assoc"]).sum())} for p in POL}}
    pooled = {p: rates(rows, nets, {k: rows[k]["act"][p] for k in nets}) for p in POL}
    med = {p: {"median_min_per_day": round(float(np.median([per[k][p]["analyst_min_per_day"] for k in nets])), 1),
               "max_min_per_day": max(per[k][p]["analyst_min_per_day"] for k in nets)} for p in POL}
    return {"networks": len(nets), "network_days": sum(rows[k]["calendar_days"] for k in nets), "pooled": pooled,
            "per_network_summary": med, "per_network": per}


def run(labels):
    rows = collect(labels); nets = sorted(k for k, v in rows.items() if v["included"])
    out = {"labels": labels, "frozen_operating_points": frozen(rows, nets)}
    if labels != "reviewed": return out
    # self-check of the recomputed families
    for k in nets:
        r = rows[k]
        assert (cg_c(r["S"], r["snr"], r["ok"], 1.0) == r["act"]["CG"]).all(), k
        assert (cg_c(r["S"], r["snr"], r["ok"], 0.5) == r["act"]["CG_c05"]).all(), k
        assert (p3_t(r["S"], r["snr"], r["ok"], 7.5) == r["act"]["P3"]).all(), k
    cgf = {c: {k: cg_c(rows[k]["S"], rows[k]["snr"], rows[k]["ok"], c) for k in nets} for c in C_GRID}
    p3f = {t: {k: p3_t(rows[k]["S"], rows[k]["snr"], rows[k]["ok"], t) for k in nets} for t in T_GRID}
    out["sweep_CG_c"] = {str(c): rates(rows, nets, cgf[c]) for c in C_GRID}
    out["sweep_P3_t"] = {str(t): rates(rows, nets, p3f[t]) for t in T_GRID}
    out["matched"] = {}
    for name in ("CG_c05", "CG-D"):
        target = out["frozen_operating_points"]["pooled"][name]["escalations_per_network_day"]
        t = min(T_GRID, key=lambda x: abs(out["sweep_P3_t"][str(x)]["escalations_per_network_day"] - target))
        d = {k: (rows[k]["days"], rows[k]["assoc"], {"X": rows[k]["act"][name], "Y": p3f[t][k]}) for k in nets}
        out["matched"][name] = {"P3_threshold_dB": t, "escalations_per_network_day": {name: target, f"P3_{t}": out["sweep_P3_t"][str(t)]["escalations_per_network_day"]},
                                "policy": out["frozen_operating_points"]["pooled"][name], f"P3_{t}": out["sweep_P3_t"][str(t)],
                                "dismissed_associated_diff_vs_matched_P3": v2.cluster_boot(d, "X", "Y")}
    # description of the two operating curves at equal analyst minutes (linear interpolation of the P3 curve; points of
    # the CG family outside the P3 range are not compared)
    P3s = out["sweep_P3_t"]; x = np.array([v["analyst_min_per_network_day"] for v in P3s.values()]); o = np.argsort(x)
    ip = lambda key, m: float(np.interp(m, x[o], np.array([v[key] for v in P3s.values()])[o]))
    out["equal_minutes_curve_comparison"] = {}
    for c, v in out["sweep_CG_c"].items():
        m = v["analyst_min_per_network_day"]
        if not (x.min() <= m <= x.max()): continue
        d3, u3 = ip("dismissed_associated_share_pct", m), ip("unassociated_alerts_per_network_day", m)
        out["equal_minutes_curve_comparison"][c] = {"analyst_min_per_network_day": m, "dismissed_pct_CG": v["dismissed_associated_share_pct"],
                                                    "dismissed_pct_P3_curve": round(d3, 2), "dismissed_diff_pp": round(v["dismissed_associated_share_pct"] - d3, 2),
                                                    "unassoc_alerts_CG": v["unassociated_alerts_per_network_day"], "unassoc_alerts_P3_curve": round(u3, 2),
                                                    "unassoc_alert_reduction_pct": round(100 * (1 - v["unassociated_alerts_per_network_day"] / u3), 1)}
    return out


def figure(res, fn):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    w = res["reviewed"]; fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for key, lab, col, mk in (("sweep_CG_c", "CG family (c = 0 ... 1)", "#A42421", "o"), ("sweep_P3_t", "P3 family (5 ... 12 dB)", "#595959", "s")):
        xs = [v["analyst_min_per_network_day"] for v in w[key].values()]
        axes[0].plot(xs, [v["dismissed_associated_share_pct"] for v in w[key].values()], mk + "-", color=col, ms=4, label=lab)
        axes[1].plot(xs, [v["unassociated_alerts_per_network_day"] for v in w[key].values()], mk + "-", color=col, ms=4, label=lab)
    fp = w["frozen_operating_points"]["pooled"]
    for p, col in (("CG", "#A42421"), ("CG-D", "#1f77b4"), ("CG_c05", "#ff7f0e"), ("P3", "#000000")):
        for ax, y in ((axes[0], "dismissed_associated_share_pct"), (axes[1], "unassociated_alerts_per_network_day")):
            ax.plot(fp[p]["analyst_min_per_network_day"], fp[p][y], "*", ms=12, color=col, label={"CG_c05": "CG c = 0.5"}.get(p, p) if ax is axes[0] else None)
    axes[0].set_xlabel("analyst minutes per network-day (2 min / escalation)"); axes[0].set_ylabel("dismissed reviewed-associated (%)")
    axes[1].set_xlabel("analyst minutes per network-day (2 min / escalation)"); axes[1].set_ylabel("automatic alerts not associated, per network-day")
    axes[0].legend(fontsize=7); fig.tight_layout(); fig.savefig(fn, dpi=600); plt.close(fig)


if __name__ == "__main__":
    res = {"status": "post hoc, method fixed in PLAN_WORKLOAD_2026-11-08.md (5e1863c) before computing; descriptive",
           "minutes_per_escalation": MIN_PER_ESC, "reviewed": run("reviewed"), "catalogue": run("catalogue")}
    json.dump(res, open(os.path.join(root, "results", "posthoc", "workload.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    figure(res, os.path.join(root, "figures", "fig6_workload.png"))
    for lab in ("reviewed", "catalogue"):
        f = res[lab]["frozen_operating_points"]; print("==", lab, f["networks"], "networks", f["network_days"], "network-days")
        for p in POL: print(p, f["pooled"][p], f["per_network_summary"][p])
    for k, v in res["reviewed"]["matched"].items():
        print("MATCHED", k, v["P3_threshold_dB"], v["escalations_per_network_day"], v["dismissed_associated_diff_vs_matched_P3"])
    for c, v in res["reviewed"]["sweep_CG_c"].items(): print("c", c, v["analyst_min_per_network_day"], v["dismissed_associated_share_pct"], v["unassociated_alerts_per_network_day"])
    for t, v in res["reviewed"]["sweep_P3_t"].items(): print("t", t, v["analyst_min_per_network_day"], v["dismissed_associated_share_pct"], v["unassociated_alerts_per_network_day"])
