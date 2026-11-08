"""Sensitivity of the reviewed-bulletin verdicts to the hand-set weights and thresholds, and ablations of the sufficiency
constraint (delta) and of the reject band. Plan: PLAN_SENSITIVITY_WEIGHTS_2026-11-08.md (pushed before computing).

Inputs: results/posthoc/_collect_reviewed.pkl (analysis/posthoc_collect.py; the 33 reviewed-label networks of
results/v2_reviewed/v2_eval_reviewed.json). Nothing in pipeline/ is used or changed.
Outputs: results/sensitivity/sens_weights.json, results/sensitivity/ablations.json, figures/fig_sens_weights.png.
"""
import os, sys, json, itertools, importlib.util, time
import numpy as np, pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "results", "sensitivity"); os.makedirs(OUT, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


v2 = _load("v2_sens", os.path.join(here, "v2_networks.py"))
sys.path.insert(0, here)
from posthoc_collect import collect

SEED, MARGIN, RATIO_MAX = 7, 3.0, 1.5
FROZEN = dict(w=0.40, g=1, delta=0.45, ta=0.60, td=0.16)
POLS = ["CG", "CG_c05", "CG-D"]


def site_weights(w, g):
    raw = np.array([0.20 + g * 0.05, 0.20, 0.20 - g * 0.05])
    # rounded so the frozen point gives exactly 0.25 / 0.20 / 0.15 (float noise flipped 11 boundary episodes)
    return np.round(raw / raw.sum() * (1.0 - w), 12)


def prep(rows):
    """Per network: precomputed q-components independent of parameters."""
    nets = {}
    for k, v in rows.items():
        if not v.get("included"): continue
        S = v["S"][:3]; snr = v["snr"]; ok = v["ok"]
        b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), v2.BINS, labels=v2.LAB).astype(str).to_numpy()
        comp = []
        for r, s in enumerate(S):
            tab = v2.TAB.get("MAKZ", {}).get(v2.DEV_ROLE_BY_RANK[r], {})
            p = np.array([tab.get(x, {"p": 0.5})["p"] if x in v2.LAB else 0.5 for x in b])
            comp.append((s == "YES", s == "NO", np.isin(s, ["YES", "NO"]), p))
        nets[k] = dict(comp=comp, snrterm=np.clip(snr / 30, 0, 1) * ok, ok=ok.astype(float),
                       days=np.asarray(v["days"]), assoc=np.asarray(v["assoc"], bool), act=v["act"])
    return nets


def actions(N, pol, w, g, delta, ta, td, single=None):
    ws = site_weights(w, g); n = len(N["ok"]); num = np.zeros(n); den = np.zeros(n)
    for r, (yes, no, valid, p) in enumerate(N["comp"]):
        q = valid.astype(float)
        if pol == "CG-D": q = np.where(no, p, q)
        if pol == "CG_c05": q = np.where(no, 0.5, q)
        num += ws[r] * yes * q; den += ws[r] * q
    num += w * N["snrterm"]; den += w * N["ok"]
    dd = den >= delta if delta > 0 else den > 0
    D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
    a = np.full(n, "E", dtype=object)
    if single is not None:
        a[dd & (D >= single)] = "A"; a[dd & (D < single)] = "D"
    else:
        a[dd & (D >= ta)] = "A"; a[dd & (D <= td)] = "D"
    return a


