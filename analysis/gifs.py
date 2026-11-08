"""Animated figures for the repository README, drawn only from result files (no hand-entered numbers).
gif_discount_sweep.gif      : c from 1 to 0 on the 2025-26 periods (results/posthoc/extended_discount.json):
                              excess dismissals vs P3 with 95% interval and the 3-point margin, alerts, escalations
gif_availability_546.gif    : daily valid-data share of the four stations over the 546 extended days, outage days marked
gif_weak_alarms.gif         : share of associated alarms a neighbour did NOT confirm, by reference SNR
                              (results/posthoc/mechanism_extended.json)
gif_one_alarm.gif           : one real associated alarm that CG dismissed and P3 escalated: the score D(x) under
                              c = 1, c = 0.5 and with the nearest neighbour missing (values from its episode row)
gif_prespec_timeline.gif    : server-side push time of each plan against the start of its run
                              (results/provenance/prespecification_timeline.json)
Usage: python code/29_gifs.py [out_dir]   (default: figures/)
"""
import os, sys, json, glob
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
RED, GREY, BLUE, ORANGE = "#a42421", "#8c8c8c", "#4a6fa5", "#d9822b"
J = lambda *p: json.load(open(os.path.join(root, *p), encoding="utf-8"))
made = []


def save(anim, name, fps=1):
    path = os.path.join(OUT, name); anim.save(path, writer=PillowWriter(fps=fps)); made.append(path); plt.close("all")


