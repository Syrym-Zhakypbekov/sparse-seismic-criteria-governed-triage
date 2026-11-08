"""Ten explanatory animations for the README of manuscript build v21, drawn only from result files and from the
constants of the scoring code (no hand-entered result numbers). Deterministic: no randomness is used.

gif_v21_missing_vs_no.gif      one recorded alarm; the nearest neighbour shown as YES (recorded), NO and MISSING (what-if):
                               effective weights, D(x) and the action (episode from results/extended/*/episodes.csv)
gif_v21_evidence_threshold.gif valid evidence weight sum w_i q_i against delta as neighbours drop out (Statement 1);
                               counts of all-missing episodes from extended_eval.json, kurk_ext_eval.json, ak_eval.json
gif_v21_c_tradeoff.gif         c from 1 to 0: excess dismissals vs P3 against unassociated alerts, 2024 (Table 9) and
                               2025-26 (Table 10); results/y2024/discount_sweep.json, results/posthoc/extended_discount.json
gif_v21_outage_days.gif        associated alarms dismissed on IM.MK31 outage days per policy (149 IU.MAKZ, 71 II.KURK);
                               extended_eval.json, kurk_ext_eval.json, extended_discount.json
gif_v21_mechanism_snr.gif      excess dismissals of CG over P3 by reference SNR band, with the nearest neighbour's NO share;
                               results/posthoc/mechanism_extended.json
gif_v21_base_model_tests.gif   E3, K3, N3, R3: CG - P3 intervals against the 3-point margin
gif_v21_discounted_tests.gif   D1 (two references), N5, R5, R6 pre-specified, then post-hoc variants in grey
gif_v21_alaska_table12.gif     Table 12: dismissed / unassociated alerts / escalations per day, results/ak/ak_eval.json
gif_v21_oos_costs.gif          45 cost-test combinations, lowest out-of-sample cost per episode;
                               results/posthoc/oos_operating_points.json
gif_v21_chronology.gif         plan push (repository host time) against the first run anchor of each test, anchor type
                               labelled; results/provenance/*.json, results/ak/outAK_tune/started_utc.txt
Usage: python analysis/gifs_v21.py [out_dir]   (default: figures/)
"""
import os, sys, re, json, glob, statistics
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titlesize": 11})
RED, GREY, BLUE, ORANGE, GREEN, DARK = "#a42421", "#8c8c8c", "#4a6fa5", "#d9822b", "#4f8a4b", "#242424"
DPI = 90
J = lambda *p: json.load(open(os.path.join(root, *p), encoding="utf-8"))
made = []

# frozen dismissal threshold of CG, read from the scorer of the pre-specified tests
_src = open(os.path.join(root, "analysis", "extended_eval.py"), encoding="utf-8").read()
THD = float(re.search(r"DELTA, THA, THD, FULL = [\d.]+, [\d.]+, ([\d.]+)", _src).group(1))
# model constants read from the source text of the model (importing it would re-run its analysis)
_m = open(os.path.join(root, "analysis", "criteria_governed_model.py"), encoding="utf-8").read()
W = json.loads(re.search(r"^W = (\{.*?\})", _m, re.M).group(1).replace("'", '"'))
DELTA = float(re.search(r"^DELTA = ([\d.]+)", _m, re.M).group(1))
FULL = float(re.search(r"^SNR_FULL = ([\d.]+)", _m, re.M).group(1))
THA = float(re.search(r"^THETA_A = ([\d.]+)", _m, re.M).group(1))
NB = json.loads(re.search(r"^NB = (\[.*?\])", _m, re.M).group(1))


def save(fig, frame_fn, n, name, fps=1.5, hold=3):
    """n content frames, the last held for `hold` extra frames."""
    seq = list(range(n)) + [n - 1] * hold
    anim = FuncAnimation(fig, lambda i: frame_fn(seq[i]), frames=len(seq))
    path = os.path.join(OUT, name)
    anim.save(path, writer=PillowWriter(fps=fps), dpi=DPI)
    made.append(path); plt.close(fig)


