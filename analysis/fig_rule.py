"""Diagram of the criteria-governed rule (Paper 1, Eqs. 1-3, Table 2), with one worked alarm computed here.

Weights, delta, theta_A, theta_D and the 30-dB scale are the manuscript's fixed values (Section 3.4, Table 2).
Writes figures/fig_rule.png (600 dpi).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = {"IM.MK31": 0.25, "II.KURK": 0.20, "G.WUS": 0.15, "SNR": 0.40}
DELTA, THETA_A, THETA_D, C = 0.45, 0.60, 0.16, 1.0

# worked alarm: nearest station MK31 out of service, KURK and WUS record but do not confirm, SNR 15 dB
state = {"IM.MK31": "MISSING", "II.KURK": "NO", "G.WUS": "NO"}
snr = 15.0
q = {k: {"YES": 1.0, "NO": C, "MISSING": 0.0}[v] for k, v in state.items()}
s = {k: 1.0 if v == "YES" else 0.0 for k, v in state.items()}
q["SNR"], s["SNR"] = 1.0, min(1.0, max(0.0, snr / 30.0))
B = sum(W[k] * q[k] for k in W)
D = sum(W[k] * s[k] * q[k] for k in W) / B if B >= DELTA else None
A = "ESCALATE" if D is None else ("ALERT" if D >= THETA_A else "DISMISS" if D <= THETA_D else "ESCALATE")
# P1 classic coincidence (Table 4): ALERT if any neighbour is YES, otherwise DISMISS (MISSING counts as NO)
classic = "ALERT" if any(v == "YES" for v in state.values()) else "DISMISS"

RED, DARK, GREY, LIGHT = "#a42421", "#242424", "#595959", "#f5f5f5"
fig, ax = plt.subplots(figsize=(6.0, 3.9))
ax.set_xlim(0, 100)
ax.set_ylim(-9, 60)
ax.axis("off")


def box(x, y, w, h, text, fc=LIGHT, ec=GREY, color=DARK, size=7.5, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=0.8", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=color, weight=weight)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=0.9))


box(1, 46, 22, 11, "Detector alarm x\nat reference station\nIU.MAKZ", weight="bold")
rows = [("IM.MK31  w = 0.25", 39), ("II.KURK  w = 0.20", 32), ("G.WUS  w = 0.15", 25), ("SNR at IU.MAKZ  w = 0.40", 18)]
for t, y in rows:
    box(1, y, 22, 5, t, size=7)
box(1, 1, 22, 13, "Each neighbour record:\nYES  \u2192 q = 1, s = 1\nNO (recorded, no trigger)\n      \u2192 q = c, s = 0\nMISSING \u2192 q = 0", size=6.8, fc="white")
for _, y in rows:
    arrow(23.8, y + 2.5, 29.6, 31)
box(30, 25, 25, 12, "Evidence sufficiency\nB(x) = \u03a3 w\u1d62 q\u1d62(x)\n= weight of valid evidence", size=7.3)
arrow(55.8, 31, 59.6, 31)
box(60, 26, 11, 10, "B(x) \u2265 \u03b4 ?\n\u03b4 = 0.45", size=7.5, weight="bold")
arrow(65.5, 25.2, 65.5, 14.6)
ax.text(66.8, 19.5, "no", fontsize=6.8, color=GREY)
box(57, 5, 17, 9, "ESCALATE\ninsufficient evidence\n(Remark 1)", fc="white", ec=RED, color=RED, size=7)
arrow(71.8, 31, 75.6, 31)
ax.text(73.7, 32.4, "yes", ha="center", fontsize=6.8, color=GREY)
box(76, 24, 23, 14, "D(x) = \u03a3 w\u1d62 s\u1d62 q\u1d62 / B(x)\nALERT if D \u2265 \u03b8$_A$ = 0.60\nDISMISS if D \u2264 \u03b8$_D$ = 0.16\nESCALATE otherwise", size=7)
box(76, 5, 23, 14, "Ledger per alarm:\nevery contribution\nw\u1d62\u1d49\u1da0\u1da0 s\u1d62 and the action,\nso each decision\ncan be reproduced", fc="white", size=6.8)
arrow(87.5, 23.2, 87.5, 19.8)
ax.text(62, 52, "MISSING carries no weight;\na NO from a working station is\nweighted by its reliability c", ha="center", va="center",
        fontsize=7.4, color=RED, style="italic")

ex = (f"Worked example, nearest station out of service: MK31 MISSING, KURK NO, WUS NO, SNR {snr:.0f} dB, c = {C:g}\n"
      f"B = {B:.2f} \u2265 \u03b4,  D = {D:.2f}  \u2192  {A};   classic coincidence P1: {classic}")
ax.add_patch(FancyBboxPatch((1, -8.2), 98, 5.4, boxstyle="round,pad=0.4,rounding_size=0.8", fc="white", ec=RED, lw=0.9))
ax.text(50, -5.5, ex, ha="center", va="center", fontsize=6.8, color=DARK, linespacing=1.4)
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
out = os.path.join(REPO, "figures/fig_rule.png")
fig.savefig(out, dpi=600)
print("written", out, "| example B", round(B, 3), "D", None if D is None else round(D, 3), A, "classic", classic)