class FastBoot:
    """Vectorised two-stage cluster bootstrap on per-day counts (networks, then days within network)."""

    def __init__(self, nets, reps=500, seed=SEED):
        self.names = sorted(nets); self.reps = reps
        rng = np.random.default_rng(seed)
        self.day_index = {}
        for k in self.names:
            ud, inv = np.unique(nets[k]["days"], return_inverse=True)
            self.day_index[k] = (len(ud), inv)
        K = len(self.names)
        self.draws = []  # per replicate: list of (net index, day multiplicity vector)
        for _ in range(reps):
            ks = rng.choice(K, K); rep = []
            for ki in ks:
                nd = self.day_index[self.names[ki]][0]
                rep.append((ki, np.bincount(rng.choice(nd, nd), minlength=nd)))
            self.draws.append(rep)

    def run(self, nets, A, B):
        """A, B: {net: action array}. Returns pooled diff (obs), CI, ratio (obs), ratio CI."""
        cnt = []
        for k in self.names:
            nd, inv = self.day_index[k]; a = nets[k]["assoc"]
            na = np.bincount(inv[a], minlength=nd); da = np.bincount(inv[a & (A[k] == "D")], minlength=nd)
            db = np.bincount(inv[a & (B[k] == "D")], minlength=nd); cnt.append((na, da, db))
        tot = np.array([[c[0].sum(), c[1].sum(), c[2].sum()] for c in cnt], float)
        obs_d = (tot[:, 1].sum() - tot[:, 2].sum()) / tot[:, 0].sum() * 100
        obs_r = (tot[:, 1].sum() + 0.5) / (tot[:, 2].sum() + 0.5)
        dv = []; rv = []
        for rep in self.draws:
            na = da = db = 0.0
            for ki, m in rep:
                c = cnt[ki]; na += m @ c[0]; da += m @ c[1]; db += m @ c[2]
            if na > 0: dv.append((da - db) / na * 100); rv.append((da + 0.5) / (db + 0.5))
        dv = np.array(dv); rv = np.array(rv)
        return dict(diff_pp=round(float(obs_d), 3), ci95=[round(float(np.percentile(dv, 2.5)), 3), round(float(np.percentile(dv, 97.5)), 3)],
                    ratio=round(float(obs_r), 3), ratio_ci95=[round(float(np.percentile(rv, 2.5)), 3), round(float(np.percentile(rv, 97.5)), 3)])


def counts(nets, A):
    out = dict(assoc_D=0, assoc_A=0, assoc_E=0, all_D=0, all_A=0, all_E=0)
    for k in nets:
        a = A[k]; s = nets[k]["assoc"]
        for x in "DAE":
            out[f"assoc_{x}"] += int((a[s] == x).sum()); out[f"all_{x}"] += int((a == x).sum())
    return out


