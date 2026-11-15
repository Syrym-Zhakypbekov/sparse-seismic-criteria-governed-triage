"""P10 figures for the repository and the manuscript, all from result files (no hand-entered numbers).
fig1_availability.png  : valid share of each station per day, tuning week and MK31 outage marked
fig2_policies.png      : unassociated automatic ALERTs, unsafe dismissals and escalations per policy (development, CV thresholds)
fig3_outage_event.gif  : a real catalogue event during the MK31 outage (ISC M3.9, 2026-09-03 02:47 UTC):
                         classic coincidence dismisses it, the availability-aware rule escalates it
Usage: python code/05_figures.py [out_dir]   (default: figures/)
Waveforms for fig3 are fetched from EarthScope FDSN (public); everything else is read from results/stage1_v3.
"""
import os, sys, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results", "stage1_v3")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
C = {"P1": "#8c8c8c", "P1t": "#4a6fa5", "P2": "#a42421", "bad": "#d9822b"}

# ---------- fig 1: availability ----------
av = pd.read_csv(os.path.join(R, "availability.csv"))
av["day"] = pd.to_datetime(av["day"])
cols = [c for c in av.columns if c.endswith("_valid_share")]
fig, ax = plt.subplots(figsize=(9, 2.8))
img = av[cols].T.to_numpy()
ax.imshow(img, aspect="auto", cmap="Greys", vmin=0, vmax=1, interpolation="nearest",
          extent=[0, len(av), len(cols) - 0.5, -0.5])
ax.set_yticks(range(len(cols)), [c.replace("_valid_share", "") for c in cols])
ticks = list(range(0, len(av), 14))
ax.set_xticks(ticks, [av.day.iloc[i].strftime("%d %b") for i in ticks])
mk = av.index[av[cols[[c.startswith("MK31") for c in cols].index(True)]] < 0.1]
if len(mk):
    ax.axvspan(mk.min(), mk.max() + 1, ymin=0, ymax=1, fill=False, ec=C["bad"], lw=1.5)
    ax.text(mk.min() + 0.5, len(cols) - 0.65, "MK31 outage", color=C["bad"], fontsize=9, va="bottom")
ax.set_title("Share of valid one-second samples per station and day (black = complete), 2026-07-08 to 09-30", fontsize=10, loc="left", pad=8)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig1_availability.png"), dpi=200); plt.close(fig)

# ---------- fig 2: policies (code/09_cg_evaluation.py) ----------
r = json.load(open(os.path.join(root, "results", "criteria_governed", "cg_evaluation.json")))
Dv = r["development"]
C.update({"P3": "#7a9a6a", "CG": "#a42421", "P2": "#c98f8d"})
names = [("P1", "P1\nclassic", C["P1"]), ("P1t", "P1t\ntuned", C["P1t"]),
         ("P3", "P3\nabstaining", C["P3"]), ("P2", "P2\ncrisp rule", C["P2"]),
         ("CG", "CG\nmodel", C["CG"])]
unassoc = [Dv[k]["all"]["alert_unassoc"] for k, _, _ in names]
unsafe_out = [Dv[k]["outage"]["missed"] for k, _, _ in names]
assoc_out = Dv["P1"]["outage"]["assoc"]
esc = [Dv[k]["all"]["esc_per_day"] for k, _, _ in names]
fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
for ax, vals, title, fmt in [(axs[0], unassoc, "Automatic alerts without\na catalogue event (85 days)", "{:d}"),
                             (axs[1], unsafe_out, f"Associated alarms dismissed\nduring the MK31 outage (of {assoc_out})", "{:d}"),
                             (axs[2], esc, "Alarms escalated to\nthe analyst per day", "{:.1f}")]:
    ax.bar(range(len(names)), vals, color=[n[2] for n in names], width=0.65)
    ax.set_xticks(range(len(names)), [n[1] for n in names], fontsize=8)
    ax.set_title(title, fontsize=9, loc="left")
    for i, v in enumerate(vals):
        ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=8)
    ax.set_yticks([])
fig.suptitle("Development period 2026-07-08 to 09-30; thresholds by five-fold contiguous-block cross-validation", fontsize=9, x=0.01, ha="left")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_policies.png"), dpi=200); plt.close(fig)

# ---------- fig 3: one real event during the outage ----------
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
t0 = UTCDateTime("2026-09-03T02:47:27")
cl = Client("https://service.earthscope.org")
rows = [("IU", "MAKZ", "00", "BHZ", "MAKZ (reference)"), ("IM", "MK31", "*", "BHZ", "MK31, 24 km"), ("II", "KURK", "00", "BHZ", "KURK, 500 km")]
traces = []
for net, sta, loc, cha, lab in rows:
    try:
        st = cl.get_waveforms(net, sta, loc, cha, t0 - 60, t0 + 180)
        st.merge(fill_value=None); tr = st[0].split()[0] if hasattr(st[0], "split") else st[0]
        tr.detrend("demean"); tr.filter("bandpass", freqmin=1, freqmax=8, corners=4, zerophase=True)
        traces.append((lab, tr.times(reftime=t0), tr.data / (np.abs(tr.data).max() or 1)))
    except Exception:
        traces.append((lab, None, None))
fig, axs = plt.subplots(len(rows) + 1, 1, figsize=(8, 5.6), gridspec_kw={"height_ratios": [1, 1, 1, 0.9]})
lines = []
for ax, (lab, t, y) in zip(axs, traces):
    ax.set_xlim(-60, 180); ax.set_yticks([]); ax.set_ylabel(lab, rotation=0, ha="right", va="center", fontsize=9)
    if t is None:
        ax.text(60, 0, "no data (station outage)", ha="center", va="center", color=C["bad"], fontsize=10)
        ax.set_ylim(-1, 1)
    else:
        ax.plot(t, y, color="#bbbbbb", lw=0.5)
        ln, = ax.plot([], [], color="#242424", lw=0.6); lines.append((ln, t, y))
    ax.axvline(0, color="#a42421", lw=0.8, ls=":")
axs[-2].set_xlabel("seconds after the MAKZ trigger, 2026-09-03 02:47:27 UTC (1-8 Hz)")
dax = axs[-1]; dax.axis("off")
cursor = [a.axvline(-60, color=C["P1t"], lw=0.8) for a in axs[:-1]]
txt = dax.text(0.0, 0.5, "", fontsize=10, va="center", family="DejaVu Sans Mono")
fig.suptitle("Catalogue event ISC M3.9 at 6.9° during the MK31 outage", fontsize=10, x=0.01, ha="left")
fig.tight_layout()
frames = np.linspace(-60, 180, 60).tolist() + [180] * 20
def draw(i):
    tc = frames[i]
    for c in cursor:
        c.set_xdata([tc, tc])
    for ln, t, y in lines:
        m = t <= tc; ln.set_data(t[m], y[m])
    if i >= 60:
        txt.set_text("Neighbours: MK31 = MISSING, KURK = NO, WUS = MISSING     SNR = 26.7 dB\n"
                     "P1 -> DISMISS   P1t -> ALERT   P3 -> ESCALATE   P2 -> ESCALATE\n"
                     "CG model: D(x) = 0.59, between thresholds -> ESCALATE (sent to the analyst)")
    return []
FuncAnimation(fig, draw, frames=len(frames), blit=False).save(os.path.join(OUT, "fig3_outage_event.gif"), writer=PillowWriter(fps=10))
draw(len(frames) - 1)
fig.savefig(os.path.join(OUT, "fig3_outage_event.png"), dpi=300)   # still image for the manuscript (≥ 1000 px)
plt.close(fig)
print("written:", sorted(os.listdir(OUT)))