# ---------- 1: discount sweep on the periods of the failed tests ----------
ph = J("results", "posthoc", "extended_discount.json")
keys = ["c=1.0", "c=0.75", "c=0.5", "c=0.25", "c=0.0"]
fig, axes = plt.subplots(2, 3, figsize=(10, 5.4))
def frame1(i):
    for r, ref in enumerate(["MAKZ", "KURK"]):
        d = ph[ref]; p3 = d["P3"]
        cs = [float(k[2:]) for k in keys[: i + 1]]
        diff = [d[k]["diff_vs_P3_pp"] for k in keys[: i + 1]]
        lo = [d[k]["diff_vs_P3_pp"] - d[k]["ci95"][0] for k in keys[: i + 1]]
        hi = [d[k]["ci95"][1] - d[k]["diff_vs_P3_pp"] for k in keys[: i + 1]]
        al = [d[k]["alert_unassoc"] for k in keys[: i + 1]]; es = [d[k]["esc_per_day"] for k in keys[: i + 1]]
        a0, a1, a2 = axes[r]
        for a in (a0, a1, a2): a.clear(); a.set_xlim(1.08, -0.08); a.set_xlabel("weight of a non-confirmation, c")
        a0.errorbar(cs, diff, yerr=[lo, hi], fmt="o-", color=RED, capsize=3)
        a0.axhline(3, color=GREY, ls="--", lw=1); a0.axhline(0, color="k", lw=0.6)
        a0.text(1.05, 3.2, "margin 3 pp", color=GREY, fontsize=8); a0.set_ylim(-4, 12.5)
        a0.set_ylabel(f"{ref}\nexcess dismissed vs P3, pp")
        a1.plot(cs, al, "o-", color=BLUE); a1.axhline(p3["alert_unassoc"], color=GREY, ls="--", lw=1)
        a1.text(1.05, p3["alert_unassoc"] * 0.97, "P3", color=GREY, fontsize=8, va="top"); a1.set_ylim(0, 8000)
        a1.set_ylabel("unassociated alerts")
        a2.plot(cs, es, "o-", color=ORANGE); a2.axhline(p3["esc_per_day"], color=GREY, ls="--", lw=1)
        a2.text(1.05, p3["esc_per_day"] - 0.4, "P3", color=GREY, fontsize=8, va="top"); a2.set_ylim(8, 24)
        a2.set_ylabel("escalations per day")
    fig.suptitle(f"Discounting a neighbour's non-confirmation, January 2025 - June 2026 (post hoc): c = {float(keys[i][2:]):g}",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
save(FuncAnimation(fig, lambda i: frame1(min(i, len(keys) - 1)), frames=len(keys) + 2), "gif_discount_sweep.gif", fps=1)

# ---------- 2: availability over 546 days ----------
E = os.path.join(root, "results", "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
dirs = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")]
av = pd.concat([pd.read_csv(os.path.join(d, "availability.csv")) for d in dirs]).drop_duplicates("day").sort_values("day").reset_index(drop=True)
cols = ["MAKZ_valid_share", "MK31_valid_share", "KURK_valid_share", "WUS_valid_share"]
img = av[cols].T.to_numpy(); n = len(av); out_days = av.index[av.MK31_valid_share < 0.1]
fig, ax = plt.subplots(figsize=(10, 2.9))
steps = list(range(30, n, 30)) + [n] * 3
def frame2(i):
    k = steps[i]; ax.clear()
    m = np.full_like(img, np.nan, dtype=float); m[:, :k] = img[:, :k]
    ax.imshow(m, aspect="auto", cmap="Greys", vmin=0, vmax=1, interpolation="nearest", extent=[0, n, 3.5, -0.5])
    ax.set_yticks(range(4), [c.split("_")[0] for c in cols])
    t = list(range(0, n, 61)); ax.set_xticks(t, [av.day.iloc[j][:7] for j in t])
    o = out_days[out_days < k]
    for j in o: ax.axvspan(j, j + 1, ymin=0.5, ymax=0.75, color=ORANGE, alpha=0.9, lw=0)
    ax.set_title(f"Valid data per station and day, {av.day.iloc[0]} to {av.day.iloc[k - 1]} · IM.MK31 outage days so far: {len(o)} (orange)",
                 fontsize=10, loc="left")
    fig.tight_layout()
save(FuncAnimation(fig, frame2, frames=len(steps)), "gif_availability_546.gif", fps=2)

# ---------- 3: weak alarms are often not confirmed ----------
me = J("results", "posthoc", "mechanism_extended.json")
bins = ["5-10", "10-15", "15-20", ">=20"]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
order = [(r, k) for r in ["MAKZ", "KURK"] for k in me[r]["neighbours"]]
def frame3(i):
    shown = order[: i + 1]
    for a, ref in zip(axes, ["MAKZ", "KURK"]):
        a.clear(); a.set_ylim(0, 1); a.set_xticks(range(len(bins)), [b + " dB" for b in bins])
        a.axvspan(-0.5, 1.5, color=RED, alpha=0.07)
        a.text(0.5, 0.95, "all excess dismissals\nof CG lie here", ha="center", va="top", fontsize=8, color=RED)
        for j, (r, k) in enumerate([x for x in shown if x[0] == ref]):
            v = me[ref]["neighbours"][k]
            y = [v["by_snr_bin"][b]["no_share"] for b in bins]
            a.plot(range(len(bins)), y, "o-", color=[BLUE, ORANGE, GREY][j], label=f"{k}, {v['distance_km']:.0f} km")
        a.set_title(f"reference {ref}: {me[ref]['excess_dismissals']} excess dismissals", fontsize=10, loc="left")
        a.set_xlabel("reference SNR"); a.legend(fontsize=8, loc="upper right", frameon=False, bbox_to_anchor=(1, 0.8))
    axes[0].set_ylabel("share of catalogue-associated alarms\nthe neighbour did NOT confirm")
    fig.suptitle("A valid 'no' is weak evidence for weak alarms, even at 24 km (2025 - June 2026)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
save(FuncAnimation(fig, lambda i: frame3(min(i, len(order) - 1)), frames=len(order) + 2), "gif_weak_alarms.gif", fps=1)

# ---------- 4: one real alarm under three treatments ----------
ep = pd.concat([pd.read_csv(os.path.join(d, "episodes.csv")) for d in dirs], ignore_index=True)
NB, W = ["MK31", "KURK", "WUS"], {"MK31": 0.25, "KURK": 0.20, "WUS": 0.15, "SNR": 0.40}
cand = ep[(ep.assoc_event >= 0) & (ep.n_MK31 == "NO") & (ep.n_KURK == "NO") & (ep.n_WUS == "NO") & ep.snr_db.between(8, 12)]
x = cand.sort_values("snr_db").iloc[len(cand) // 2]
def score(states, c):
    num = den = 0.0
    contrib = {}
    for k in NB:
        q = {"YES": 1.0, "NO": c, "MISSING": 0.0}[states[k]]; s = 1.0 if states[k] == "YES" else 0.0
        num += W[k] * s * q; den += W[k] * q; contrib[k] = (W[k] * q, W[k] * s * q)
    s4 = min(1, max(0, x.snr_db / 30)); num += W["SNR"] * s4; den += W["SNR"]; contrib["SNR"] = (W["SNR"], W["SNR"] * s4)
    D = num / den if den >= 0.45 else None
    act = "ESCALATE" if D is None else ("ALERT" if D >= 0.60 else ("DISMISS" if D <= 0.16 else "ESCALATE"))
    return D, act, contrib, den
cases = [("All three neighbours recorded and did not trigger, c = 1 (CG)", {k: "NO" for k in NB}, 1.0),
         ("Same records, a non-confirmation weighted c = 0.5", {k: "NO" for k in NB}, 0.5),
         ("If IM.MK31 had no data (MISSING), c = 1", {"MK31": "MISSING", "KURK": "NO", "WUS": "NO"}, 1.0)]
fig, ax = plt.subplots(figsize=(9, 3.6))
def frame4(i):
    title, st, c = cases[min(i, len(cases) - 1)]; D, act, contrib, den = score(st, c); ax.clear()
    labs = ["MK31 24 km", "KURK 500 km", "WUS 661 km", f"SNR {x.snr_db:.1f} dB"]
    eff = [contrib[k][0] / den for k in NB + ["SNR"]]; part = [contrib[k][1] / den for k in NB + ["SNR"]]
    ax.barh(labs, eff, color="#dddddd", label="effective weight")
    ax.barh(labs, part, color=BLUE, label="contribution to D(x)")
    for j, k in enumerate(NB): ax.text(0.01, j, st[k], va="center", fontsize=9)
    ax.set_xlim(0, 1); ax.invert_yaxis(); ax.legend(loc="lower right", fontsize=8, frameon=False)
    col = {"DISMISS": RED, "ESCALATE": ORANGE, "ALERT": BLUE}[act]
    ax.set_title(f"{title}\nD(x) = {D:.2f} -> {act}   (dismiss <= 0.16, alert >= 0.60)", fontsize=10, loc="left", color=col)
    fig.tight_layout()
save(FuncAnimation(fig, frame4, frames=len(cases) + 1), "gif_one_alarm.gif", fps=0.5)

# ---------- 5: pre-specification timeline ----------
tl = J("results", "provenance", "prespecification_timeline.json")
rows = [r for r in tl["rows"] if r["runs"] and "scorer" not in r["document"]]
t0 = pd.Timestamp("2026-11-07T10:00:00Z")
fig, ax = plt.subplots(figsize=(10, 3.6))
def frame5(i):
    ax.clear()
    for j, r in enumerate(rows[: i + 1]):
        p = (pd.Timestamp(r["github_push_utc"]) - t0).total_seconds() / 60
        ax.plot(p, j, "D", color=BLUE)
        for k, v in r["runs"].items():
            s = (pd.Timestamp(v["time"]) - t0).total_seconds() / 60
            ax.plot(s, j, "o", color=RED); ax.plot([p, s], [j, j], color=GREY, lw=1)
        ax.text(p - 2, j, r["document"].replace("PREREGISTRATION", "plan").replace("_", " "), ha="right", va="center", fontsize=8)
    ax.set_yticks([]); ax.set_xlim(-60, 260); ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlabel("minutes after 10:00 UTC, 7 November 2026")
    ax.plot([], [], "D", color=BLUE, label="plan pushed (GitHub server time)"); ax.plot([], [], "o", color=RED, label="first output of the run")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.set_title("Every plan reached the repository host before its run started", fontsize=10, loc="left")
    fig.tight_layout()
save(FuncAnimation(fig, lambda i: frame5(min(i, len(rows) - 1)), frames=len(rows) + 2), "gif_prespec_timeline.gif", fps=1)

for m in made: print(m, os.path.getsize(m) // 1024, "KB")
print("example alarm:", x.t_on_utc, "snr", round(float(x.snr_db), 2), "assoc", int(x.assoc_event))
