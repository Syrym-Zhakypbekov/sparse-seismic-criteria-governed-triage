"""P10X-03 (registry v4-P10, 9063f88): one threshold procedure (rule (4) on the WHOLE development set) for every policy.
03a: E3 (CG - P3, extended IU.MAKZ 2025-26) re-computed; 03b: reviewed 33-network CG - P3 (and c=0.5, CG-D) with P3 at
the one-procedure threshold. Output: results/p10x/onethreshold.json, results/registry/P10X-03.json."""
import os, sys, glob, re, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = os.path.join(P10, "results")
spec = importlib.util.spec_from_file_location("v2", os.path.join(P10, "analysis", "v2_networks.py"))
v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
DIST_DEV = {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}


def load_dirs(dirs):
    fr, dist = [], {}
    for d in dirs:
        e = pd.read_csv(os.path.join(d, "episodes.csv")); e["day"] = e.t_on_utc.str[:10]; fr.append(e)
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    return pd.concat(fr, ignore_index=True), dist


def feats(ep, dist):
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    S = [ep[f"n_{k}"].astype(str).to_numpy().astype(object) for k in NB]
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for s in S: yes |= s == "YES"; no |= s == "NO"
    return {"S": S, "snr": snr, "ok": ok, "yes": yes, "no": no, "assoc": (ep.assoc_event >= 0).to_numpy(),
            "D1": cg_score(S, snr, ok, 1.0), "days": ep.day.to_numpy()}


def snr_act(name, tau, f):
    yes, no, snr, ok = f["yes"], f["no"], f["snr"], f["ok"]
    a = np.full(len(yes), "E", dtype=object)
    if name == "P1t":
        a[:] = "D"; a[yes | (ok & (snr >= tau))] = "A"; return a
    a[yes & ok & (snr >= tau)] = "A"; d = (~yes) & ok & (snr < tau)
    if name == "P2": d &= no
    a[d] = "D"; return a


def cg_act(f, td, ta=THETA_A):
    a = act_from_D(f["D1"], td, ta); return np.where(a == 1, "A", np.where(a == -1, "D", "E")).astype(object)


def rule4(acts_of, grid, assoc):
    best = None
    for t in grid:
        a = acts_of(t)
        if ((a != "D") & assoc).sum() / max(assoc.sum(), 1) >= 0.95: best = float(t)
    return best


dev = pd.read_csv(os.path.join(R, "stage1_v3", "episodes.csv")); dev["day"] = dev.t_on_utc.str[:10]
fd = feats(dev, DIST_DEV)
GRID = np.round(np.arange(0, 30.01, 0.5), 2); THETA = np.round(np.arange(0, 0.5901, 0.01), 2)
thr = {n: rule4(lambda t, n=n: snr_act(n, t, fd), GRID, fd["assoc"]) for n in ("P1t", "P2", "P3")}
thr["CG_theta_D"] = rule4(lambda t: cg_act(fd, t), THETA, fd["assoc"])
print("one-procedure (whole development) thresholds:", thr)

E = os.path.join(R, "extended")
rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
mak = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")]
ep, dist = load_dirs(mak); fe = feats(ep, dist)
res = {"thresholds_one_procedure": thr, "frozen": {"P3": 7.5, "CG_theta_D": THETA_D}}


def e3(p3_tau, cg_td):
    a = cg_act(fe, cg_td); b = snr_act("P3", p3_tau, fe)
    r = v2.day_boot(fe["days"], fe["assoc"], a, b)
    r["counts"] = {"CG_dismissed_assoc": int(((a == "D") & fe["assoc"]).sum()), "P3_dismissed_assoc": int(((b == "D") & fe["assoc"]).sum())}
    return r


res["E3_frozen_selfcheck"] = e3(7.5, THETA_D)
res["E3_one_procedure"] = e3(thr["P3"], thr["CG_theta_D"])
print("E3 frozen", res["E3_frozen_selfcheck"]); print("E3 one-procedure", res["E3_one_procedure"])

# 03b reviewed 33 networks
rows, nets, pkl_sha = load_reviewed()
res["pickle_sha256"] = pkl_sha
b_nets_fr = {}; b_nets_sp = {}
for k in nets:
    r = rows[k]; S = r["S"]; snr = np.asarray(r["snr"], float); ok = np.asarray(r["ok"], bool); y = anyyes(S)
    p3 = lambda t: np.where(p3_2t(y, snr, ok, t, t) == 1, "A", np.where(p3_2t(y, snr, ok, t, t) == -1, "D", "E")).astype(object)
    assert (p3(7.5) == r["act"]["P3"]).all()
    D1 = cg_score(S, snr, ok, 1.0); D5 = cg_score(S, snr, ok, 0.5)
    lab = lambda a: np.where(a == 1, "A", np.where(a == -1, "D", "E")).astype(object)
    act_sp = {"P3": p3(thr["P3"]), "CG": lab(act_from_D(D1, thr["CG_theta_D"], THETA_A)),
              "CG_c05": lab(act_from_D(D5, thr["CG_theta_D"], THETA_A)), "CG-D": r["act"]["CG-D"]}
    b_nets_fr[k] = (np.asarray(r["days"]), np.asarray(r["assoc"], bool), r["act"])
    b_nets_sp[k] = (np.asarray(r["days"]), np.asarray(r["assoc"], bool), act_sp)
