"""Forest plot of every non-inferiority contrast against P3-2t (Paper 1, #19).

Reads only existing result files:
  results/paper1/harmonised.json            (post hoc harmonised comparisons, catalogue-associated alarms)
  results/tdh2023_p1/tdh2023_p1_eval.json   (pre-registered 2023 test, analyst-reviewed events)
Writes figures/fig_forest.png (600 dpi).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = json.load(open(os.path.join(REPO, "results/paper1/harmonised.json"), encoding="utf-8"))
T = json.load(open(os.path.join(REPO, "results/tdh2023_p1/tdh2023_p1_eval.json"), encoding="utf-8"))
MARGIN = 3.0
VARIANTS = [("CG", "CG (c = 1)", "#a42421", "o"),
            ("CG c=0.5", "CG, c = 0.5", "#4a6fa5", "s"),
            ("CG-D", "CG-D (detectability)", "#7a9a6a", "D")]

rows = []  # (label, group, {variant: (diff, lo, hi)})
NAMES = {"extended IU.MAKZ": "IU.MAKZ 2025–26", "extended II.KURK": "II.KURK 2025–26",
         "2024 IU.MAKZ": "IU.MAKZ 2024", "2024 II.KURK": "II.KURK 2024", "KZ network": "KZ network", "AK network": "AK network"}
for s in NAMES:
    c = H["sets"][s]["contrasts_vs_P3_2t"]
    rows.append((NAMES[s], "post hoc, catalogue", {v: (c[f"{v} - P3-2t"]["dism_pp"], *c[f"{v} - P3-2t"]["dism_ci"]) for v, *_ in VARIANTS}))
for net, lab in [("IU.MAKZ", "IU.MAKZ 2023"), ("AK", "AK network 2023")]:
    f = T["family"]
    rows.append((lab, "pre-registered, reviewed", {v: (f[f"T1-{net}-{v}"]["diff_pp"], *f[f"T1-{net}-{v}"]["ci95_pp"]) for v, *_ in VARIANTS}))

fig, ax = plt.subplots(figsize=(7.2, 6.2))
y = 0
yt, yl = [], []
for lab, grp, d in reversed(rows):
    for k, (v, name, col, m) in enumerate(VARIANTS):
        diff, lo, hi = d[v]
        yy = y + (1 - k) * 0.24
        ax.plot([lo, hi], [yy, yy], color=col, lw=1.6)
        ax.plot(diff, yy, marker=m, color=col, ms=5.5, mec="white", mew=0.6,
                label=name if y == 0 else None)
    yt.append(y)
    yl.append(f"{lab}\n({grp})")
    y += 1
ax.axvline(0, color="#595959", lw=0.8)
ax.axvline(MARGIN, color="#242424", lw=1.2, ls="--")
ax.text(MARGIN + 0.1, y - 0.55, "non-inferiority\nmargin, 3 points", fontsize=8, va="top")
ax.axhline(1.5, color="#bababa", lw=0.8)
ax.set_yticks(yt)
ax.set_yticklabels(yl, fontsize=8)
ax.set_xlabel("Difference in dismissed associated alarms vs P3-2t (percentage points, 95% interval)", fontsize=8.5)
ax.set_xlim(-2, 11)
ax.set_ylim(-0.6, y - 0.4)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="lower right", fontsize=8, frameon=False)
ax.tick_params(axis="x", labelsize=8)
fig.tight_layout()
out = os.path.join(REPO, "figures/fig_forest.png")
fig.savefig(out, dpi=600)
print("written", out)
