"""POST HOC (specified 07.11.2026 after review R12-M02): out-of-sample comparison of policies at common constraints and
under a range of relative costs. Operating points are chosen ONLY on the development episodes (IU.MAKZ, 85 days) and
then applied unchanged to every test set: extended IU.MAKZ and II.KURK (2025-01..2026-06), 2024 IU.MAKZ and II.KURK,
and the KZ network (2024-01-08..2025-09-30).

Families and their free thresholds (grids):
  P1   classic coincidence (none)            P1t  tau in 0..30 dB step 0.5
  P3   tau_D <= tau_A in 0..30 dB step 0.5   P2   as P3, DISMISS also needs a NO
  CG(c=1), CG(c=0.5), CG-D (development tables; KZ uses the IU.MAKZ table): theta_D < theta_A in 0..1 step 0.01,
  weights by distance rank 0.25/0.20/0.15 + SNR 0.40, SNR full score 30 dB, delta 0.45 (frozen)
A. Constraint selection: minimise unassociated alerts per episode subject to dismissed-associated share <= m and
   escalated share of episodes <= e (m in 3%, 5%; e in 30%, 40%, 50%); ties -> fewer escalations.
B. Cost selection: minimise cost per episode = r_m * dismissed associated + 1 * unassociated alert + r_e * escalation,
   r_m in 20, 50, 100, r_e in 0.1, 0.25, 0.5 (relative to one unassociated alert).
Unassociated alerts are not verified false alarms; costs are illustrative, not measured.
Output: results/posthoc/oos_operating_points.json and .md
"""
import os, json, glob, re, itertools
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(root, "results")
_t = [os.path.join(R, "prereg", "detectability_tables_dev.json"), os.path.join(R, "detectability_tables_dev.json")]
TAB = json.load(open(next(f for f in _t if os.path.exists(f))))
BINS = [-1e9, 5, 10, 15, 20, 1e9]; LAB = ["<5", "5-10", "10-15", "15-20", ">=20"]
WRANK = [0.25, 0.20, 0.15]; WSNR = 0.40; DELTA = 0.45


def load_dirs(dirs):
    fr, dist = [], {}
    for d in dirs:
        e = pd.read_csv(os.path.join(d, "episodes.csv")); e["day"] = e.t_on_utc.str[:10]; fr.append(e)
        log = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
    return pd.concat(fr, ignore_index=True), dist


def test_sets():
    E = os.path.join(R, "extended")
    rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
    mak = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")]
    kur = sorted(glob.glob(os.path.join(E, "kurk_ext", "outK_*")) or glob.glob(os.path.join(R, "kurk_ext", "outK_*")))
    return {"extended IU.MAKZ": (mak, "MAKZ"), "extended II.KURK": (kur, "KURK"),
            "2024 IU.MAKZ": (sorted(glob.glob(os.path.join(R, "y2024", "out24_MAKZ_*"))), "MAKZ"),
            "2024 II.KURK": (sorted(glob.glob(os.path.join(R, "y2024", "out24_KURK_*"))), "KURK"),
            "KZ network": (sorted(glob.glob(os.path.join(R, "kz", "outKZ_20*"))), "MAKZ")}


