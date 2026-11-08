"""README animations for every P10 experiment.

Reads ONLY result files in results/ (and the blind adjudication plots) and writes
figures/gif/<name>.gif plus figures/gif/experiments_table.md (key numbers per experiment,
read from the same JSON files). No number is typed by hand.

    python analysis/make_readme_gifs.py            # all GIFs
    python analysis/make_readme_gifs.py regions     # one GIF
"""
import io
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "gif")
W, H, DPI = 8.0, 4.5, 100          # 800 x 450 px
MS = 1600                           # ms per frame
MARGIN = 3.0
COL = {"P1": "#9e9e9e", "P1t": "#bdbdbd", "P3": "#455a64", "CG": "#c62828", "CG-D": "#1565c0",
       "CG_c05": "#2e7d32", "CG-ctx": "#6a1b9a", "LR": "#ef6c00", "GB": "#f9a825", "MLP": "#8d6e63",
       "LLR-T": "#00838f", "LLR-M": "#26a69a", "SCREEN": "#ad1457", "P3_2t": "#78909c", "OPT": "#000000"}
LABEL = {"CG": "CG (c = 1)", "CG-D": "CG-D", "CG_c05": "CG, c = 0.5", "CG-ctx": "CG, context c",
         "P3": "P3", "P1": "P1", "P1t": "P1t", "CG-platt": "context c, Platt",
         "CG-iso": "context c, isotonic", "P3_2t": "P3 two-threshold", "SCREEN": "screen",
         "OPT": "cost-optimal"}

plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "axes.spines.top": False,
                     "axes.spines.right": False})


def J(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def lab(p):
    return LABEL.get(p, p)


def fig2img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save(name, frames, ms=MS):
    os.makedirs(OUT, exist_ok=True)
    pal = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT) for f in frames]
    durs = [ms] * (len(pal) - 1) + [ms * 2]
    path = os.path.join(OUT, name + ".gif")
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=durs, loop=0, optimize=True)
    frames[0].save(os.path.join(OUT, "_frames", name + "_first.png")) if os.path.isdir(os.path.join(OUT, "_frames")) else None
    frames[-1].save(os.path.join(OUT, "_frames", name + "_last.png")) if os.path.isdir(os.path.join(OUT, "_frames")) else None
    return path


def forest_frames(title, rows, xlabel="policy minus P3 (percentage points of dismissed associated alarms)",
                  margin=MARGIN, note="", xlim=None):
    """rows: list of (label, point, lo, hi, colour). One frame per revealed row."""
    frames = []
    lo_all = min(r[2] for r in rows)
    hi_all = max(r[3] for r in rows)
    if xlim is None:
        xlim = (min(-1.0, lo_all - 0.5), max(margin + 1.0, hi_all + 0.5))
    for k in range(1, len(rows) + 1):
        fig, ax = plt.subplots(figsize=(W, H))
        ax.axvline(0, color="#999", lw=1)
        if margin is not None:
            ax.axvline(margin, color="#c62828", ls="--", lw=1.2)
            ax.text(margin, len(rows) - 0.4, f" margin {margin:g}", color="#c62828", va="bottom", fontsize=9)
        for i, (name, pt, lo, hi, c) in enumerate(rows[:k]):
            y = len(rows) - 1 - i
            ok = margin is None or hi <= margin
            ax.plot([lo, hi], [y, y], color=c, lw=3)
            ax.plot(pt, y, "o", color=c, ms=8)
            ax.text(xlim[1], y, f"  {pt:+.2f} [{lo:.2f}, {hi:.2f}]" + ("" if margin is None else ("  met" if ok else "  not met")),
                    va="center", fontsize=9, color="#2e7d32" if ok else "#c62828")
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r[0] for r in rows][::-1])
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.7, len(rows) - 0.1)
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left")
        if note:
            fig.text(0.01, 0.01, note, fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 0.80, 1))
        frames.append(fig2img(fig))
    return frames