def main():
    t0 = time.time()
    rows = collect("reviewed"); nets = prep(rows)
    assert len(nets) == 33, len(nets)
    P3 = {k: nets[k]["act"]["P3"] for k in nets}
    # 1) reproduction checks
    repro = {}
    for pol in POLS:
        A = {k: actions(nets[k], pol, **FROZEN) for k in nets}
        mism = int(sum((A[k] != nets[k]["act"][pol]).sum() for k in nets))
        repro[pol] = mism
    print("reproduction mismatches:", repro)
    assert all(v == 0 for v in repro.values()), repro
    frozen2000 = {}
    for pol in POLS:
        d = {k: (nets[k]["days"], nets[k]["assoc"], {"X": nets[k]["act"][pol], "P3": P3[k]}) for k in nets}
        cb = v2.cluster_boot(d, "X", "P3")
        frozen2000[pol] = {x: cb[x] for x in ["pooled_diff_pp", "pooled_ci95_pp", "pooled_noninferior", "ratio", "ratio_ci95", "ratio_criterion_holds"]}
    print("frozen 2000:", json.dumps(frozen2000))
    # 2) grid
    fb = FastBoot(nets, reps=500)
    grid = list(itertools.product([0.30, 0.35, 0.40, 0.45, 0.50], [0, 1, 2], [0.35, 0.40, 0.45, 0.50, 0.55], [0.55, 0.60, 0.65], [0.11, 0.16, 0.21]))
    res = {pol: [] for pol in POLS}
    for i, (w, g, de, ta, td) in enumerate(grid):
        for pol in POLS:
            A = {k: actions(nets[k], pol, w, g, de, ta, td) for k in nets}
            r = fb.run(nets, A, P3); r.update(w=w, g=g, delta=de, theta_A=ta, theta_D=td); r.update(counts(nets, A))
            res[pol].append(r)
        if i % 75 == 0: print(i, round(time.time() - t0), "s", flush=True)
    frozen_verdict = {p: frozen2000[p]["pooled_noninferior"] for p in POLS}
    frozen_ratio = {p: frozen2000[p]["ratio_criterion_holds"] for p in POLS}
    summ = {}
    for pol in POLS:
        R = res[pol]
        met = np.array([r["ci95"][1] <= MARGIN for r in R]); rat = np.array([r["ratio_ci95"][1] <= RATIO_MAX for r in R])
        worst = max(R, key=lambda r: r["ci95"][1]); best = min(R, key=lambda r: r["ci95"][1])
        worst_r = max(R, key=lambda r: r["ratio_ci95"][1])
        fz = [r for r in R if (r["w"], r["g"], r["delta"], r["theta_A"], r["theta_D"]) == (0.40, 1, 0.45, 0.60, 0.16)][0]
        summ[pol] = dict(points=len(R), frozen_difference_verdict_met=frozen_verdict[pol], frozen_ratio_holds=frozen_ratio[pol],
                         share_points_met=round(float(met.mean()), 4), share_same_difference_verdict=round(float((met == frozen_verdict[pol]).mean()), 4),
                         share_ratio_holds=round(float(rat.mean()), 4), share_same_ratio_verdict=round(float((rat == frozen_ratio[pol]).mean()), 4),
                         worst_upper_pp=worst["ci95"][1], worst_at={x: worst[x] for x in ["w", "g", "delta", "theta_A", "theta_D"]},
                         best_upper_pp=best["ci95"][1], best_at={x: best[x] for x in ["w", "g", "delta", "theta_A", "theta_D"]},
                         worst_ratio_upper=worst_r["ratio_ci95"][1], worst_ratio_at={x: worst_r[x] for x in ["w", "g", "delta", "theta_A", "theta_D"]},
                         frozen_point_500rep=dict(diff_pp=fz["diff_pp"], ci95=fz["ci95"], ratio=fz["ratio"], ratio_ci95=fz["ratio_ci95"]),
                         range_assoc_dismissed=[min(r["assoc_D"] for r in R), max(r["assoc_D"] for r in R)],
                         range_all_escalated=[min(r["all_E"] for r in R), max(r["all_E"] for r in R)],
                         range_all_alerted=[min(r["all_A"] for r in R), max(r["all_A"] for r in R)])
    # one-at-a-time
    oat = {}
    for pol in POLS:
        oat[pol] = {}
        for par, vals in [("w", [0.30, 0.35, 0.40, 0.45, 0.50]), ("g", [0, 1, 2]), ("delta", [0.35, 0.40, 0.45, 0.50, 0.55]),
                          ("theta_A", [0.55, 0.60, 0.65]), ("theta_D", [0.11, 0.16, 0.21])]:
            fz = {"w": 0.40, "g": 1, "delta": 0.45, "theta_A": 0.60, "theta_D": 0.16}
            pts = []
            for val in vals:
                want = dict(fz); want[par] = val
                r = [x for x in res[pol] if all(x[q] == want[q] for q in want)][0]
                pts.append({"value": val, "diff_pp": r["diff_pp"], "upper": r["ci95"][1], "ratio_upper": r["ratio_ci95"][1],
                            "assoc_D": r["assoc_D"], "all_E": r["all_E"], "all_A": r["all_A"]})
            oat[pol][par] = pts
    P3c = counts(nets, P3)
    json.dump(dict(plan="PLAN_SENSITIVITY_WEIGHTS_2026-11-08.md", networks=len(nets), reps_grid=500, seed=SEED,
                   reproduction_mismatches=repro, frozen_2000=frozen2000, P3_counts=P3c, summary=summ, one_at_a_time=oat,
                   grid=res), open(os.path.join(OUT, "sens_weights.json"), "w"), indent=1)
    # 3) ablations
    abl = {}
    variants = {"frozen": dict(FROZEN), "A1_no_delta": dict(FROZEN, delta=0.0),
                "A2_single_0.38": dict(FROZEN, single=0.38), "A2_single_thetaD_0.16": dict(FROZEN, single=0.16),
                "A2_single_thetaA_0.60": dict(FROZEN, single=0.60), "A3_no_delta_single_0.38": dict(FROZEN, delta=0.0, single=0.38)}
    for pol in POLS:
        abl[pol] = {}
        for name, prm in variants.items():
            A = {k: actions(nets[k], pol, **prm) for k in nets}
            d = {k: (nets[k]["days"], nets[k]["assoc"], {"X": A[k], "P3": P3[k]}) for k in nets}
            cb = v2.cluster_boot(d, "X", "P3")
            abl[pol][name] = dict(counts(nets, A), pooled_diff_pp=cb["pooled_diff_pp"], pooled_ci95_pp=cb["pooled_ci95_pp"],
                                  noninferior=cb["pooled_noninferior"], ratio=cb["ratio"], ratio_ci95=cb["ratio_ci95"],
                                  ratio_criterion_holds=cb["ratio_criterion_holds"])
            print(pol, name, abl[pol][name]["pooled_diff_pp"], abl[pol][name]["pooled_ci95_pp"], flush=True)
    json.dump(dict(plan="PLAN_SENSITIVITY_WEIGHTS_2026-11-08.md", reps=2000, seed=SEED, P3_counts=P3c, ablations=abl),
              open(os.path.join(OUT, "ablations.json"), "w"), indent=1)
    plot(res, summ)
    print("done", round(time.time() - t0), "s")


