"""PLAN_REGIONS_2026-11-08.md (pushed 5e1863c before computing): per-region stratification, post hoc, descriptive.

Strata = the `region` field of results/v2/network_check.json (selection rule, written before scoring) + two aggregates.
Per stratum and label set: dismissed share of associated episodes for P1, P3, CG, CG-D, CG c = 0.5, and the differences
vs P3 with the frozen two-stage cluster bootstrap (v2_networks.cluster_boot, 2000 draws, seed 7, margin 3 pp).
Self-check: the all-network stratum must reproduce the frozen pooled CG - P3 of v2_eval_AB.json / v2_eval_reviewed.json.
Output: results/posthoc/regions.json, figures/fig5_regions.png (600 dpi).
"""
import os, sys, json, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); sys.path.insert(0, here)
from posthoc_collect import collect, _load
v2 = _load("v2r", os.path.join(here, "v2_networks.py"))
POL = ["P1", "P3", "CG", "CG-D", "CG_c05"]; NA = {"USA-Mexico", "Alaska-Aleutians-Canada"}


def strata():
    reg = {x["network"]: x["region"] for x in json.load(open(os.path.join(root, "results", "v2", "network_check.json")))}
    return reg


def block(rows, nets):
    d = {k: (rows[k]["days"], rows[k]["assoc"], rows[k]["act"]) for k in nets}
    na = sum(int(rows[k]["assoc"].sum()) for k in nets)
    share = {p: round(100 * sum(int(((rows[k]["act"][p] == "D") & rows[k]["assoc"]).sum()) for k in nets) / max(na, 1), 2) for p in POL}
    o = {"networks": sorted(nets), "n_networks": len(nets), "associated": na, "dismissed_share_pct": share,
         "single_network_day_bootstrap": len(nets) == 1}
    if na:
        o["vs_P3"] = {p: v2.cluster_boot(d, p, "P3") for p in ("CG", "CG-D", "CG_c05", "P1")}
    return o


def run(labels, run_dirs=("runs",)):
    rows = collect(labels, run_dirs); reg = strata()
    inc = sorted(k for k, v in rows.items() if v["included"])
    out = {"labels": labels, "run_dirs": list(run_dirs), "included_networks": len(inc), "strata": {}}
    for r in sorted({reg[k] for k in inc}):
        out["strata"][r] = block(rows, [k for k in inc if reg[k] == r])
    out["strata"]["ALL"] = block(rows, inc)
    out["strata"]["outside USA-Mexico"] = block(rows, [k for k in inc if reg[k] != "USA-Mexico"])
    out["strata"]["outside North America"] = block(rows, [k for k in inc if reg[k] not in NA])
    out["strata"]["USA-Mexico"] = out["strata"].get("USA-Mexico")
    return out


def figure(res, fn):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    for ax, lab in zip(axes, ("catalogue", "reviewed")):
        S = res[lab]["strata"]; names = [k for k in S if k not in ("ALL",)] + ["ALL"]
        y = np.arange(len(names))[::-1]
        for off, p, col in ((-0.2, "CG", "#A42421"), (0.0, "CG-D", "#595959"), (0.2, "CG_c05", "#1f77b4")):
            m = [S[n]["vs_P3"][p]["pooled_diff_pp"] for n in names]; lo = [S[n]["vs_P3"][p]["pooled_ci95_pp"][0] for n in names]
            hi = [S[n]["vs_P3"][p]["pooled_ci95_pp"][1] for n in names]
            ax.errorbar(m, y + off, xerr=[np.array(m) - np.array(lo), np.array(hi) - np.array(m)], fmt="o", ms=4, color=col,
                        capsize=2, label={"CG_c05": "CG c = 0.5"}.get(p, p))
        ax.axvline(0, color="k", lw=0.6); ax.axvline(3, color="k", lw=0.8, ls="--")
        C, Rv = res["catalogue"]["strata"], res["reviewed"]["strata"]   # shared y axis: label with both network counts
        ax.set_yticks(y); ax.set_yticklabels([f"{n} ({C[n]['n_networks']}/{Rv[n]['n_networks']})" for n in names], fontsize=8)
        ax.set_xlabel("dismissed associated, policy minus P3 (pp)")
        ax.set_title(f"{lab} labels ({res[lab]['included_networks']} networks)")
    axes[0].text(0.0, -0.13, "(n/m) = networks with catalogue / reviewed labels", transform=axes[0].transAxes, fontsize=7)
    axes[0].legend(fontsize=8, loc="lower right"); fig.tight_layout(); fig.savefig(fn, dpi=600); plt.close(fig)


if __name__ == "__main__":
    ext = len(sys.argv) > 1 and sys.argv[1] == "ext12B"
    res = {"status": "post hoc, method fixed in PLAN_REGIONS_2026-11-08.md (5e1863c) before computing; descriptive",
           "catalogue": run("catalogue"), "reviewed": run("reviewed")}
    # self-check against the frozen pooled results
    ab = json.load(open(os.path.join(root, "results", "v2", "v2_eval_AB.json")))["PRIMARY_pooled_CG_minus_P3"]["pooled_diff_pp"]
    rv = json.load(open(os.path.join(root, "results", "v2_reviewed", "v2_eval_reviewed.json")))["PRIMARY_all38"]["R1_CG_minus_P3"]["pooled_diff_pp"]
    res["selfcheck"] = {"catalogue_ALL_CG_minus_P3": res["catalogue"]["strata"]["ALL"]["vs_P3"]["CG"]["pooled_diff_pp"], "frozen_AB": ab,
                        "reviewed_ALL_CG_minus_P3": res["reviewed"]["strata"]["ALL"]["vs_P3"]["CG"]["pooled_diff_pp"], "frozen_reviewed": rv}
    assert abs(res["selfcheck"]["catalogue_ALL_CG_minus_P3"] - ab) < 1e-6 and abs(res["selfcheck"]["reviewed_ALL_CG_minus_P3"] - rv) < 1e-6, res["selfcheck"]
    os.makedirs(os.path.join(root, "results", "posthoc"), exist_ok=True)
    json.dump(res, open(os.path.join(root, "results", "posthoc", "regions.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    figure(res, os.path.join(root, "figures", "fig5_regions.png"))
    for lab in ("catalogue", "reviewed"):
        print("==", lab)
        for k, s in res[lab]["strata"].items():
            if not s: continue
            v = s["vs_P3"]
            print(f"{k:30s} n={s['n_networks']:2d} assoc={s['associated']:5d} | P3 {s['dismissed_share_pct']['P3']:5.2f}% | "
                  + " | ".join(f"{p} {v[p]['pooled_diff_pp']:+.2f} {v[p]['pooled_ci95_pp']} NI={v[p]['pooled_noninferior']}" for p in ("CG", "CG-D", "CG_c05")))
    print(res["selfcheck"])