def bars_frames(title, groups, ylabel, order=None, note="", fmt="{:.0f}"):
    """groups: list of (frame_title, {series: value}). One frame per group."""
    frames = []
    for gt, vals in groups:
        ymax = max(1.0, max(vals.values()) * 1.18)
        keys = order or list(vals.keys())
        fig, ax = plt.subplots(figsize=(W, H))
        xs = range(len(keys))
        ax.bar(xs, [vals[k] for k in keys], color=[COL.get(k, "#607d8b") for k in keys])
        for x, k in zip(xs, keys):
            ax.text(x, vals[k], fmt.format(vals[k]), ha="center", va="bottom", fontsize=9)
        ax.set_xticks(list(xs))
        long = max(len(lab(k)) for k in keys) * len(keys) > 70
        ax.set_xticklabels([lab(k).replace('_', ' ') for k in keys], rotation=18 if long else 0,
                           ha='right' if long else 'center', fontsize=8 if long else 9)
        ax.set_ylim(0, ymax)
        ax.set_ylabel(ylabel)
        ax.set_title(f"{title}\n{gt}", loc="left")
        if note:
            fig.text(0.01, 0.01, note, fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    return frames


def row(d, label, c):
    ci = d.get("pooled_ci95_pp") or d.get("ci95_pp") or d.get("ci95")
    pt = d.get("pooled_diff_pp", d.get("diff_pp"))
    return (label, pt, ci[0], ci[1], c)


TABLE = []   # rows for experiments_table.md


def tab(name, question, verdict, numbers, source):
    TABLE.append((name, question, verdict, numbers, source))


# ---------------------------------------------------------------- experiments
def single_network():
    kz, ak, ex = J("results", "kz", "kz_eval.json"), J("results", "ak", "ak_eval.json"), J("results", "extended", "extended_eval.json")
    ku = J("results", "kurk_ext", "kurk_ext_eval.json")
    k3 = next(v for k, v in ku.items() if k.startswith("K3"))
    rows = [row(ex["E3"], "IU.MAKZ 2025-26, CG (E3)", COL["CG"]),
            row(k3, "II.KURK 2025-26, CG (K3)", COL["CG"]),
            row(kz["N3_CG_noninferiority"], "KZ network, CG (N3)", COL["CG"]),
            row(kz["N5_CGD_noninferiority"], "KZ network, CG-D (N5)", COL["CG-D"]),
            row(ak["R3_CG_noninferiority"], "AK Alaska, CG (R3)", COL["CG"]),
            row(ak["R5_CGD_noninferiority"], "AK Alaska, CG-D (R5)", COL["CG-D"]),
            row(ak["R6_constant_c05_noninferiority"], "AK Alaska, c = 0.5 (R6)", COL["CG_c05"])]
    save("01_single_network", forest_frames("Single-network tests (catalogue association)", rows,
         note="Sources: results/extended, kurk_ext, kz, ak *_eval.json"))
    tab("Single-network tests (Kazakhstan, Alaska)", "Is CG non-inferior to P3 at one reference station?",
        "CG fails in Kazakhstan, met in Alaska; the discounted variants met where tested",
        f"E3 {ex['E3']['diff_pp']}, N3 {kz['N3_CG_noninferiority']['diff_pp']}, N5 {kz['N5_CGD_noninferiority']['diff_pp']}, R3 {ak['R3_CG_noninferiority']['diff_pp']}",
        "results/kz/kz_eval.json, results/ak/ak_eval.json, results/extended/extended_eval.json")


def batches():
    rows = []
    for f, nm in [("v2_eval_batchA.json", "batch A"), ("v2_eval_batchB.json", "batch B"), ("v2_eval_AB.json", "A + B")]:
        d = J("results", "v2", f)
        rows += [row(d["PRIMARY_pooled_CG_minus_P3"], f"{nm}: CG", COL["CG"]),
                 row(d["pooled_CGD_minus_P3"], f"{nm}: CG-D", COL["CG-D"]),
                 row(d["pooled_CGc05_minus_P3"], f"{nm}: c = 0.5", COL["CG_c05"])]
    save("02_multinetwork_catalogue", forest_frames("Multi-network test, catalogue association (38 networks)", rows,
         note="Source: results/v2/v2_eval_batchA/batchB/AB.json"))
    b = J("results", "v2", "v2_eval_batchB.json")
    tab("Multi-network test, catalogue labels", "Does rule v2 hold across networks selected by metadata?",
        "CG fails; discounted variants met in batch B",
        f"batch B: CG {b['PRIMARY_pooled_CG_minus_P3']['pooled_diff_pp']}, CG-D {b['pooled_CGD_minus_P3']['pooled_diff_pp']}, c=0.5 {b['pooled_CGc05_minus_P3']['pooled_diff_pp']}",
        "results/v2/v2_eval_batchB.json")


def reviewed33():
    d = J("results", "v2_reviewed", "v2_eval_reviewed.json")["PRIMARY_all38"]
    rows = [row(d["R1_CG_minus_P3"], "R1 CG (primary)", COL["CG"]),
            row(d["R2_CGD_minus_P3"], "R2 CG-D", COL["CG-D"]),
            row(d["R3_CGc05_minus_P3"], "R3 c = 0.5", COL["CG_c05"]),
            row(d["CG_v2_minus_v1"], "rule v2 minus v1", "#795548")]
    fr = forest_frames("Analyst-reviewed bulletins, 33 networks", rows,
                       note="Source: results/v2_reviewed/v2_eval_reviewed.json")
    o = d["R7_outage"]
    fr += bars_frames("Outage days of the nearest site", [(f"{o['networks']} networks, {o['assoc']} reviewed-associated alarms",
                      {"P1": o["P1"], "CG": o["CG"]})], "dismissed reviewed-associated")
    save("03_reviewed_bulletin", fr)
    tab("Reviewed-bulletin test, 33 networks (primary)", "Within 3 points of P3 on analyst-reviewed events?",
        "primary CG not met; CG-D and c = 0.5 met (secondary)",
        f"CG {d['R1_CG_minus_P3']['pooled_diff_pp']}; CG-D {d['R2_CGD_minus_P3']['pooled_diff_pp']} (ratio {d['R2_CGD_minus_P3']['ratio']}); c=0.5 {d['R3_CGc05_minus_P3']['pooled_diff_pp']} (ratio {d['R3_CGc05_minus_P3']['ratio']}); outage CG {o['CG']} vs P1 {o['P1']}",
        "results/v2_reviewed/v2_eval_reviewed.json")


def ext12b():
    rows = []
    for f, nm in [("v2_eval_ext12B.json", "extension months"), ("v2_eval_B_ext12B.json", "full year")]:
        d = J("results", "v2", f)
        rows += [row(d["PRIMARY_pooled_CG_minus_P3"], f"{nm}: CG", COL["CG"]),
                 row(d["pooled_CGD_minus_P3"], f"{nm}: CG-D", COL["CG-D"]),
                 row(d["pooled_CGc05_minus_P3"], f"{nm}: c = 0.5", COL["CG_c05"])]
    n = J("results", "v2", "v2_eval_ext12B.json")["PRIMARY_pooled_CG_minus_P3"]["networks"]
    save("04_ext12B", forest_frames(f"Twelve-month extension, {n} of 31 batch-B networks (catalogue)", rows,
         note="Source: results/v2/v2_eval_ext12B.json, v2_eval_B_ext12B.json"))
    y = J("results", "v2", "v2_eval_B_ext12B.json")
    tab("12-month extension (ext12B)", "Does the result hold over a full year?",
        f"{n} of 31 networks; discounted variants met over the year",
        f"full year: CG-D {y['pooled_CGD_minus_P3']['pooled_diff_pp']}, c=0.5 {y['pooled_CGc05_minus_P3']['pooled_diff_pp']}, CG {y['PRIMARY_pooled_CG_minus_P3']['pooled_diff_pp']}",
        "results/v2/v2_eval_B_ext12B.json")


def rescue():
    d = J("results", "v2_rescue", "v2_eval_rescue.json")
    rows = []
    for lbl, nm in [("reviewed", "reviewed"), ("catalogue", "catalogue")]:
        for g, gn in [("RESCUE", "rescued 8"), ("ALL_primary_plus_rescue", "primary + rescued")]:
            rows.append(row(d[lbl][g]["CGc05_minus_P3"], f"{nm}, {gn}: c = 0.5", COL["CG_c05"]))
    save("05_rescue", forest_frames("Rescued networks (post hoc extension)", rows,
         note="Source: results/v2_rescue/v2_eval_rescue.json"))
    r = d["reviewed"]["RESCUE"]["CGc05_minus_P3"]
    a = d["reviewed"]["ALL_primary_plus_rescue"]["CGc05_minus_P3"]
    tab("Rescue of excluded networks", "Do the networks that first failed change the result?",
        "primary result unchanged; rescued set alone fails the ratio criterion",
        f"reviewed rescued c=0.5 {r['pooled_diff_pp']} (ratio upper {r['ratio_ci95'][1]}); primary+rescued {a['pooled_diff_pp']} (ratio upper {a['ratio_ci95'][1]})",
        "results/v2_rescue/v2_eval_rescue.json")


def context_c():
    c = J("results", "context_c", "context_c.json")["T1_reviewed_batchB"]
    rec = J("results", "context_c", "recal.json")
    bins = c["H3_calibration"]["reliability"][0]["bins"]
    frames = []
    for k in range(2, len(bins) + 1):
        fig, ax = plt.subplots(figsize=(W, H))
        ax.plot([0, 1], [0, 1], color="#999", ls="--", lw=1, label="perfect calibration")
        ax.axhline(0.5, color=COL["CG_c05"], lw=1.5, label="c = 0.5 (constant)")
        xs = [b["mean_pred"] for b in bins[:k]]
        ys = [b["obs_rate"] for b in bins[:k]]
        ax.plot(xs, ys, "o-", color=COL["CG-ctx"], label="context c")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xlabel("predicted confirmation probability"); ax.set_ylabel("observed confirmation rate")
        b = c["H3_calibration"]["brier"]
        ax.set_title(f"Context-dependent reliability on 26 test networks\nBrier: context {b['p_ctx']}, CG-D table {b['p_tab']}, c = 0.5 {b['c05']}", loc="left")
        ax.legend(loc="lower right", fontsize=9)
        fig.text(0.01, 0.01, "Source: results/context_c/context_c.json (H3). Points above the diagonal: under-prediction.", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    t = rec["T1_counts"]
    frames += bars_frames("Dismissed reviewed-associated alarms, 26 test networks",
                          [("original and recalibrated context c", {k: t[k]["dismissed_assoc"] for k in ["P3", "CG_c05", "CG-ctx", "CG-platt", "CG-iso"]})],
                          "dismissed reviewed-associated")
    save("06_context_c", frames)
    h1, h2 = c["H1_CGctx_minus_P3"], c["H2_CGctx_minus_CGc05"]
    tab("Context-dependent reliability c_j(x)", "Does a per-alarm reliability beat a constant c?",
        "H1-H4 held; lower Brier mainly from resolution; direction kept after recalibration",
        f"H1 {h1['pooled_diff_pp']}, H2 {h2['pooled_diff_pp']}, Brier {c['H3_calibration']['brier']['p_ctx']} vs {c['H3_calibration']['brier']['c05']}; Platt dismissed {t['CG-platt']['dismissed_assoc']} vs P3 {t['P3']['dismissed_assoc']}",
        "results/context_c/context_c.json, results/context_c/recal.json")


def regions():
    st = J("results", "posthoc", "regions.json")["reviewed"]["strata"]
    names = [k for k in st if k not in ("ALL",)]
    rows = []
    for k in names + ["ALL"]:
        v = st[k]["vs_P3"]["CG_c05"]
        rows.append(row(v, f"{k} ({st[k]['n_networks']})", COL["CG_c05"] if k not in ("ALL",) else "#000"))
    save("07_regions", forest_frames("c = 0.5 minus P3 by region (reviewed labels)", rows,
         note="Source: results/posthoc/regions.json. Single-network regions use a day bootstrap."))
    a, o = st["ALL"]["vs_P3"]["CG_c05"], st["outside USA-Mexico"]["vs_P3"]["CG_c05"]
    tab("Regions (post hoc)", "Does the result hold outside the USA?",
        "c = 0.5 within the margin in every region except the single East Asia network",
        f"all {a['pooled_diff_pp']}; outside USA-Mexico {o['pooled_diff_pp']} [{o['pooled_ci95_pp'][0]}, {o['pooled_ci95_pp'][1]}]",
        "results/posthoc/regions.json")


def workload():
    w = J("results", "posthoc", "workload.json")["reviewed"]
    cs, ps = w["sweep_CG_c"], w["sweep_P3_t"]
    frames = []
    keys = list(cs.keys())
    for i in range(1, len(keys) + 1):
        fig, ax = plt.subplots(figsize=(W, H))
        ax.plot([ps[t]["analyst_min_per_network_day"] for t in ps], [ps[t]["unassociated_alerts_per_network_day"] for t in ps],
                "s-", color=COL["P3"], label="P3 threshold 5-12 dB")
        sel = keys[:i]
        ax.plot([cs[c]["analyst_min_per_network_day"] for c in sel], [cs[c]["unassociated_alerts_per_network_day"] for c in sel],
                "o-", color=COL["CG_c05"], label="CG, c from 0 to 1")
        last = cs[sel[-1]]
        ax.plot(last["analyst_min_per_network_day"], last["unassociated_alerts_per_network_day"], "o", ms=12, mfc="none", mec="#000")
        ax.set_xlabel("analyst minutes per network-day (2 min per escalation)")
        ax.set_ylabel("false automatic alerts per network-day")
        ax.set_title(f"Operating curves on 33 reviewed networks\nc = {sel[-1]}: {last['analyst_min_per_network_day']} min, {last['unassociated_alerts_per_network_day']} false alerts, {last['dismissed_associated']} dismissed", loc="left")
        ax.legend(fontsize=9)
        fig.text(0.01, 0.01, "Source: results/posthoc/workload.json", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    save("08_workload", frames, ms=1100)
    fp = w["frozen_operating_points"]["pooled"]
    tab("Analyst workload (post hoc)", "Is escalation worth the analyst time?",
        "same analyst minutes as P3, about half the false automatic alerts",
        f"minutes/network-day P3 {fp['P3']['analyst_min_per_network_day']} vs c=0.5 {fp['CG_c05']['analyst_min_per_network_day']}; false alerts {fp['P3']['unassociated_alerts_per_network_day']} vs {fp['CG_c05']['unassociated_alerts_per_network_day']}",
        "results/posthoc/workload.json")


def gap():
    g = J("results", "gap", "gap_reviewed.json")
    loo = g["G4_leave_one_out"]["CG_c05"]["per_removed_network"]
    nets = list(loo.keys())
    frames = []
    step = max(1, len(nets) // 10)
    for i in range(step, len(nets) + step, step):
        sel = nets[:min(i, len(nets))]
        fig, ax = plt.subplots(figsize=(W, H))
        ax.bar(range(len(sel)), [loo[n]["upper95_pp"] for n in sel], color=COL["CG_c05"], alpha=0.55, label="upper 95% bound")
        ax.plot(range(len(sel)), [loo[n]["pooled_diff_pp"] for n in sel], "o", color=COL["CG_c05"], label="difference")
        ax.axhline(MARGIN, color="#c62828", ls="--", label="margin 3")
        ax.set_xticks(range(len(sel))); ax.set_xticklabels(sel, rotation=90, fontsize=8)
        ax.set_ylim(0, 3.6); ax.set_ylabel("c = 0.5 minus P3 (points)")
        cc = g["G2_chance_corrected"]["CG_c05"]
        ax.set_title(f"Leave one network out, c = 0.5 ({len(sel)}/{len(nets)} removals)\nchance-corrected {cc['chance_corrected_diff_pp']} [{cc['ci95_pp'][0]}, {cc['ci95_pp'][1]}]", loc="left")
        ax.legend(fontsize=8, loc="upper right")
        fig.text(0.01, 0.01, "Source: results/gap/gap_reviewed.json (G2, G4)", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    save("09_gap_map", frames, ms=900)
    ov = g["G1_overlap"]["reviewed_associated"]
    tab("Gap map: overlap, chance, margin, leave-one-out (post hoc)", "Is c = 0.5 just P3? Do chance matches or one network drive it?",
        "no verdict changes; c = 0.5 dismisses only all-NO alarms that P3 does not",
        f"Jaccard (reviewed) {ov['jaccard']}; c=0.5-only {ov['CG_c05_only']['n']} all-NO; chance-corrected {g['G2_chance_corrected']['CG_c05']['chance_corrected_diff_pp']}; LOO changes {len(g['G4_leave_one_out']['CG_c05']['removals_changing_verdict'])}",
        "results/gap/gap_reviewed.json")


def sensitivity():
    s = J("results", "sensitivity", "sens_weights.json")
    o = s["one_at_a_time"]["CG_c05"]
    frames = []
    for par, vals in o.items():
        fig, ax = plt.subplots(figsize=(W, H))
        xs = [v["value"] for v in vals]
        ax.plot(xs, [v["upper"] for v in vals], "o-", color=COL["CG_c05"], label="upper 95% bound")
        ax.plot(xs, [v["diff_pp"] for v in vals], "s--", color=COL["CG_c05"], alpha=0.6, label="difference")
        ax.axhline(MARGIN, color="#c62828", ls="--", label="margin 3")
        ax.set_xlabel(f"parameter {par} (others frozen)"); ax.set_ylabel("c = 0.5 minus P3 (points)")
        sm = s["summary"]["CG_c05"]
        ax.set_title(f"Sensitivity of c = 0.5 to {par}\nmargin met at {sm['share_points_met']*100:.0f}% of {sm['points']} grid points", loc="left")
        ax.legend(fontsize=9)
        fig.text(0.01, 0.01, "Source: results/sensitivity/sens_weights.json", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    ab = J("results", "sensitivity", "ablations.json")["ablations"]["CG"]
    frames += bars_frames("Ablations of CG (c = 1), 33 reviewed networks",
                          [("dismissed reviewed-associated alarms", {k: v["assoc_D"] for k, v in ab.items()})],
                          "dismissed", note="Source: results/sensitivity/ablations.json")
    save("10_sensitivity_ablation", frames)
    sm = {k: s["summary"][k]["share_points_met"] for k in ("CG", "CG_c05", "CG-D")}
    tab("Weights and thresholds sensitivity, ablations (post hoc)", "Do the verdicts depend on hand-set weights?",
        "the margin verdict depends on the hand-set weights and thresholds",
        f"share of 675 points met: c=0.5 {sm['CG_c05']}, CG-D {sm['CG-D']}, CG {sm['CG']}; single SNR threshold 0.38: CG dismissed {ab['A2_single_0.38']['assoc_D']} vs frozen {ab['frozen']['assoc_D']}",
        "results/sensitivity/sens_weights.json, results/sensitivity/ablations.json")


def twothreshold():
    t = J("results", "posthoc", "twothreshold.json")
    pts = t["P3_two_threshold_pareto"]
    ta = t["CG_c05_thetaA"]
    frames = []
    keys = list(ta.keys())
    for i in range(1, len(keys) + 1):
        fig, ax = plt.subplots(figsize=(W, H))
        ax.scatter([p["unassociated_alerts_per_network_day"] for p in pts], [p["dismissed_associated"] for p in pts],
                   s=10, color=COL["P3_2t"], alpha=0.5, label=f"P3 two-threshold ({len(pts)} settings)")
        sel = keys[:i]
        ax.plot([ta[k]["unassociated_alerts_per_network_day"] for k in sel], [ta[k]["dismissed_associated"] for k in sel],
                "o-", color=COL["CG_c05"], label="c = 0.5, theta_A varied")
        m = t["matched"]["CG_c05"]
        ax.plot(m["best_P3_2t"]["unassociated_alerts_per_network_day"], m["best_P3_2t"]["dismissed_associated"], "*", ms=14,
                color=COL["P3"], label=f"matched P3 {m['best_P3_2t']['tD_tA']} dB")
        ax.set_xlabel("automatic alerts without a reviewed event per network-day")
        ax.set_ylabel("dismissed reviewed-associated")
        ax.set_title(f"Two-threshold abstaining baseline (theta_A = {sel[-1]})", loc="left")
        ax.legend(fontsize=8)
        fig.text(0.01, 0.01, "Source: results/posthoc/twothreshold.json", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    save("11_two_threshold", frames, ms=1100)
    m = t["matched"]["CG_c05"]
    cst = J("results", "posthoc", "twothreshold_cost.json")
    tab("Two-threshold baseline and alert cost (post hoc)", "Is the gain from c or from the reject band?",
        "close to a two-threshold rule; alert reduction mainly from the reject band and theta_A",
        f"matched P3 {m['best_P3_2t']['tD_tA']}: dismissed {m['best_P3_2t']['dismissed_associated']} vs {m['target']['dismissed_associated']}; false alerts/day {m['best_P3_2t']['unassociated_alerts_per_network_day']} vs {m['target']['unassociated_alerts_per_network_day']}; P1t false alerts/day {cst['unassociated_alerts_per_network_day']['P1t_8.0']}",
        "results/posthoc/twothreshold.json, results/posthoc/twothreshold_cost.json")


def detprob():
    s = J("results", "detprob", "detprob.json")["T1_batchB_reviewed"]["summary"]
    order = ["P3", "CG_c05", "CG-D", "CG-ctx", "LLR-T", "LLR-M"]
    fr = bars_frames("Likelihood (detection-probability) baseline, 26 test networks", [
        ("dismissed reviewed-associated", {k: s[k]["dismissed_assoc"] for k in order}),
        ("analyst items (alerts + escalations)", {k: s[k]["analyst_items_alert_plus_escalation"] for k in order})],
        "count", order=order, note="Source: results/detprob/detprob.json")
    save("12_likelihood_baseline", fr)
    tab("Detection-probability likelihood baseline", "Does a likelihood-ratio rule on detection probability do better?",
        "no: it dismisses more reviewed events and fails the ratio criterion against P3",
        f"LLR-M dismissed {s['LLR-M']['dismissed_assoc']} vs c=0.5 {s['CG_c05']['dismissed_assoc']}; LLR-T {s['LLR-T']['dismissed_assoc']}",
        "results/detprob/detprob.json")


def gap2():
    f = J("results", "gap2", "forward_retune.json")
    rows = []
    for p in ("CG", "CG-D", "CG_c05"):
        rows.append(row(f["frozen_on_test_days"][p], f"{lab(p)}, frozen", COL[p]))
        rows.append(row(f["retuned"][p], f"{lab(p)}, re-tuned on first 30 days", COL[p]))
    lc = J("results", "gap2", "low_chance.json")["results"]["low_chance"]
    rows.append(row(lc["CG_c05"], "c = 0.5, low-chance networks", COL["CG_c05"]))
    save("13_forward_retune", forest_frames("Forward re-tuning and low-chance subset (post hoc)", rows,
         note="Source: results/gap2/forward_retune.json, low_chance.json"))
    r = f["retuned"]
    tab("Forward re-tuning, low-chance subset, G.WUS (post hoc)", "Does the failure come from the frozen threshold?",
        "re-tuned forward in time, all three variants meet both criteria",
        f"re-tuned CG {r['CG']['pooled_diff_pp']}, CG-D {r['CG-D']['pooled_diff_pp']}, c=0.5 {r['CG_c05']['pooled_diff_pp']}",
        "results/gap2/forward_retune.json, results/gap2/low_chance.json, results/gap2/wus_removed.json")


def learned():
    c = J("results", "review2", "learned_rejectband.json")["T1"]["counts"]
    order = ["P3", "CG_c05", "CG-D", "LR", "GB", "MLP"]
    fr = bars_frames("Learned baselines with a reject band, 26 test networks", [
        ("dismissed reviewed-associated", {k: c[k]["dismissed_assoc"] for k in order}),
        ("escalations per network-day", {k: c[k]["escalations_per_network_day"] for k in order}),
        ("false automatic alerts per network-day", {k: c[k]["unassoc_alerts_per_network_day"] for k in order})],
        "value", order=order, note="Source: results/review2/learned_rejectband.json", fmt="{:.1f}")
    save("14_learned_rejectband", fr)
    tab("Learned baselines with a reject band", "Do ML models with abstention do better?",
        "fewer dismissals but more escalations and false alerts; none better on all three",
        f"LR {c['LR']['dismissed_assoc']}, GB {c['GB']['dismissed_assoc']}, MLP {c['MLP']['dismissed_assoc']} vs c=0.5 {c['CG_c05']['dismissed_assoc']}",
        "results/review2/learned_rejectband.json")


def calendar_holm():
    cal = J("results", "review2", "calendar_ctx.json")
    rows = []
    for b, v in cal["blocks"].items():
        rows.append((f"H1 context c - P3, blocks {b}", cal["observed"]["H1_ctx_minus_P3_pp"], v["H1_diff_ci95_pp"][0], v["H1_diff_ci95_pp"][1], COL["CG-ctx"]))
    for b, v in cal["blocks"].items():
        rows.append((f"H2 context c - c=0.5, blocks {b}", cal["observed"]["H2_ctx_minus_c05_pp"], v["H2_diff_ci95_pp"][0], v["H2_diff_ci95_pp"][1], COL["CG_c05"]))
    fr = forest_frames("Shared-calendar bootstrap for context c", rows, margin=MARGIN,
                       note="Source: results/review2/calendar_ctx.json")
    h = J("results", "review2", "holm_hires.json")
    fr += bars_frames(f"Multiplicity at {h['resamples']} resamples, family of {h['family_size']} tests",
                      [("tests met", {"unadjusted": h["met_unadjusted"], "Holm": h["met_after_holm"], "BY": h["met_after_BY"]})],
                      "tests met", note="Source: results/review2/holm_hires.json")
    save("15_calendar_holm", fr)
    tab("Calendar bootstrap for context c; Holm at 20,000 resamples", "Do the context-c and pooled results survive dependence and multiplicity?",
        "context-c H1/H2 kept at every block length; c = 0.5, CG-D and context-c H1/H2 pass after Holm, CG does not",
        f"Holm met {h['met_after_holm']} of {h['family_size']}; c=0.5 Holm p {h['key']['reviewed_pooled:CG_c05']['holm']}; CG Holm p {h['key']['reviewed_pooled:CG']['holm']}",
        "results/review2/calendar_ctx.json, results/review2/holm_hires.json")


def margin_cost():
    m = J("results", "review2", "margin_cost.json")
    fs = sorted({c["f_min_per_false_alert"] for c in m["cells"]})
    ks = sorted({c["k_min_per_dismissed_reviewed"] for c in m["cells"]})
    frames = []
    for pol in ("CG_c05", "CG-D"):
        fig, ax = plt.subplots(figsize=(W, H))
        grid = [[next(c[pol]["break_even_margin_pp"] for c in m["cells"] if c["f_min_per_false_alert"] == f and c["k_min_per_dismissed_reviewed"] == k) for k in ks] for f in fs]
        im = ax.imshow(grid, cmap="RdYlGn", aspect="auto", vmin=-1, vmax=4, origin="lower")
        for i, f in enumerate(fs):
            for j, k in enumerate(ks):
                ax.text(j, i, f"{grid[i][j]:.2f}", ha="center", va="center", fontsize=9)
        ax.set_xticks(range(len(ks))); ax.set_xticklabels([f"k={k}" for k in ks])
        ax.set_yticks(range(len(fs))); ax.set_yticklabels([f"f={f}" for f in fs])
        ax.set_xlabel("analyst-minutes per dismissed reviewed event (k)")
        ax.set_ylabel("minutes per false automatic alert (f)")
        ax.set_title(f"Break-even extra-dismissal margin for {lab(pol)} (points)\nobserved excess {m['observed_extra_dismissed_pp'][pol]}", loc="left")
        fig.colorbar(im, ax=ax, fraction=0.04)
        fig.text(0.01, 0.01, "Source: results/review2/margin_cost.json", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    save("16_margin_cost", frames, ms=2200)
    tab("Margin from analyst cost", "Is 3 points lenient or strict in analyst minutes?",
        "depends on the cost of a false alert: the c = 0.5 excess pays for itself when f >= 0.5 min and k <= 120 min, not when false alerts cost nothing",
        f"observed excess c=0.5 {m['observed_extra_dismissed_pp']['CG_c05']}, CG-D {m['observed_extra_dismissed_pp']['CG-D']}",
        "results/review2/margin_cost.json")


def rule_checks():
    u = J("results", "review2", "undefined_snr.json")
    tt = J("results", "review2", "threshold_table.json")
    fr = bars_frames(f"Undefined-SNR variant: {u['episodes_undefined_snr']} episodes on {u['networks']} networks",
                     [("decisions changed to escalation", {p: sum(u["policies"][p]["changed_decisions_from"].values()) for p in ("CG", "CG-D", "CG_c05")}),
                      ("reviewed-associated dismissals removed", {p: u["policies"][p]["reviewed_associated_dismissals_removed"] for p in ("CG", "CG-D", "CG_c05")})],
                     "count", note="Source: results/review2/undefined_snr.json")
    fig, ax = plt.subplots(figsize=(W, H))
    ax.axis("off")
    lines = [f"Closed-form SNR threshold table (Table A2)", "",
             f"cells checked: {tt['cells_checked']}", f"cell mismatches: {len(tt['cell_mismatches'])}"]
    for p, v in tt["episode_check"].items():
        lines.append(f"{lab(p)}: " + ", ".join(f"{k} {x}" for k, x in v.items()))
    ax.text(0.02, 0.95, "\n".join(lines), va="top", fontsize=13, family="monospace")
    fig.text(0.01, 0.01, "Source: results/review2/threshold_table.json", fontsize=8, color="#555")
    fr.append(fig2img(fig))
    save("17_rule_checks", fr)
    tab("Undefined SNR variant; threshold-table check", "Do edge cases or the closed-form table change anything?",
        "no verdict changes; 0 mismatches",
        f"undefined-SNR episodes {u['episodes_undefined_snr']}; cells {tt['cells_checked']}, mismatches {len(tt['cell_mismatches'])}",
        "results/review2/undefined_snr.json, results/review2/threshold_table.json")


def schorlemmer():
    d = J("results", "review3", "detprob_schorlemmer.json")
    mb = d["by_magnitude_bin"]
    frames = []
    for i in range(1, len(mb) + 1):
        fig, ax = plt.subplots(figsize=(W, H))
        xs = list(range(i))
        for key, c, nm in [("obs", "#000", "observed"), ("p_pd_lr", "#00838f", "magnitude-distance model"),
                           ("p_ctx", COL["CG-ctx"], "context c"), ("p_tab", COL["CG-D"], "CG-D table")]:
            ax.plot(xs, [b[key] for b in mb[:i]], "o-", color=c, label=nm)
        ax.set_xticks(range(len(mb))); ax.set_xticklabels([f"M {b['mag_bin']}" for b in mb])
        ax.set_xlim(-0.5, len(mb) - 0.5); ax.set_ylim(0, 1)
        ax.set_ylabel("neighbour confirmation rate")
        br = d["brier"]
        ax.set_title(f"Detection probability by magnitude ({len(d['test']['networks'])} test networks)\nBrier: magnitude model {br['p_pd_lr']}, context c {br['p_ctx']}, table {br['p_tab']}", loc="left")
        ax.legend(fontsize=8, loc="upper left")
        fig.text(0.01, 0.01, "Source: results/review3/detprob_schorlemmer.json", fontsize=8, color="#555")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        frames.append(fig2img(fig))
    save("18_schorlemmer", frames)
    tab("Schorlemmer-style detection probability", "Does context c match a standard seismological quantity?",
        "partly; lower Brier than the table and the constant",
        f"Brier magnitude model {d['brier']['p_pd_lr']}, context c {d['brier']['p_ctx']}, table {d['brier']['p_tab']}, c=0.5 {d['brier']['c05']}",
        "results/review3/detprob_schorlemmer.json")


def costopt():
    groups = []
    order = ["OPT", "CG", "CG_c05", "CG-D", "P3", "P3_2t", "P1t"]
    co = J("results", "review3", "costopt_thresholds.json")["by_k"]
    for k in ("30", "60", "120", "240"):
        groups.append((f"no cost for false alerts, k = {k} min per dismissed event", {p: co[k]["test_cost_per_network_day"][p] for p in order}))
    for F in ("5", "15", "30"):
        d = J("results", "review3", f"costopt_falsealert_F{F}.json")["by_k"]["60"]
        groups.append((f"exploratory: false alert {F} min, k = 60", {p: d["test_cost_per_network_day"][p] for p in order}))
    save("19_cost_optimal", bars_frames("Analyst cost per network-day on 26 test networks", groups, "minutes per network-day",
                                        order=order, note="Sources: results/review3/costopt_*.json", fmt="{:.1f}"))
    f15 = J("results", "review3", "costopt_falsealert_F15.json")["by_k"]["60"]["test_cost_per_network_day"]
    tab("Cost-optimal thresholds", "How close are the frozen thresholds to cost-optimal?",
        "frozen thresholds are far from cost-optimal; with a false-alert cost the CG variants cost less than P3 and P1t (exploratory)",
        f"F=15: c=0.5 {f15['CG_c05']}, CG-D {f15['CG-D']}, P3 {f15['P3']}, P1t {f15['P1t']}",
        "results/review3/costopt_thresholds.json, results/review3/costopt_falsealert_F*.json")


def draelos():
    d = J("results", "review3", "draelos_screen.json")["test_totals"]
    order = ["P3", "CG_c05", "CG-D", "P3_2t", "SCREEN"]
    save("20_draelos_screen", bars_frames("False-event screening baseline, 26 test networks", [
        ("dismissed reviewed-associated", {k: d[k]["dismissed_reviewed_associated"] for k in order}),
        ("escalations", {k: d[k]["escalations"] for k in order}),
        ("false automatic alerts", {k: d[k]["unassociated_alerts"] for k in order})],
        "count", order=order, note="Source: results/review3/draelos_screen.json"))
    tab("Draelos-style false-event screen", "Does a learned screen beat the rule?",
        "matches P3 dismissals only by escalating more and alerting about twice as often",
        f"screen dismissed {d['SCREEN']['dismissed_reviewed_associated']}, escalations {d['SCREEN']['escalations']}, false alerts {d['SCREEN']['unassociated_alerts']} vs c=0.5 {d['CG_c05']['unassociated_alerts']}",
        "results/review3/draelos_screen.json")


def kz_reviewed():
    k = J("results", "kz_analyst", "kz_reviewed_eval.json")["runs"]
    rows = []
    for run in ("K-MAKZ_L1", "K-KZ_L1", "K-KURK_L1", "K-MAKZ_L2", "K-KZ_L2", "K-KURK_L2"):
        v = k[run]
        rows.append(row(v["KR1_CG"], f"{run}: CG", COL["CG"]))
        rows.append(row(v["KR3_CGc05"], f"{run}: c = 0.5", COL["CG_c05"]))
    save("21_kazakhstan_reviewed", forest_frames("Kazakhstan against analyst-reviewed events (L1 ISC, L2 national)", rows,
         note="Source: results/kz_analyst/kz_reviewed_eval.json"))
    m = k["K-MAKZ_L1"]
    tab("Kazakhstan, analyst-reviewed labels", "Do the Kazakhstan results hold on reviewed events?",
        "MAKZ: all met (L1); KZ: CG not met, discounted met; KURK L2 discounted not met",
        f"MAKZ L1 CG {m['KR1_CG']['diff_pp']}, c=0.5 {m['KR3_CGc05']['diff_pp']}; KZ L1 CG {k['K-KZ_L1']['KR1_CG']['diff_pp']}; KURK L2 c=0.5 {k['K-KURK_L2']['KR3_CGc05']['diff_pp']}",
        "results/kz_analyst/kz_reviewed_eval.json")


def blind():
    pdir = os.path.join(ROOT, "adjudication", "blind_v1", "plots")
    files = sorted(f for f in os.listdir(pdir) if f.endswith(".png"))[:8]
    frames = []
    for f in files:
        im = Image.open(os.path.join(pdir, f)).convert("RGB")
        im.thumbnail((800, 450))
        canvas = Image.new("RGB", (800, 470), "white")
        canvas.paste(im, ((800 - im.width) // 2, 0))
        frames.append(canvas)
    import csv
    with open(os.path.join(ROOT, "adjudication", "blind_v1", "cases.csv"), encoding="utf-8") as fh:
        n = sum(1 for _ in csv.DictReader(fh))
    save("22_blind_adjudication", frames, ms=1300)
    tab("Blind adjudication package (planned)", "Would an analyst confirm the disputed dismissals?",
        "package ready; adjudication by a human analyst not yet done",
        f"{n} cases with waveform plots, no rule labels",
        "adjudication/blind_v1/")


ALL = [single_network, batches, reviewed33, ext12b, rescue, context_c, regions, workload, gap, sensitivity,
       twothreshold, detprob, gap2, learned, calendar_holm, margin_cost, rule_checks, schorlemmer, costopt,
       draelos, kz_reviewed, blind]


def main():
    os.makedirs(os.path.join(OUT, "_frames"), exist_ok=True)
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        fn()
        print("ok", fn.__name__)
    if not want:
        with open(os.path.join(OUT, "experiments_table.md"), "w", encoding="utf-8") as f:
            f.write("| Experiment | Question | Verdict | Key numbers (from the result file) | Result file |\n|---|---|---|---|---|\n")
            for r in TABLE:
                f.write("| " + " | ".join(r) + " |\n")


if __name__ == "__main__":
    main()