res["reviewed_frozen_selfcheck"] = v2.cluster_boot(b_nets_fr, "CG", "P3")
res["reviewed_one_procedure"] = {pol: v2.cluster_boot(b_nets_sp, pol, "P3") for pol in ("CG", "CG_c05", "CG-D")}
res["reviewed_one_procedure_counts"] = {pol: int(sum(((v[2][pol] == "D") & v[1]).sum() for v in b_nets_sp.values())) for pol in ("P3", "CG", "CG_c05", "CG-D")}
res["note_CG-D"] = "CG-D keeps its frozen actions: its theta_D is that of CG; if the one-procedure CG theta_D differs, CG-D is re-scored is NOT done (see JSON thresholds)."
print("reviewed frozen", res["reviewed_frozen_selfcheck"]); print("reviewed sp", res["reviewed_one_procedure"])


# one-sided p for 03b from the same bootstrap draws (v2.cluster_boot does not return them): recompute with identical RNG use
def cboot_draws(nets_, pa, pb, n=NB, seed=SEED):
    names = sorted(nets_); rng = np.random.default_rng(seed); per = {}
    for k in names:
        days, assoc, act = nets_[k]; ud = np.array(sorted(set(days)))
        idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}; per[k] = (ud, idx, act[pa] == "D", act[pb] == "D")
    v = []
    for _ in range(n):
        ks = rng.choice(names, len(names)); na = da = db = 0.0
        for k in ks:
            ud, idx, A, B = per[k]; sel = rng.choice(ud, len(ud))
            ids = np.concatenate([idx[d] for d in sel]) if len(sel) else np.array([], int)
            na += len(ids); da += A[ids].sum(); db += B[ids].sum()
        if na: v.append(((da - db) / na * 100, (da + 0.5) / (db + 0.5)))
    return np.array(v)


V = cboot_draws(b_nets_sp, "CG", "P3")
cb = res["reviewed_one_procedure"]["CG"]
assert abs(np.percentile(V[:, 0], 97.5) - cb["pooled_ci95_pp"][1]) < 1e-3, (np.percentile(V[:, 0], 97.5), cb)
p03b = max(float(((V[:, 0] >= 3.0).sum() + 1) / (len(V) + 1)), float(((V[:, 1] >= 1.5).sum() + 1) / (len(V) + 1)))
fe3 = res["E3_one_procedure"]
dump(os.path.join(OUT, "onethreshold.json"), res)
dump(os.path.join(REG, "P10X-03.json"), {
    "family": "F-P10X", "id": "P10X-03", "chain": "C",
    "data": "rule (4) on whole IU.MAKZ development (stage1_v3); 03a extended IU.MAKZ 2025-26; 03b 33 reviewed networks (P10 a97d376)",
    "metric": "03a: E3 CG - P3 dismissed share of associated (pp), day bootstrap, margin 3; 03b: pooled CG - P3 reviewed (pp), cluster bootstrap, margin 3 and ratio <= 1.5",
    "est": fe3["diff_pp"], "ci": fe3["ci95_pp"], "p": fe3["p_one_sided_H0_ge_margin"],
    "verdict_unadjusted": verdict([(fe3["diff_pp"], fe3["ci95_pp"][1], 3.0)]), "verdict": None,
    "sub": {"03a": {"est": fe3["diff_pp"], "ci": fe3["ci95_pp"], "p": fe3["p_one_sided_H0_ge_margin"],
                    "verdict_unadjusted": verdict([(fe3["diff_pp"], fe3["ci95_pp"][1], 3.0)]),
                    "frozen_selfcheck": res["E3_frozen_selfcheck"], "frozen_verdict": "not established (published)", "counts": fe3["counts"]},
            "03b": {"est": cb["pooled_diff_pp"], "ci": cb["pooled_ci95_pp"], "ratio": cb["ratio"], "ratio_ci": cb["ratio_ci95"], "p": p03b,
                    "verdict_unadjusted": verdict([(cb["pooled_diff_pp"], cb["pooled_ci95_pp"][1], 3.0), (cb["ratio"], cb["ratio_ci95"][1], 1.5)]),
                    "c05_and_CGD": {k: res["reviewed_one_procedure"][k] for k in ("CG_c05", "CG-D")}}},
    "thresholds_one_procedure": thr,
    "note": "03a re-computes a known result (Table B2); it is not independent confirmation. Final verdicts after Holm (holm.py)."})
