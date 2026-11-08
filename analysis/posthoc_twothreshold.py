"""PLAN_TWOTHRESHOLD_2026-11-08.md (pushed 92f6764 before computing), post hoc, descriptive.

1. Two-threshold P3 (tD <= tA) frontier on the 33 reviewed networks, matched to the escalation budget of CG c = 0.5 / CG-D.
2. CG c = 0.5 with the alert threshold theta_A varied (all else frozen).
3. Analyst items (alerts + escalations) and queue precision for P1, P1t, P3, CG, CG-D, CG c = 0.5.
Output: results/posthoc/twothreshold.json
"""
import os, sys, json
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); sys.path.insert(0, here)
from posthoc_collect import collect, _load
v2 = _load("v2t", os.path.join(here, "v2_networks.py"))


def cg(S, snr, ok, c, theta_a):
    S = S[:3]; n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for r, s in enumerate(S):
        q = np.isin(s, ["YES", "NO"]).astype(float); q = np.where(s == "NO", c, q)
        num += v2.W_RANK[r] * (s == "YES") * q; den += v2.W_RANK[r] * q
    num += v2.W_SNR * np.clip(snr / 30, 0, 1) * ok; den += v2.W_SNR * ok
    dd = den >= v2.DELTA; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(n, "E", dtype=object); a[dd & (D >= theta_a)] = "A"; a[dd & (D <= v2.THETA_D)] = "D"; return a


def anyyes(S):
    y = np.zeros(len(S[0]), bool)
    for s in S[:3]: y |= s == "YES"
    return y


def p3_2t(S, snr, ok, td, ta):
    y = anyyes(S); a = np.full(len(snr), "E", dtype=object)
    a[y & ok & (snr >= ta)] = "A"; a[(~y) & ok & (snr < td)] = "D"; return a


def p1(S, snr, ok):
    return np.where(anyyes(S), "A", "D").astype(object)


def p1t(S, snr, ok, t=8.0):
    return np.where(anyyes(S) | (ok & (snr >= t)), "A", "D").astype(object)


def rates(rows, nets, acts):
    days = sum(rows[k]["calendar_days"] for k in nets)
    E = sum(int((acts[k] == "E").sum()) for k in nets); A = sum(int((acts[k] == "A").sum()) for k in nets)
    Aa = sum(int(((acts[k] == "A") & rows[k]["assoc"]).sum()) for k in nets)
    Ea = sum(int(((acts[k] == "E") & rows[k]["assoc"]).sum()) for k in nets)
    Da = sum(int(((acts[k] == "D") & rows[k]["assoc"]).sum()) for k in nets)
    return {"escalations": E, "escalations_per_network_day": round(E / days, 3), "alerts": A,
            "unassociated_alerts": A - Aa, "unassociated_alerts_per_network_day": round((A - Aa) / days, 3),
            "dismissed_associated": Da, "items_alerts_plus_escalations": A + E,
            "items_per_network_day": round((A + E) / days, 2),
            "item_precision_pct": round(100 * (Aa + Ea) / max(A + E, 1), 2)}


