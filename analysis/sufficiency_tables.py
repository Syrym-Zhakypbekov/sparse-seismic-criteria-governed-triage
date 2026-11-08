"""Tables K1-K3 of Appendix K (evidence-sufficiency stress test, post hoc; plan e30842d) from the result JSON.

Input: results/sufficiency/stress.json, results/sufficiency/thin_subset.json (analysis/sufficiency_stress.py).
Output: results/sufficiency/tables_K.md (pasted into the manuscript unchanged). Read-only on the inputs.
Usage: python analysis/sufficiency_tables.py
"""
import json, os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(root, "results", "sufficiency")
S = json.load(open(os.path.join(D, "stress.json")))
T = json.load(open(os.path.join(D, "thin_subset.json")))

ROWS = [("P1", "P1 (classic coincidence)"), ("P3", "P3 (7.5 dB)"), ("P3_2t", "P3-2t (8.0 / 13.5 dB)"),
        ("CG|0.45", "CG, c = 1, δ = 0.45"), ("CG_c05|0.0", "CG, c = 0.5, δ = 0"),
        ("CG_c05|0.45", "CG, c = 0.5, δ = 0.45"), ("CG_c05|0.55", "CG, c = 0.5, δ = 0.55"),
        ("CG-D|0.0", "CG-D, δ = 0"), ("CG-D|0.45", "CG-D, δ = 0.45")]


def n(x):
    v = int(round(x))
    return f"{v:,}" if v >= 10000 else str(v)


def pct(r):
    # from counts (means over seeds), not from the 3-decimal pct stored in the JSON: avoids double rounding
    return 100.0 * r["assoc_dismissed"] / r["assoc"]


def thin_pct(r):
    return 100.0 * r["auto_thin"] / r["auto"] if r["auto"] else 0.0


def ci(c):
    lo, hi = c["ci95_pp"]
    f = lambda v: f"{v:.2f}".replace("-", "−")
    return f"{f(c['mean_pp'])} [{f(lo)}, {f(hi)}]"


out = []
ind, cor = S["modes"]["independent"], S["modes"]["correlated"]
out.append("Table K1. Evidence-sufficiency stress test on the 33 reviewed-label networks (263,303 episodes, 4,321 "
           "reviewed-associated): share of reviewed-associated alarms dismissed without masking and with half of the "
           "neighbour-site states set to MISSING (independently per episode and site, or as whole-day site outages), "
           "and, for independent masking at p = 0.5, automatic alerts without a reviewed event, escalations and the "
           "share of automatic decisions resting on fewer than two evidence sources. Columns 3 and 5–7: independent "
           "masking at p = 0.5; column 4: whole-day site outages at p = 0.5. Masked values are means over 50 "
           "masking seeds. Post hoc (results/sufficiency/stress.json).")
out.append("")
out.append("| Rule | Dismissed (%), p = 0 | Dismissed (%), p = 0.5 | Dismissed (%), outages p = 0.5 | "
           "Alerts without a reviewed event | Escalations | On < 2 sources (%) |")
out.append("|---|---|---|---|---|---|---|")
for k, lab in ROWS:
    r0, r5, c5 = ind["0.0"]["rules"][k], ind["0.5"]["rules"][k], cor["0.5"]["rules"][k]
    out.append(f"| {lab} | {pct(r0):.2f} | {pct(r5):.2f} | {pct(c5):.2f} | "
               f"{n(r5['unassoc_alerts'])} | {n(r5['escalations'])} | {thin_pct(r5):.1f} |")
out.append("")
out.append("Table K2. Pre-stated contrasts of the stress test (percentage points; mean over 50 masking seeds, 95% "
           "interval from the 50 × 500 pooled two-stage cluster-bootstrap values). S1: P1 minus the criteria-governed "
           "rule (δ = 0.45). S2: c = 0.5 with δ = 0 minus δ = 0.45. S3: rise in the dismissed share from p = 0 to "
           "p = 0.5, c = 0.5 (δ = 0.45) minus the comparator.")
out.append("")
out.append("| Contrast | Independent, p = 0.5 | Whole-day outages, p = 0.5 |")
out.append("|---|---|---|")
for k, lab in (("S1_P1_minus_CGc05", "S1: P1 − CG c = 0.5"), ("S1_P1_minus_CG", "S1: P1 − CG c = 1"),
               ("S1_P1_minus_CGD", "S1: P1 − CG-D"), ("S2_CGc05_delta0_minus_045", "S2: δ = 0 − δ = 0.45 (c = 0.5)"),
               ("S2b_CGc05_delta055_minus_045", "δ = 0.55 − δ = 0.45 (c = 0.5)"),
               ("S3_rise_CGc05_minus_P3_2t", "S3: rise, c = 0.5 − P3-2t"), ("S3_rise_CGc05_minus_P3", "S3: rise, c = 0.5 − P3")):
    out.append(f"| {lab} | {ci(ind['0.5']['comparisons'][k])} | {ci(cor['0.5']['comparisons'][k])} |")
out.append("")
out.append("Table K3. The real thin subset: episodes of the unmasked archive with at least two of the three neighbour "
           f"sites missing ({n(T['episodes'])} episodes on {T['networks_with_thin']} networks). Post hoc "
           "(results/sufficiency/thin_subset.json).")
out.append("")
out.append("| Rule | Dismissed reviewed-associated | Automatic alerts without a reviewed event | Escalations | Automatic decisions on < 2 sources |")
out.append("|---|---|---|---|---|")
for k, lab in ROWS:
    r = T["rules"][k]
    out.append(f"| {lab} | {r['assoc_dismissed']} of {r['assoc']} | {r['unassoc_alerts']} | {n(r['escalations'])} | {r['auto_thin']} |")
txt = "\n".join(out) + "\n"
open(os.path.join(D, "tables_K.md"), "w", encoding="utf-8").write(txt)
print(txt)
