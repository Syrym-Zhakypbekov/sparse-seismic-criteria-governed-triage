"""Figure 6 with the two-threshold abstaining family added (internal review of v33, point M2). Reads results/posthoc/workload.json
(analysis/posthoc_workload.py) and results/posthoc/twothreshold.json (analysis/posthoc_twothreshold.py); computes nothing new.
Writes figures/fig6_workload.png."""
import os, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = json.load(open(os.path.join(root, "results", "posthoc", "workload.json")))["reviewed"]
T = json.load(open(os.path.join(root, "results", "posthoc", "twothreshold.json")))
ASSOC = 4321; MIN = 2.0
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
xs = [MIN * p["escalations_per_network_day"] for p in T["P3_two_threshold_pareto"]]
axes[0].scatter(xs, [100 * p["dismissed_associated"] / ASSOC for p in T["P3_two_threshold_pareto"]], s=6, c="#BABABA", label="P3 two-threshold settings (360)")
axes[1].scatter(xs, [p["unassociated_alerts_per_network_day"] for p in T["P3_two_threshold_pareto"]], s=6, c="#BABABA")
for key, lab, col, mk in (("sweep_CG_c", "CG family (c = 0 ... 1)", "#A42421", "o"), ("sweep_P3_t", "P3 family (5 ... 12 dB)", "#595959", "s")):
    x = [v["analyst_min_per_network_day"] for v in W[key].values()]
    axes[0].plot(x, [v["dismissed_associated_share_pct"] for v in W[key].values()], mk + "-", color=col, ms=4, label=lab)
    axes[1].plot(x, [v["unassociated_alerts_per_network_day"] for v in W[key].values()], mk + "-", color=col, ms=4, label=lab)
fp = W["frozen_operating_points"]["pooled"]
for p, col in (("CG", "#A42421"), ("CG-D", "#1f77b4"), ("CG_c05", "#ff7f0e"), ("P3", "#000000")):
    for ax, y in ((axes[0], "dismissed_associated_share_pct"), (axes[1], "unassociated_alerts_per_network_day")):
        ax.plot(fp[p]["analyst_min_per_network_day"], fp[p][y], "*", ms=12, color=col, label={"CG_c05": "CG c = 0.5"}.get(p, p) if ax is axes[0] else None)
b = T["matched"]["CG_c05"]["best_P3_2t"]
for ax, y in ((axes[0], 100 * b["dismissed_associated"] / ASSOC), (axes[1], b["unassociated_alerts_per_network_day"])):
    ax.plot(MIN * b["escalations_per_network_day"], y, "D", ms=7, mfc="none", color="#000000", label="best matched two-threshold (8.0/13.5 dB)" if ax is axes[0] else None)
axes[0].set_xlabel("analyst minutes per network-day (2 min / escalation)"); axes[0].set_ylabel("dismissed reviewed-associated (%)")
axes[1].set_xlabel("analyst minutes per network-day (2 min / escalation)"); axes[1].set_ylabel("automatic alerts not associated, per network-day")
axes[0].legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(root, "figures", "fig6_workload.png"), dpi=600); plt.close(fig)
print("ok")