def main():
    rows = collect("reviewed"); nets = sorted(k for k, v in rows.items() if v["included"])
    R = lambda f: {k: f(rows[k]) for k in nets}
    for k in nets:  # self-checks
        r = rows[k]
        assert (cg(r["S"], r["snr"], r["ok"], 0.5, v2.THETA_A) == r["act"]["CG_c05"]).all(), k
        assert (cg(r["S"], r["snr"], r["ok"], 1.0, v2.THETA_A) == r["act"]["CG"]).all(), k
        assert (p3_2t(r["S"], r["snr"], r["ok"], 7.5, 7.5) == r["act"]["P3"]).all(), k
        assert (p1(r["S"], r["snr"], r["ok"]) == r["act"]["P1"]).all(), k
    out = {"status": "post hoc, method fixed in PLAN_TWOTHRESHOLD_2026-11-08.md (92f6764) before computing; descriptive",
           "networks": len(nets), "network_days": sum(rows[k]["calendar_days"] for k in nets)}
    frozen = {p: rates(rows, nets, R(lambda r, p=p: r["act"][p])) for p in ("P1", "P3", "CG", "CG-D", "CG_c05")}
    frozen["P1t_8.0"] = rates(rows, nets, R(lambda r: p1t(r["S"], r["snr"], r["ok"])))
    out["analyst_items"] = frozen
    # 1. two-threshold P3 frontier
    grid = []; acts2 = {}
    for td in np.arange(5.0, 12.01, 0.5):
        for ta in np.arange(td, 20.01, 0.5):
            a = R(lambda r, td=td, ta=ta: p3_2t(r["S"], r["snr"], r["ok"], td, ta)); key = f"{td:.1f}/{ta:.1f}"
            acts2[key] = a; grid.append({"tD_tA": key, **rates(rows, nets, a)})
    out["P3_two_threshold_grid_points"] = len(grid)
    out["matched"] = {}
    for name in ("CG_c05", "CG-D"):
        f = frozen[name]; e = f["escalations_per_network_day"]
        cand = [g for g in grid if abs(g["escalations_per_network_day"] - e) <= 0.05 * e and g["dismissed_associated"] <= f["dismissed_associated"]]
        rec = {"target": f, "candidates_within_5pct_and_no_more_dismissals": len(cand)}
        if cand:
            best = min(cand, key=lambda g: g["unassociated_alerts"]); rec["best_P3_2t"] = best
            d = {k: (rows[k]["days"], rows[k]["assoc"], {"X": rows[k]["act"][name], "Y": acts2[best["tD_tA"]][k]}) for k in nets}
            rec["dismissed_diff_policy_minus_P3_2t"] = v2.cluster_boot(d, "X", "Y")
            rec["unassoc_alert_reduction_pct"] = round(100 * (1 - f["unassociated_alerts"] / max(best["unassociated_alerts"], 1)), 1)
        # also the best P3-2t at the budget regardless of the dismissal constraint (for transparency)
        cand2 = [g for g in grid if abs(g["escalations_per_network_day"] - e) <= 0.05 * e]
        if cand2: rec["fewest_alerts_at_budget_any_dismissals"] = min(cand2, key=lambda g: g["unassociated_alerts"])
        out["matched"][name] = rec
    # Pareto frontier (escalations, dismissed, unassociated alerts) of P3-2t, compact
    pts = sorted(grid, key=lambda g: (g["escalations"], g["dismissed_associated"], g["unassociated_alerts"]))
    front = []
    for g in pts:
        if not any(h["escalations"] <= g["escalations"] and h["dismissed_associated"] <= g["dismissed_associated"]
                   and h["unassociated_alerts"] <= g["unassociated_alerts"] and h is not g and
                   (h["escalations"], h["dismissed_associated"], h["unassociated_alerts"]) != (g["escalations"], g["dismissed_associated"], g["unassociated_alerts"]) for h in pts):
            front.append(g)
    out["P3_two_threshold_pareto"] = front
    # does any P3-2t point dominate CG_c05 / CG-D on all three?
    for name in ("CG_c05", "CG-D"):
        f = frozen[name]
        dom = [g for g in grid if g["escalations"] <= f["escalations"] and g["dismissed_associated"] <= f["dismissed_associated"] and g["unassociated_alerts"] <= f["unassociated_alerts"]]
        out["matched"][name]["P3_2t_points_dominating_on_all_three"] = len(dom)
        if dom: out["matched"][name]["example_dominating"] = min(dom, key=lambda g: g["unassociated_alerts"])
    # 2. theta_A separation
    out["CG_c05_thetaA"] = {f"{ta:.2f}": rates(rows, nets, R(lambda r, ta=ta: cg(r["S"], r["snr"], r["ok"], 0.5, ta)))
                            for ta in np.arange(0.40, 0.901, 0.05)}
    json.dump(out, open(os.path.join(root, "results", "posthoc", "twothreshold.json"), "w"), indent=1,
              default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    for p, v in frozen.items(): print("ITEMS", p, v)
    for n, v in out["matched"].items(): print("MATCH", n, json.dumps(v)[:900])
    for t, v in out["CG_c05_thetaA"].items(): print("thA", t, v["escalations_per_network_day"], v["dismissed_associated"], v["unassociated_alerts_per_network_day"])


if __name__ == "__main__":
    main()