def plot(res, summ):
    """Figure from the grid (also: python analysis/sens_weights.py --plot, from the saved JSON)."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    ws = [0.30, 0.35, 0.40, 0.45, 0.50]; ds = [0.35, 0.40, 0.45, 0.50, 0.55]
    for ax, pol, title in zip(axs, POLS, ["CG (c = 1)", "CG, c = 0.5", "CG-D"]):
        M = np.zeros((len(ds), len(ws)))
        for i, de in enumerate(ds):
            for j, w in enumerate(ws):
                r = [x for x in res[pol] if x["w"] == w and x["delta"] == de and x["g"] == 1 and x["theta_A"] == 0.60 and x["theta_D"] == 0.16][0]
                M[i, j] = r["ci95"][1]
        im = ax.imshow(M, origin="lower", cmap="RdYlGn_r", vmin=0, vmax=8, aspect="auto")
        for i in range(len(ds)):
            for j in range(len(ws)):
                ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8)
        ax.set_xticks(range(len(ws))); ax.set_xticklabels(ws); ax.set_yticks(range(len(ds))); ax.set_yticklabels(ds)
        ax.set_xlabel("SNR weight"); ax.set_ylabel("delta" if pol == POLS[0] else ""); ax.set_title(title + f"  (met: {summ[pol]['share_points_met']*100:.0f}% of grid)", fontsize=9)
    fig.colorbar(im, ax=axs, shrink=0.8, label="upper 95% bound vs P3 (pp); margin 3")
    fig.suptitle("Upper bound of the dismissed-share difference to P3, reviewed labels, 33 networks (other parameters frozen)", fontsize=10)
    fig.savefig(os.path.join(root, "figures", "fig_sens_weights.png"), dpi=600, bbox_inches="tight")


if __name__ == "__main__":
    if "--plot" in sys.argv:
        J = json.load(open(os.path.join(OUT, "sens_weights.json")))
        plot(J["grid"], J["summary"])
    else:
        main()
