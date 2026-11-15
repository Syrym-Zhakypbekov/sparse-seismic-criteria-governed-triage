"""Escalation cost of the evidence-sufficiency condition in the stress test (POST HOC, cold review v34).

Reads the existing stress-test outputs (results/sufficiency/stress.json, thin_subset.json; plan
PLAN_SUFFICIENCY_STRESS_2026-11-08.md, e30842d) and derives, for c = 0.5 and CG-D, delta = 0.45 against delta = 0:
  - automatic decisions on fewer than two evidence sources that delta removes ("thin" automatic decisions),
  - additional escalations, and escalations per removed thin automatic decision,
  - reviewed-associated dismissals avoided, and escalations per avoided reviewed-associated dismissal,
  - automatic alerts without a reviewed event removed, and total automatic dismissals removed.
Masked values are means over the 50 masking seeds, as in Table K1. No new scoring.

Usage: python analysis/sufficiency_cost.py -> results/sufficiency/cost.json
"""
import os, json

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
S = os.path.join(root, "results", "sufficiency")


def cost(r0, r1):
    esc = r1["escalations"] - r0["escalations"]
    thin = r0["auto_thin"] - r1["auto_thin"]
    dis = r0["assoc_dismissed"] - r1["assoc_dismissed"]
    return {"thin_automatic_decisions_removed": round(thin, 2),
            "additional_escalations": round(esc, 2),
            "additional_escalations_pct": round(100 * esc / r0["escalations"], 2),
            "escalations_per_removed_thin_decision": round(esc / thin, 3) if thin else None,
            "reviewed_associated_dismissals_avoided": round(dis, 2),
            "escalations_per_avoided_reviewed_associated_dismissal": round(esc / dis, 1) if dis else None,
            "alerts_without_reviewed_event_removed": round(r0["unassoc_alerts"] - r1["unassoc_alerts"], 2),
            "automatic_dismissals_removed": round(r0["dismissals"] - r1["dismissals"], 2)}


def main():
    st = json.load(open(os.path.join(S, "stress.json"))); th = json.load(open(os.path.join(S, "thin_subset.json")))
    out = {"status": "POST HOC (cold review v34_7f6b540); derived from stress.json and thin_subset.json, no new scoring",
           "reviewed_associated": st["reviewed_associated"], "masked": {}, "real_thin_subset": {}}
    for mode in ("independent", "correlated"):
        r = st["modes"][mode]["0.5"]["rules"]
        out["masked"][mode + "_p0.5"] = {pol: cost(r[pol + "|0.0"], r[pol + "|0.45"]) for pol in ("CG_c05", "CG-D")}
    r = th["rules"]
    out["real_thin_subset"] = {"episodes": th["episodes"], "networks": th["networks_with_thin"],
                               **{pol: cost(r[pol + "|0.0"], r[pol + "|0.45"]) for pol in ("CG_c05", "CG-D")}}
    json.dump(out, open(os.path.join(S, "cost.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