def features(ep, dist, table_ref):
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, WRANK))
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    D = {}
    for name in ["CG(c=1)", "CG(c=0.5)", "CG-D"]:
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float)
            if name == "CG(c=0.5)": q = np.where(S[k] == "NO", 0.5, q)
            if name == "CG-D":
                p = np.array([TAB[table_ref][k].get(x, {"p": 0.5})["p"] if x in LAB else 0.5 for x in b])
                q = np.where(S[k] == "NO", p, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += WSNR * np.clip(snr / 30, 0, 1) * ok; den += WSNR * ok
        D[name] = np.where(den >= DELTA, num / np.where(den > 0, den, 1), np.nan)
    return {"yes": yes, "no": no, "snr": snr, "ok": ok, "D": D, "assoc": (ep.assoc_event >= 0).to_numpy(), "n": len(ep)}


def act(F, fam, p):
    n = F["n"]; yes, no, snr, ok = F["yes"], F["no"], F["snr"], F["ok"]
    if fam == "P1": return np.where(yes, 1, -1)                       # 1 ALERT, -1 DISMISS, 0 ESCALATE
    if fam == "P1t": return np.where(yes | (ok & (snr >= p[0])), 1, -1)
    if fam in ("P3", "P2"):
        tD, tA = p; a = np.zeros(n, int); a[yes & ok & (snr >= tA)] = 1
        d = (~yes) & ok & (snr < tD)
        if fam == "P2": d &= no
        a[d] = -1; return a
    D = F["D"][fam]; tD, tA = p; a = np.zeros(n, int)
    a[~np.isnan(D) & (D >= tA)] = 1; a[~np.isnan(D) & (D <= tD)] = -1; return a


def metrics(F, a):
    s = F["assoc"]; n = F["n"]
    return {"dismissed_assoc_share": float(((a == -1) & s).sum() / max(s.sum(), 1)),
            "unassoc_alert_per_ep": float(((a == 1) & ~s).sum() / n),
            "escalated_share": float((a == 0).sum() / n),
            "dismissed_assoc": int(((a == -1) & s).sum()), "unassoc_alerts": int(((a == 1) & ~s).sum()),
            "escalations": int((a == 0).sum()), "episodes": int(n), "assoc": int(s.sum())}


def grid(fam):
    g = np.round(np.arange(0, 30.01, 0.5), 2)
    if fam == "P1": return [()]
    if fam == "P1t": return [(t,) for t in g]
    if fam in ("P3", "P2"): return [(d, a) for d in g for a in g if d <= a]
    th = np.round(np.arange(0, 1.0001, 0.01), 2)
    return [(d, a) for d in th for a in th if d < a]


FAMS = ["P1", "P1t", "P3", "P2", "CG(c=1)", "CG(c=0.5)", "CG-D"]
dev = pd.read_csv(os.path.join(R, "stage1_v3", "episodes.csv")); dev["day"] = dev.t_on_utc.str[:10]
Fdev = features(dev, {"MK31": 24.0, "KURK": 499.6, "WUS": 661.1}, "MAKZ")
devtab = {f: [(p, metrics(Fdev, act(Fdev, f, p))) for p in grid(f)] for f in FAMS}

CONS = [(m, e) for m in (0.03, 0.05) for e in (0.30, 0.40, 0.50)]
COSTS = [(rm, re_) for rm in (20, 50, 100) for re_ in (0.1, 0.25, 0.5)]
sel = {"constraint": {}, "cost": {}}
for m, e in CONS:
    for f in FAMS:
        ok_ = [(p, x) for p, x in devtab[f] if x["dismissed_assoc_share"] <= m and x["escalated_share"] <= e]
        if ok_:
            p, x = min(ok_, key=lambda t: (t[1]["unassoc_alert_per_ep"], t[1]["escalated_share"]))
            sel["constraint"][f"m{m}_e{e}|{f}"] = {"params": list(p), "dev": x}
for rm, re_ in COSTS:
    for f in FAMS:
        cost = lambda x: rm * x["dismissed_assoc"] + x["unassoc_alerts"] + re_ * x["escalations"]
        p, x = min(devtab[f], key=lambda t: cost(t[1]))
        sel["cost"][f"rm{rm}_re{re_}|{f}"] = {"params": list(p), "dev": x, "dev_cost_per_ep": cost(x) / x["episodes"]}

out = {"status": "post hoc after review R12-M02; operating points chosen on IU.MAKZ development only, frozen on tests",
       "constraints": [{"max_dismissed_assoc_share": m, "max_escalated_share": e} for m, e in CONS],
       "costs": [{"r_missed": rm, "r_escalation": re_} for rm, re_ in COSTS], "selected": sel, "tests": {}}
for tname, (dirs, ref) in test_sets().items():
    ep, dist = load_dirs(dirs); F = features(ep, dist, ref)
    res = {"constraint": {}, "cost": {}}
    for kind in ("constraint", "cost"):
        for key, v in sel[kind].items():
            x = metrics(F, act(F, key.split("|")[1], tuple(v["params"])))
            if kind == "cost":
                rm, re_ = [float(t[2:]) for t in key.split("|")[0].split("_")]
                x["cost_per_ep"] = (rm * x["dismissed_assoc"] + x["unassoc_alerts"] + re_ * x["escalations"]) / x["episodes"]
            else:
                m, e = [float(t[1:]) for t in key.split("|")[0].split("_")]
                x["constraints_held"] = bool(x["dismissed_assoc_share"] <= m and x["escalated_share"] <= e)
            res[kind][key] = x
    out["tests"][tname] = res

os.makedirs(os.path.join(R, "posthoc"), exist_ok=True)
json.dump(out, open(os.path.join(R, "posthoc", "oos_operating_points.json"), "w"), indent=1)

# compact summary: per constraint and test, the family with fewest unassociated alerts among those whose
# constraints held out of sample; per cost and test, the family with the lowest out-of-sample cost
L = ["# Out-of-sample operating points (post hoc)\n", "## A. Common constraints (chosen on development)\n",
     "| constraint | test | families meeting both constraints out of sample (fewest unassociated alerts first) |", "|---|---|---|"]
for m, e in CONS:
    for t, res in out["tests"].items():
        held = [(k.split("|")[1], v) for k, v in res["constraint"].items() if k.startswith(f"m{m}_e{e}|") and v["constraints_held"]]
        held.sort(key=lambda kv: kv[1]["unassoc_alert_per_ep"])
        txt = "; ".join(f"{f} {v['unassoc_alert_per_ep']*1000:.0f}/1000 alerts, dism {v['dismissed_assoc_share']*100:.1f}%, esc {v['escalated_share']*100:.0f}%" for f, v in held) or "none"
        L.append(f"| dism<={m*100:.0f}%, esc<={e*100:.0f}% | {t} | {txt} |")
L += ["\n## B. Relative costs (chosen on development)\n", "| r_missed, r_escalation | test | lowest out-of-sample cost per episode (top 3) |", "|---|---|---|"]
for rm, re_ in COSTS:
    for t, res in out["tests"].items():
        c = sorted([(k.split("|")[1], v["cost_per_ep"]) for k, v in res["cost"].items() if k.startswith(f"rm{rm}_re{re_}|")], key=lambda kv: kv[1])
        L.append(f"| {rm}, {re_} | {t} | " + "; ".join(f"{f} {v:.3f}" for f, v in c[:3]) + " |")
open(os.path.join(R, "posthoc", "oos_operating_points.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
