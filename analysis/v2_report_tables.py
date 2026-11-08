"""Descriptive tables for Section 4.10 / Appendix D of the manuscript (written 08.11.2026 after all v2 sets were scored; reads only
the stored scorer outputs, recomputes nothing): exclusion accounting, V6 and V8 pooled, chance share per set, margin sensitivity
of the pooled contrasts (post hoc), networks with zero observed discordance (with the exact one-sided 97.5% upper bound for a
Bernoulli rate when 0 adverse discordances are observed among n associated episodes, i.e. 1 - 0.025**(1/n)), per-network table.
    python analysis/v2_report_tables.py  -> results/posthoc/v2_report_tables.json, results/posthoc/v2_report_tables.md"""
import os, json
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); V = os.path.join(root, "results", "v2")
SETS = [("A", "v2_eval_batchA.json"), ("EXT12", "v2_eval_ext12.json"), ("B", "v2_eval_batchB.json"),
        ("A+B", "v2_eval_AB.json"), ("A+EXT12", "v2_eval_A_ext12.json")]
KEYS = [("CG", "PRIMARY_pooled_CG_minus_P3"), ("CG-D", "pooled_CGD_minus_P3"), ("c=0.5", "pooled_CGc05_minus_P3"),
        ("CG vs P3 8.0", "pooled_CG_minus_P3_8.0")]
out, md = {}, []
for name, f in SETS:
    d = json.load(open(os.path.join(V, f))); N = d["networks"]
    inc = {n: r for n, r in N.items() if r.get("included_in_pooled")}
    exc = {}
    for n, r in N.items():
        if r.get("included_in_pooled"): continue
        if "status" in r: exc[n] = r["status"]
        elif r.get("associated", 0) < 30: exc[n] = f"fewer than 30 associated episodes ({r.get('associated')})"
        else: exc[n] = "other: " + json.dumps({k: r[k] for k in ("catalogue_failures",) if k in r})
    s = lambda pol, key: sum(r["all"][pol][key] for r in inc.values())
    v6 = {"CG": s("CG", "unassoc_alerts"), "P3": s("P3", "unassoc_alerts"), "P1t": s("P1t", "unassoc_alerts"),
          "networks_CG_below_both": sum(1 for r in inc.values() if r["H_unassoc_alerts"]["CG"] < min(r["H_unassoc_alerts"]["P3"], r["H_unassoc_alerts"]["P1t"])),
          "networks": len(inc)}
    v8 = {"episodes": sum(r["H_all_missing_escalated"]["episodes"] for r in inc.values()),
          "CG_escalated": sum(r["H_all_missing_escalated"]["CG_escalated"] for r in inc.values())}
    assoc = sum(r["associated"] for r in inc.values()); chance = sum(r["chance_control"]["chance_associated_mean"] for r in inc.values())
    pooled = {}
    for lab, k in KEYS:
        x = d.get(k)
        if not x: continue
        hi = x["pooled_ci95_pp"][1]
        pooled[lab] = {"diff": x["pooled_diff_pp"], "ci": x["pooled_ci95_pp"], "equal_weight": x["equal_weight_diff_pp"],
                       "equal_weight_ci": x["equal_weight_ci95_pp"], "ratio": x["ratio"], "ratio_ci": x["ratio_ci95"],
                       "met_at_margin_pp": {m: hi < m for m in (1, 2, 3, 5)}}
    zero = {n: {"assoc": r["associated"], "exact_upper_975_pct": round(100 * (1 - 0.025 ** (1 / r["associated"])), 2)}
            for n, r in inc.items() if r["H_noninferiority"]["CG-P3"]["ci95_pp"] == [0.0, 0.0]}
    holm = d.get("per_network_holm_CG_minus_P3", {})
    rows = []
    for n, r in sorted(inc.items(), key=lambda t: -t[1]["associated"]):
        a = r["all"]; h = r["H_noninferiority"]["CG-P3"]
        rows.append({"net": n, "assoc": r["associated"], "P3": a["P3"]["dismissed_assoc"], "CG": a["CG"]["dismissed_assoc"],
                     "CG-D": a["CG-D"]["dismissed_assoc"], "c05": a["CG_c05"]["dismissed_assoc"], "diff": h["diff_pp"], "ci": h["ci95_pp"],
                     "chance_share": round(r["chance_control"]["chance_associated_mean"] / max(r["associated"], 1), 3),
                     "holm_p": holm.get(n), "outage_assoc": r["outage_nearest_site"]["CG"]["assoc"] if r["outage_nearest_site"].get("CG") else 0})
    out[name] = {"file": f, "included": len(inc), "listed": len(N), "excluded": exc, "V6": v6, "V8": v8,
                 "chance_share_pooled": round(chance / max(assoc, 1), 3), "associated": assoc, "pooled": pooled,
                 "zero_discordance_networks": zero, "V7": d.get("outage_hypothesis"), "rows": rows}
    md.append(f"## {name} ({f}): {len(inc)} of {len(N)} included; associated {assoc}; chance share {out[name]['chance_share_pooled']}")
    md.append("excluded: " + "; ".join(f"{k} {v}" for k, v in exc.items()))
    md.append(f"V6 pooled unassociated alerts CG {v6['CG']}, P3 {v6['P3']}, P1t {v6['P1t']}; CG below both in {v6['networks_CG_below_both']}/{v6['networks']} networks; V8 {v8}")
    for lab, p in pooled.items(): md.append(f"{lab}: {p['diff']} {p['ci']} eq {p['equal_weight']} {p['equal_weight_ci']} ratio {p['ratio']} {p['ratio_ci']} met@1/2/3/5 {p['met_at_margin_pp']}")
    md.append("zero discordance: " + json.dumps(zero))
    md.append("| net | assoc | P3 | CG | CG-D | c=0.5 | CG−P3 pp [95%] | chance share | Holm p |"); md.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows: md.append(f"| {r['net']} | {r['assoc']} | {r['P3']} | {r['CG']} | {r['CG-D']} | {r['c05']} | {r['diff']} [{r['ci'][0]}, {r['ci'][1]}] | {r['chance_share']} | {r['holm_p']} |")
    md.append("")
os.makedirs(os.path.join(root, "results", "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(root, "results", "posthoc", "v2_report_tables.json"), "w"), indent=1)
open(os.path.join(root, "results", "posthoc", "v2_report_tables.md"), "w", encoding="utf-8").write("\n".join(md))
print("\n".join(md))