def score(states, snr, c):
    """Equations (1)-(3) for one alarm; states: neighbour -> YES/NO/MISSING."""
    q = {k: {"YES": 1.0, "NO": c, "MISSING": 0.0}[states[k]] for k in NB}
    s = {k: 1.0 if states[k] == "YES" else 0.0 for k in NB}
    q["SNR"], s["SNR"] = 1.0, min(1.0, max(0.0, snr / FULL))
    den = sum(W[k] * q[k] for k in W); num = sum(W[k] * s[k] * q[k] for k in W)
    if den < DELTA:
        return None, "ESCALATE", den, q, s
    D = num / den
    return D, ("ALERT" if D >= THA else "DISMISS" if D <= THD else "ESCALATE"), den, q, s


ACOL = {"DISMISS": RED, "ESCALATE": ORANGE, "ALERT": BLUE}

# ---------------- (a) missing vs non-confirming nearest neighbour ----------------
E = os.path.join(root, "results", "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
dirs = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")]
ep = pd.concat([pd.read_csv(os.path.join(d, "episodes.csv")) for d in dirs], ignore_index=True)
cand = ep[(ep.assoc_event >= 0) & (ep.n_MK31 == "YES") & (ep.n_KURK == "NO") & (ep.n_WUS == "NO") & ep.snr_db.between(9.5, 11.5)]
x = cand.sort_values(["snr_db", "t_on_utc"]).iloc[len(cand) // 2]
SNR_X = float(x.snr_db)
cases = [("YES", "as recorded: IM.MK31 triggered"), ("NO", "what-if: IM.MK31 recorded, no trigger"),
         ("MISSING", "what-if: IM.MK31 had no data")]
fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.35, 1]})
def fa(i):
    st_mk, label = cases[i]; states = {"MK31": st_mk, "KURK": "NO", "WUS": "NO"}
    D, a, den, q, s = score(states, SNR_X, 1.0)
    ax.clear(); bx.clear()
    labs = ["IM.MK31 24 km", "II.KURK 500 km", "G.WUS 661 km", f"SNR {SNR_X:.1f} dB"]
    keys = NB + ["SNR"]
    eff = [W[k] * q[k] / den for k in keys]; part = [W[k] * q[k] * s[k] / den for k in keys]
    ax.barh(labs, eff, color="#dddddd", label="effective weight")
    ax.barh(labs, part, color=BLUE, label="contribution to D(x)")
    for j, k in enumerate(NB):
        ax.text(0.01, j, states[k], va="center", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 0.75); ax.invert_yaxis(); ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.set_title(label, loc="left")
    bx.set_xlim(0, 1); bx.set_ylim(0, 1); bx.set_yticks([])
    bx.axvspan(0, THD, color=RED, alpha=0.12); bx.axvspan(THD, THA, color=ORANGE, alpha=0.10); bx.axvspan(THA, 1, color=BLUE, alpha=0.10)
    bx.text(THD / 2, 0.9, "DISMISS", ha="center", color=RED, fontsize=9)
    bx.text((THD + THA) / 2, 0.9, "ESCALATE", ha="center", color=ORANGE, fontsize=9)
    bx.text((THA + 1) / 2, 0.9, "ALERT", ha="center", color=BLUE, fontsize=9)
    bx.plot([D], [0.45], "o", ms=14, color=ACOL[a])
    bx.text(D, 0.25, f"D(x) = {D:.3f}\n{a}", ha="center", fontsize=11, color=ACOL[a], fontweight="bold")
    bx.set_xlabel(f"D(x); θ_D = {THD:g}, θ_A = {THA:g}")
    bx.set_title(f"valid evidence Σwq = {den:.2f}", loc="left")
    fig.suptitle(f"One catalogue-associated alarm, {x.t_on_utc[:16].replace('T', ' ')} UTC (c = 1): "
                 "a missing record and a non-confirmation differ", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
save(fig, fa, len(cases), "gif_v21_missing_vs_no.gif", fps=0.8, hold=2)

# ---------------- (b) evidence threshold delta (Statement 1) ----------------
ee, kk, ak = J("results", "extended", "extended_eval.json"), J("results", "kurk_ext", "kurk_ext_eval.json"), J("results", "ak", "ak_eval.json")
cfgs = [({"MK31": "YES", "KURK": "NO", "WUS": "NO"}, 1.0), ({"MK31": "MISSING", "KURK": "NO", "WUS": "NO"}, 1.0),
        ({"MK31": "MISSING", "KURK": "MISSING", "WUS": "NO"}, 1.0), ({"MK31": "MISSING", "KURK": "MISSING", "WUS": "MISSING"}, 1.0),
        ({"MK31": "NO", "KURK": "NO", "WUS": "NO"}, 0.5), ({"MK31": "NO", "KURK": "NO", "WUS": "NO"}, 0.0)]
fig, ax = plt.subplots(figsize=(10.5, 4.2))
def fb(i):
    ax.clear()
    for j, (st, c) in enumerate(cfgs[: i + 1]):
        D, a, den, q, s = score(st, 12.0, c)
        left = 0.0
        for k, col in zip(NB + ["SNR"], [BLUE, "#7d97c0", "#b4c3dc", GREY]):
            w = W[k] * q[k]; ax.barh(j, w, left=left, color=col, edgecolor="white"); left += w
        tag = " / ".join(f"{k} {st[k][:4]}" for k in NB) + f"   c = {c:g}"
        ax.text(-0.01, j, tag, ha="right", va="center", fontsize=9)
        ax.text(den + 0.01, j, ("no decision (⊥) → ESCALATE" if D is None else f"Σwq = {den:.2f}, decision possible"),
                va="center", fontsize=9, color=ORANGE if D is None else DARK)
    ax.axvline(DELTA, color=RED, ls="--"); ax.text(DELTA + 0.01, -0.7, f"δ = {DELTA:g}", color=RED, ha="left", fontsize=10)
    ax.axvline(W["SNR"], color=GREY, ls=":", lw=1); ax.text(W["SNR"] - 0.01, -0.7, f"w_SNR = {W['SNR']:g}", color=GREY, ha="right", fontsize=9)
    ax.set_xlim(0, 1.45); ax.set_ylim(len(cfgs) - 0.3, -1.0); ax.set_yticks([])
    ax.set_xlabel("valid evidence weight Σ wᵢ qᵢ (blue: neighbours, grey: SNR at the reference)")
    ax.set_title("Statement 1: δ > w_SNR, so without any valid neighbour record no automatic decision is made. "
                 f"All-missing episodes escalated: IU.MAKZ 2025-26 {ee['E4']['escalated']} of {ee['E4']['all_missing_episodes']}, "
                 f"II.KURK {kk['K4']['escalated']} of {kk['K4']['all_missing_episodes']}, Alaska {ak['R4_all_missing_escalated']['CG_escalated']} of "
                 f"{ak['R4_all_missing_escalated']['episodes']}", loc="left", fontsize=9.5, wrap=True)
    fig.subplots_adjust(left=0.33, right=0.98, top=0.82, bottom=0.14)
save(fig, fb, len(cfgs), "gif_v21_evidence_threshold.gif", fps=1.2, hold=3)

# ---------------- (c) c sweep: excess dismissals vs unassociated alerts ----------------
sw, ph = J("results", "y2024", "discount_sweep.json"), J("results", "posthoc", "extended_discount.json")
ckeys = ["c=1.0", "c=0.75", "c=0.5", "c=0.25", "c=0.0"]
series = [("2024, IU.MAKZ (Table 9)", sw["MAKZ"], BLUE, "o"), ("2024, II.KURK (Table 9)", sw["KURK"], "#7d97c0", "s"),
          ("2025-26, IU.MAKZ (Table 10)", ph["MAKZ"], RED, "o"), ("2025-26, II.KURK (Table 10)", ph["KURK"], ORANGE, "s")]
fig, ax = plt.subplots(figsize=(10, 4.6))
def fc(i):
    ax.clear()
    for lab, d, col, mk in series:
        xs = [d[k]["diff_vs_P3_pp"] for k in ckeys[: i + 1]]; ys = [d[k]["alert_unassoc"] for k in ckeys[: i + 1]]
        ax.plot(xs, ys, "-", color=col, lw=1.5, marker=mk, label=lab)
        ax.text(xs[-1] + 0.15, ys[-1], f"c={float(ckeys[i][2:]):g}", fontsize=8, color=col, va="center")
        ax.plot([0], [d["P3"]["alert_unassoc"]], marker="_", ms=22, color=col)
    ax.axvline(3, color=GREY, ls="--"); ax.text(3.1, 7000, "margin 3 pp", color=GREY, fontsize=9)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlim(-3.5, 11); ax.set_ylim(0, 7800)
    ax.set_xlabel("excess dismissed associated alarms vs P3, percentage points (point estimate)")
    ax.set_ylabel("unassociated alerts")
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.text(-3.4, 300, "dashes at x = 0: unassociated alerts of P3 in the same data", fontsize=8, color=GREY)
    ax.set_title("Lowering the weight c of a non-confirmation: fewer dismissals, more alerts and escalations (post hoc)",
                 loc="left", fontsize=10)
    ax.text(10.8, 4600, f"c = {float(ckeys[i][2:]):g}", fontsize=16, ha="right", color=DARK, fontweight="bold")
    fig.tight_layout()
save(fig, fc, len(ckeys), "gif_v21_c_tradeoff.gif", fps=1.2, hold=3)

# ---------------- (d) outage days: waffle of associated outage alarms ----------------
ou_m, ou_k = ee["outage_usable"], kk["outage"]
pol = [("P1 classic coincidence", ou_m["P1"]["missed"], ou_k["P1"]["missed"]),
       ("P1t tuned coincidence", ou_m["P1t"]["missed"], ou_k["P1t"]["missed"]),
       ("P2 crisp availability rule", ou_m["P2"]["missed"], ou_k["P2"]["missed"]),
       ("P3 abstaining, availability-blind", ou_m["P3"]["missed"], ou_k["P3"]["missed"]),
       ("CG, c = 1 (pre-specified E1, K1)", ou_m["CG"]["missed"], ou_k["CG"]["missed"]),
       ("CG-D (post hoc replay, Table 10)", ph["MAKZ"]["CG-D table"]["missed_outage"], ph["KURK"]["CG-D table"]["missed_outage"])]
NM, NK = ou_m["P1"]["assoc"], ou_k["P1"]["assoc"]
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [15, 11]})
def waffle(a, n, k, cols, title):
    a.clear(); rows = int(np.ceil(n / cols))
    for j in range(n):
        a.add_patch(plt.Rectangle((j % cols, rows - 1 - j // cols), 0.86, 0.86, color=RED if j < k else "#d9d9d9"))
    a.set_xlim(-0.2, cols + 0.1); a.set_ylim(-0.2, rows + 0.1); a.set_aspect("equal"); a.axis("off")
    a.set_title(title, loc="left", fontsize=10)
def fd(i):
    name, km, kk_ = pol[i]
    waffle(axs[0], NM, km, 15, f"reference IU.MAKZ: {km} of {NM} dismissed")
    waffle(axs[1], NK, kk_, 11, f"reference II.KURK: {kk_} of {NK} dismissed")
    fig.suptitle(f"{name}\nAssociated alarms on IM.MK31 outage days, Jan 2025 - Jun 2026; red = dismissed automatically\n"
                 "(cells show counts, not specific alarms)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.80))
save(fig, fd, len(pol), "gif_v21_outage_days.gif", fps=0.8, hold=2)

# ---------------- (e) mechanism: excess dismissals by SNR band ----------------
me = J("results", "posthoc", "mechanism_extended.json")
bins = ["<5", "5-10", "10-15", "15-20", ">=20"]
near = {"MAKZ": ("MK31", "IM.MK31"), "KURK": ("MAKZ", "IU.MAKZ")}
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
def fe(i):
    for a, ref in zip(axs, ["MAKZ", "KURK"]):
        a.clear(); d = me[ref]; nb, nbname = near[ref]; v = d["neighbours"][nb]
        h = [d["excess_ref_snr_bins"][b] if j <= i else 0 for j, b in enumerate(bins)]
        a.bar(range(len(bins)), h, color=RED)
        for j, b in enumerate(bins[: i + 1]):
            a.text(j, h[j] + 3, f"{h[j]}", ha="center", fontsize=10)
            a.text(j, -24, f"{v['by_snr_bin'][b]['no_share']:.0%}\n(n={v['by_snr_bin'][b]['n']})", ha="center", fontsize=8, color=BLUE)
        a.set_xticks(range(len(bins)), [b + " dB" for b in bins]); a.set_ylim(-34, 140)
        a.set_title(f"reference {'IU.MAKZ' if ref == 'MAKZ' else 'II.KURK'}: {d['excess_dismissals']} excess dismissals\n"
                    f"blue: share {nbname} ({v['distance_km']:.0f} km) did not confirm", loc="left", fontsize=10)
        a.set_xlabel("reference SNR band", fontsize=10)
    axs[0].set_ylabel("dismissed by CG, not by P3")
    fig.suptitle("Where the excess dismissals of E3 and K3 lie (post hoc): weak alarms (5-15 dB) "
                 "that neighbours did not confirm", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
save(fig, fe, len(bins), "gif_v21_mechanism_snr.gif", fps=1.2, hold=3)

# ---------------- (f) and (g) forest plots against the margin ----------------
kz, y24, r12 = J("results", "kz", "kz_eval.json"), J("results", "y2024", "cgd_2024_eval.json"), J("results", "posthoc", "r12_checks.json")
def forest(rows, name, title, xmax):
    fig, ax = plt.subplots(figsize=(10, 0.62 * len(rows) + 1.7))
    def f(i):
        ax.clear()
        for j, (lab, d, ci, ok, col) in enumerate(rows[: i + 1]):
            ax.plot(ci, [j, j], color=col, lw=3); ax.plot(d, j, "o", color=col, ms=8)
            ax.text(1.01, j, ("met" if ok else "not established"), transform=ax.get_yaxis_transform(), ha="left",
                    va="center", fontsize=10, color=GREEN if ok else RED, fontweight="bold")
            ax.text(ci[0], j - 0.3, f"{d:+.2f} [{ci[0]:.2f}, {ci[1]:.2f}]", fontsize=8.5, color=col)
        ax.axvline(3, color=GREY, ls="--"); ax.axvline(0, color="k", lw=0.6)
        ax.text(3.05, -0.75, "margin 3 pp", color=GREY, fontsize=9)
        ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.set_ylim(len(rows) - 0.4, -1.0)
        ax.set_xlim(-1.0, xmax); ax.set_xlabel("excess dismissed associated alarms vs P3, percentage points, 95% day bootstrap")
        ax.set_title(title, loc="left", fontsize=10.5)
        fig.tight_layout(rect=(0, 0, 0.86, 1))
    save(fig, f, len(rows), name, fps=1.0, hold=3)

b = [("E3  IU.MAKZ 2025-26, 546 d", ee["E3"]), ("K3  II.KURK 2025-26, 546 d", kk["K3"]),
     ("N3  KZ network 2024-25, 632 d", kz["N3_CG_noninferiority"]), ("R3  AK network (Alaska) 2024-25, 540 d", ak["R3_CG_noninferiority"])]
rows = [(lab, v["diff_pp"], v["ci95_pp"], v["ci95_pp"][1] < 3, RED if v["ci95_pp"][1] >= 3 else BLUE) for lab, v in b]
forest(rows, "gif_v21_base_model_tests.gif", "Base model CG (c = 1) against the abstaining rule P3: pre-specified non-inferiority tests", 13.5)

g = [("D1  CG-D, IU.MAKZ 2024", y24["MAKZ"]["D1"]), ("D1  CG-D, II.KURK 2024", y24["KURK"]["D1"]),
     ("N5  CG-D, KZ network 2024-25", kz["N5_CGD_noninferiority"]), ("R5  CG-D, Alaska 2024-25", ak["R5_CGD_noninferiority"]),
     ("R6  c = 0.5, Alaska 2024-25", ak["R6_constant_c05_noninferiority"])]
rows = [(lab, v["diff_pp"], v["ci95_pp"], v["ci95_pp"][1] < 3, BLUE) for lab, v in g]
kzc = r12["B_KZ_constant_c"]["CG(c=0.5)"]["block_bootstrap"]
for lab, d in [("post hoc  CG-D, IU.MAKZ 2025-26", ph["MAKZ"]["CG-D table"]), ("post hoc  CG-D, II.KURK 2025-26", ph["KURK"]["CG-D table"])]:
    rows.append((lab, d["diff_vs_P3_pp"], d["ci95"], d["ci95"][1] < 3, GREY))
rows.append(("post hoc  c = 0.5, KZ network (1-day blocks)", kzc["point_pp"], kzc["block_1d"], kzc["block_1d"][1] < 3, GREY))
forest(rows, "gif_v21_discounted_tests.gif", "Discounted variants against P3: pre-specified tests (blue), post-hoc analyses (grey)", 5.5)

# ---------------- (h) Alaska Table 12 ----------------
al = ak["all"]; c05 = ak["constant_c05"]["all"]
pols = [("P1", al["P1"]), ("P1t", al["P1t"]), ("P3", al["P3"]), ("P2", al["P2"]), ("CG", al["CG"]), ("CG-D", al["CG-D"]), ("CG, c = 0.5", c05)]
fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.0), sharey=True)
def fh(i):
    for a, key, lab, col, xm in zip(axs, ["missed", "alert_unassoc", "esc_per_day"],
                                    [f"dismissed associated (of {al['CG']['assoc']})", "unassociated alerts", "escalations per day"],
                                    [RED, BLUE, ORANGE], [200, 16000, 28]):
        a.clear()
        names = [p[0] for p in pols]; vals = [p[1][key] if j <= i else 0 for j, p in enumerate(pols)]
        a.barh(names, vals, color=[col if j <= i else "none" for j in range(len(pols))])
        for j in range(i + 1):
            a.text(vals[j] + xm * 0.02, j, f"{vals[j]:,.0f}" if key != "esc_per_day" else f"{vals[j]:.1f}", va="center", fontsize=9)
        a.set_xlim(0, xm); a.set_title(lab, loc="left", fontsize=10)
    axs[0].invert_yaxis()
    fig.suptitle(f"Alaska (AK network), {ak['calendar_days']} days, {al['CG']['episodes']:,} episodes, pre-specified (Table 12)",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
save(fig, fh, len(pols), "gif_v21_alaska_table12.gif", fps=1.5, hold=3)

# ---------------- (i) out-of-sample costs ----------------
oos = J("results", "posthoc", "oos_operating_points.json")
tests = list(oos["tests"]); costs = [f"rm{c['r_missed']}_re{c['r_escalation']}" for c in oos["costs"]]
win, rel = {}, []
for t in tests:
    cc = oos["tests"][t]["cost"]
    for ck in costs:
        fam = {k.split("|")[1]: v["cost_per_ep"] for k, v in cc.items() if k.split("|")[0] == ck}
        m = min(fam.values()); w = sorted(f for f, v in fam.items() if abs(v - m) < 1e-12)
        win[(t, ck)] = w
        if "P3" in w:
            rel.append((min(v for f, v in fam.items() if f.startswith("CG")) / m - 1) * 100)
cells = [(t, ck) for ck in costs for t in tests]
n_p3 = sum("P3" in w for w in win.values()); n_cg = sum(all(f.startswith("CG") for f in w) for w in win.values())
fig, ax = plt.subplots(figsize=(10.5, 5.2))
def fi(i):
    ax.clear(); shown = cells[: (i + 1) * len(tests)]
    for (t, ck) in shown:
        x0, y0 = tests.index(t), costs.index(ck); w = win[(t, ck)]
        col = GREY if "P3" in w else BLUE
        ax.add_patch(plt.Rectangle((x0, y0), 0.94, 0.9, color=col))
        ax.text(x0 + 0.47, y0 + 0.45, " = ".join(w), ha="center", va="center", fontsize=8, color="white")
    ax.set_xlim(0, len(tests)); ax.set_ylim(len(costs), 0)
    ax.set_xticks(np.arange(len(tests)) + 0.47, tests, fontsize=9)
    ax.set_yticks(np.arange(len(costs)) + 0.45,
                  [f"miss {c['r_missed']}, escalation {c['r_escalation']}" for c in oos["costs"]], fontsize=8.5)
    ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
    done = len(shown) == len(cells)
    tail = (f"P3 (tied with P2) lowest in {n_p3} of {len(cells)}, a criteria-governed variant in {n_cg}; where P3 was lowest,\n"
            f"the best CG variant cost a median {statistics.median(rel):.1f}% more per episode") if done else "\n"
    fig.suptitle("Lowest out-of-sample cost per episode (post hoc; operating points chosen on development;\n"
                 "illustrative costs in units of one unassociated alert)\n" + tail, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
save(fig, fi, len(costs), "gif_v21_oos_costs.gif", fps=2.0, hold=4)

# ---------------- (j) chronology: plan push vs first run anchor ----------------
tl = J("results", "provenance", "prespecification_timeline.json")
hosts = J("results", "provenance", "ak_host_activity.json")
by = {r["document"]: r for r in tl["rows"]}
ts = lambda s: pd.Timestamp(s)
rows = []
def add(lab, doc, run, kind):
    r = by[doc]; rows.append((lab, r["github_push_utc"], r["runs"][run]["time"], kind))
add("held-out plan (3 policies)", "PREREGISTRATION (held-out)", "heldout_kaggle_version_created", "platform creation time")
add("E1-E4 extended test", "PREREGISTRATION_EXTENDED", "extended_MAKZ_vm_created", "platform creation time")
add("K1-K4 II.KURK", "PREREGISTRATION_KURK_EXTENDED", "kurk_extended_first_chunk", "file modification time (VM)")
add("D1-D4 2024 test", "PREREGISTRATION_DETECTABILITY_2024", "y2024_MAKZ_first_chunk", "file modification time (VM)")
add("N1-N5 KZ network", "PREREGISTRATION_KZ_NETWORK", "kz_tuning_first_file", "file modification time (VM)")
ak_push = [r for r in hosts["records"] if r["after"].startswith("6825835")][0]["timestamp"]
ak_run = open(os.path.join(root, "results", "ak", "outAK_tune", "started_utc.txt"), encoding="utf-8").read().strip()
rows.append(("R1-R6 Alaska", ak_push, ak_run, "run-script launch time (authors' machine)"))
sc = by["CG-D scorer 3e0f2f3 (D1-D4 computation)"]
rows.append(("D1-D4 scorer (3e0f2f3) vs last IU.MAKZ 2024 file", sc["github_push_utc"], sc["runs"]["y2024_MAKZ_last_file"]["time"], "file modification time (VM)"))
KCOL = {"platform creation time": BLUE, "file modification time (VM)": ORANGE, "run-script launch time (authors' machine)": GREEN}
fig, ax = plt.subplots(figsize=(10.5, 4.9))
def fj(i):
    ax.clear()
    for j, (lab, p, r, kind) in enumerate(rows[: i + 1]):
        dt = (ts(r) - ts(p)).total_seconds()
        ax.barh(j, dt, color=KCOL[kind], height=0.6)
        ax.text(dt + (6 if dt >= 0 else -6), j, (f"+{dt:.0f} s" if abs(dt) < 120 else f"+{dt / 60:.1f} min") if dt >= 0 else f"{dt:.0f} s",
                va="center", ha="left" if dt >= 0 else "right", fontsize=9)
    ax.set_xscale("symlog", linthresh=10); ax.set_xlim(-200, 6000); ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9); ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlabel("seconds from push (GitHub server time) to run anchor; negative = anchor before push", fontsize=10)
    from matplotlib.patches import Patch
    if not fig.legends:
        fig.legend(handles=[Patch(color=col, label=k) for k, col in KCOL.items()], fontsize=9, frameon=False,
                   loc="lower left", ncol=3, title="run anchor:", title_fontsize=9, alignment="left")
    ax.set_title("Plan push vs run anchor, 7 November 2026 (same-day pre-specification, private repository)",
                 loc="left", fontsize=10)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
save(fig, fj, len(rows), "gif_v21_chronology.gif", fps=1.2, hold=3)

for m in made: print(os.path.relpath(m, root), os.path.getsize(m) // 1024, "KB")
print("example alarm (a):", x.t_on_utc, "snr", round(SNR_X, 2), "assoc_event", int(x.assoc_event), "theta_D", THD)
print("oos:", n_p3, n_cg, round(statistics.median(rel), 2), round(min(rel), 2), round(max(rel), 2))
