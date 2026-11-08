"""Scoring of PREREGISTRATION_KZ_ANALYST_LABELS_2026-11-08.md (pushed 7ee7f5c, 2026-11-08T06:58Z, before any label).

download: ISC FDSN events (QuakeML) per month 2023-12-31..2024-11-01, centre (48.8, 80.3), maxradius 20, M >= 2, plus USGS ComCat
global M >= 5.5 (GeoJSON) -> results/kz_analyst/labels/, sha256 in labels/SHA256.txt.
score: for K-MAKZ, K-KURK (results/y2024) and K-KZ (results/kz), episodes with t_on < 2024-11-01; catalogue rows labelled by the
matching function of analysis/v2_reviewed_bulletin.py; L1 = ISC evaluationStatus reviewed (+ ComCat reviewed tele rows);
L2 = ISC event with an NNC origin. Relabelled copies of the chunk folders are scored by the frozen evaluate() of
analysis/cgd_2024.py; CG with c = 0.5 uses the CG code path with the factor of a recorded non-confirmation set to 0.5.
Outputs: results/kz_analyst/kz_reviewed_eval.json, kz_reviewed_table.md.
"""
import os, sys, re, glob, json, math, time, hashlib, shutil, importlib.util, urllib.request, urllib.error
import numpy as np, pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "results", "kz_analyst"); LAB = os.path.join(OUT, "labels"); REL = os.path.join(OUT, "relabelled")
spec = importlib.util.spec_from_file_location("m20", os.path.join(here, "cgd_2024.py")); m20 = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m20)
except SystemExit: pass
CUT = pd.Timestamp("2024-11-01", tz="UTC").timestamp()
MONTHS = [("2023-12-31", "2024-02-01")] + [(f"2024-{i:02d}-01", f"2024-{i + 1:02d}-01") for i in range(2, 11)]
MONTHS[-1] = ("2024-10-01", "2024-11-01")
ISC = "http://www.isc.ac.uk/fdsnws/event/1/query"; USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
RUNS = {"K-MAKZ": (os.path.join(root, "results", "y2024"), "out24_MAKZ_", "MAKZ", "MAKZ"),
        "K-KURK": (os.path.join(root, "results", "y2024"), "out24_KURK_", "KURK", "KURK"),
        "K-KZ": (os.path.join(root, "results", "kz"), "outKZ_2024", "MAKZ", "MAKZ")}


def get(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "p10-research"}), timeout=600) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 204: return b""
            time.sleep(15 * (k + 1))
        except Exception:
            time.sleep(15 * (k + 1))
    raise RuntimeError("failed: " + url)


def download():
    os.makedirs(LAB, exist_ok=True)
    for t0, t1 in MONTHS:
        for kind, url in (("ISC", f"{ISC}?starttime={t0}T00:00:00&endtime={t1}T00:00:00&latitude=48.8&longitude=80.3&maxradius=20&minmagnitude=2"),
                          ("TELE", f"{USGS}?format=geojson&starttime={t0}&endtime={t1}&minmagnitude=5.5")):
            fn = os.path.join(LAB, f"{kind}_{t0}.{'xml' if kind == 'ISC' else 'json'}")
            if os.path.exists(fn) and os.path.getsize(fn) > 0: continue
            b = get(url); open(fn + ".tmp", "wb").write(b); os.replace(fn + ".tmp", fn); print(kind, t0, len(b), flush=True)
    with open(os.path.join(LAB, "SHA256.txt"), "w") as h:
        for f in sorted(glob.glob(os.path.join(LAB, "*.*"))):
            if not f.endswith("SHA256.txt"): h.write(hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + os.path.basename(f) + "\n")
    print("download done")


def parse_isc(fn):
    s = open(fn, encoding="utf-8", errors="replace").read(); rows = []
    for ev in re.findall(r"<event .*?</event>", s, re.S):
        m = re.search(r"<preferredOriginID>(.*?)</preferredOriginID>", ev)
        if not m: continue
        o = re.search(r'<origin publicID="' + re.escape(m.group(1)) + r'".*?</origin>', ev, re.S)
        if not o: continue
        o = o.group(0)
        t = re.search(r"<time>\s*<value>(.*?)</value>", o); la = re.search(r"<latitude>\s*<value>(.*?)</value>", o); lo = re.search(r"<longitude>\s*<value>(.*?)</value>", o)
        if not (t and la and lo): continue
        stt = re.search(r"<evaluationStatus>(.*?)</evaluationStatus>", o)
        nnc = bool(re.search(r"<agencyID>NNC</agencyID>", ev))
        rows.append((pd.Timestamp(t.group(1).rstrip("Z"), tz="UTC").timestamp(), float(la.group(1)), float(lo.group(1)),
                     (stt.group(1) if stt else "") == "reviewed", nnc))
    return rows


def parse_tele(fn):
    d = json.load(open(fn)); return [(f["properties"]["time"] / 1000.0, f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0],
                                     f["properties"].get("status") == "reviewed", False) for f in d.get("features", [])]


def arr(rows):
    a = np.array(rows, float) if rows else np.zeros((0, 5)); return a[np.argsort(a[:, 0])] if len(a) else a


def label_rows(cat, bull):
    """Same matching as analysis/v2_reviewed_bulletin.label_rows; returns (reviewed, nnc, matched) per row."""
    rev = np.zeros(len(cat), bool); nnc = np.zeros(len(cat), bool); hit = np.zeros(len(cat), bool)
    if not len(bull) or not len(cat): return rev, nnc, hit
    bt = bull[:, 0]
    for i, (t, la, lo) in enumerate(zip(cat.time.to_numpy(float), cat.lat.to_numpy(float), cat.lon.to_numpy(float))):
        a, b = np.searchsorted(bt, t - 2.0), np.searchsorted(bt, t + 2.0, side="right"); best = None
        for j in range(a, b):
            if abs(bull[j, 1] - la) <= 0.5 and abs(((bull[j, 2] - lo + 180) % 360) - 180) <= 0.5 / max(math.cos(math.radians(la)), 0.1) + 1e-9:
                if best is None or abs(bt[j] - t) < abs(bt[best] - t): best = j
        if best is not None: hit[i] = True; rev[i] = bool(bull[best, 3]); nnc[i] = bool(bull[best, 4])
    return rev, nnc, hit


def assoc_vec(P, t_on, t_off):
    P = np.sort(P[np.isfinite(P)])
    if not len(P): return np.zeros(len(t_on), bool)
    i = np.searchsorted(P, t_on - 15.0, side="left"); return (i < len(P)) & (P[np.minimum(i, len(P) - 1)] <= t_off)


def relabel(run, label):
    base, prefix, ref, tref = RUNS[run]; isc = arr([r for f in glob.glob(os.path.join(LAB, "ISC_*.xml")) for r in parse_isc(f)])
    tele = arr([r for f in glob.glob(os.path.join(LAB, "TELE_*.json")) for r in parse_tele(f)])
    dst_base = os.path.join(REL, f"{run}_{label}"); shutil.rmtree(dst_base, ignore_errors=True); os.makedirs(dst_base)
    info = {"chunks": [], "episodes": 0, "assoc_catalogue": 0, "assoc_label": 0, "rows": 0, "rows_labelled": 0, "agreement_min": 1.0}
    for d in sorted(glob.glob(os.path.join(base, prefix + "*"))):
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv")); cat = pd.read_csv(os.path.join(d, "catalog.csv"))
        keep = ep.t_on.to_numpy(float) < CUT
        if not keep.any(): continue
        stored = (ep.assoc_event >= 0).to_numpy(); rec = assoc_vec(cat.p_pred.to_numpy(float), ep.t_on.to_numpy(float), ep.t_off.to_numpy(float))
        agree = float((stored == rec).mean()) if len(ep) else 1.0
        if agree < 0.995: raise SystemExit(f"self-check failed {run} {d}: {agree}")
        lab = np.zeros(len(cat), bool)
        for src in ("ISC", "USGS"):
            msk = (cat.source == src).to_numpy()
            if src == "ISC":
                r, n, h = label_rows(cat[msk], isc); lab[msk] = r if label == "L1" else n
            else:
                mm = msk & (cat.kind == "tele").to_numpy(); r, n, h = label_rows(cat[mm], tele); lab[mm] = r if label == "L1" else False
        la = assoc_vec(cat.p_pred.to_numpy(float)[lab], ep.t_on.to_numpy(float), ep.t_off.to_numpy(float))
        ep2 = ep[keep].copy(); ep2["assoc_event"] = np.where(la[keep], 0, -1)
        av2 = av[pd.to_datetime(av.day).map(lambda x: x.tz_localize("UTC").timestamp() < CUT)]
        dd = os.path.join(dst_base, prefix + os.path.basename(d)[len(prefix):]); os.makedirs(dd)
        ep2.to_csv(os.path.join(dd, "episodes.csv"), index=False); av2.to_csv(os.path.join(dd, "availability.csv"), index=False)
        cat[lab].to_csv(os.path.join(dd, "catalog.csv"), index=False)
        for f in ("summary.json", "run.log"): shutil.copy(os.path.join(d, f), dd)
        info["chunks"].append(os.path.basename(d)); info["episodes"] += int(keep.sum()); info["assoc_catalogue"] += int((stored & keep).sum())
        info["assoc_label"] += int((la & keep).sum()); info["rows"] += int(len(cat)); info["rows_labelled"] += int(lab.sum())
        info["agreement_min"] = min(info["agreement_min"], round(agree, 5))
    return dst_base, prefix, ref, tref, info


def c05_and_chance(base, prefix, ref, tref):
    """CG with c = 0.5 (CG code path of cgd_2024.evaluate, NO factor 0.5), paired day bootstrap vs P3 (2000, seed 7), and the
    chance control on the labelled rows (100 shifts of 1-7 days, seed 7)."""
    frames, cats, cal, dist = [], [], [], {}
    for d in sorted(glob.glob(os.path.join(base, prefix + "*"))):
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv"))
        log = open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read()
        dist.update({m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+) distance_km ([\d.]+)", log, re.M)})
        frames.append(ep); cal += av.day.tolist(); cats.append(pd.read_csv(os.path.join(d, "catalog.csv")))
    ep = pd.concat(frames, ignore_index=True); cat = pd.concat(cats, ignore_index=True); ep["day"] = ep.t_on_utc.str[:10]
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    assoc = (ep.assoc_event >= 0).to_numpy(); snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}; yes = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"
    p3 = np.full(len(ep), "ESCALATE", dtype=object); p3[yes & ok & (snr >= 7.5)] = "ALERT"; p3[(~yes) & ok & (snr < 7.5)] = "DISMISS"

    def cg(c):
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float); q = np.where(S[k] == "NO", c, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"; return a
    cg1, c05 = cg(1.0), cg(0.5)
    days = ep.day.to_numpy(); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero((days == d) & assoc) for d in ud}

    def boot(a):
        obs = ((a[assoc] == "DISMISS").mean() - (p3[assoc] == "DISMISS").mean()) * 100 if assoc.any() else float("nan")
        rng = np.random.default_rng(7); v = []
        for _ in range(2000):
            ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))])
            if len(ids): v.append(((a[ids] == "DISMISS").mean() - (p3[ids] == "DISMISS").mean()) * 100)
        ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)] if v else [None, None]
        return {"diff_pp": round(float(obs), 2), "ci95_pp": ci, "holds": (ci[1] is not None and ci[1] <= 3.0),
                "dismissed": int(((a == "DISMISS") & assoc).sum()), "P3_dismissed": int(((p3 == "DISMISS") & assoc).sum())}
    rng = np.random.default_rng(7); offs = rng.uniform(1, 7, 100) * 86400 * rng.choice([-1, 1], 100)
    t_on, t_off = ep.t_on.to_numpy(float), ep.t_off.to_numpy(float); pp = cat.p_pred.to_numpy(float)
    t0 = pd.Timestamp(min(cal)).timestamp(); span = pd.Timestamp(max(cal)).timestamp() + 86400 - t0; rows = []
    for o in offs:
        s = assoc_vec(t0 + np.mod(pp + o - t0, span), t_on, t_off)
        rows.append((s.sum(), ((cg1 == "DISMISS") & s).sum() - ((p3 == "DISMISS") & s).sum()))
    rows = np.array(rows, float); real = ((cg1 == "DISMISS") & assoc).sum() - ((p3 == "DISMISS") & assoc).sum()
    corr = (real - rows[:, 1].mean()) / max(assoc.sum() - rows[:, 0].mean(), 1) * 100
    selfcheck = boot(cg1)
    return boot(c05), {"chance_associated_mean": round(float(rows[:, 0].mean()), 2), "label_associated": int(assoc.sum()),
                       "chance_CG_minus_P3_excess_mean": round(float(rows[:, 1].mean()), 2), "real_CG_minus_P3_excess": int(real),
                       "chance_corrected_CG_minus_P3_pp": round(float(corr), 2)}, selfcheck


def score():
    out = {"preregistration": "PREREGISTRATION_KZ_ANALYST_LABELS_2026-11-08.md (7ee7f5c)", "cutoff_utc": "2024-11-01", "runs": {}}
    for label in ("L1", "L2"):
        for run in RUNS:
            base, prefix, ref, tref, info = relabel(run, label)
            r = m20.evaluate(ref, base=base, prefix=prefix, table_ref=tref)
            c05, chance, cg_check = c05_and_chance(base, prefix, ref, tref)
            ex = info["assoc_label"] >= 20; o = r["outage"]
            res = {"label": label, **info, "calendar_days": r["calendar_days"], "outage_days": r["outage_days"], "exercised": ex,
                   "KR1_CG": r["NI_CG"], "KR2_CGD": r["D1"], "KR3_CGc05": c05, "CG_selfcheck_reimplemented": cg_check,
                   "KR4_outage": {"CG": o["CG"]["missed"], "P1": o["P1"]["missed"], "assoc": o["CG"]["assoc"],
                                  "exercised": o["CG"]["assoc"] >= 10, "holds": (o["CG"]["missed"] < o["P1"]["missed"]) if o["CG"]["assoc"] >= 10 else None},
                   "unassoc_alerts": {p: r["all"][p]["alert_unassoc"] for p in ("CG", "CG-D", "P3", "P1t")},
                   "esc_per_day": {p: r["all"][p]["esc_per_day"] for p in ("CG", "CG-D", "P3")}, "chance_control": chance}
            if abs(cg_check["diff_pp"] - r["NI_CG"]["diff_pp"]) > 1e-6: raise SystemExit(f"c-path self-check failed {run} {label}")
            out["runs"][f"{run}_{label}"] = res; print(run, label, {k: res[k] for k in ("episodes", "assoc_label", "KR1_CG", "KR2_CGD", "KR3_CGc05", "KR4_outage")}, flush=True)
    json.dump(out, open(os.path.join(OUT, "kz_reviewed_eval.json"), "w"), indent=1, default=str)
    L = ["| run | label | episodes | assoc (catalogue) | assoc (label) | CG − P3 pp [95%] | CG-D − P3 | c = 0.5 − P3 | outage CG vs P1 | chance-corrected CG − P3 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in out["runs"].items():
        L.append(f"| {k.rsplit('_', 1)[0]} | {r['label']} | {r['episodes']} | {r['assoc_catalogue']} | {r['assoc_label']} | {r['KR1_CG']['diff_pp']} {r['KR1_CG']['ci95_pp']} | "
                 f"{r['KR2_CGD']['diff_pp']} {r['KR2_CGD']['ci95_pp']} | {r['KR3_CGc05']['diff_pp']} {r['KR3_CGc05']['ci95_pp']} | "
                 f"{r['KR4_outage']['CG']} vs {r['KR4_outage']['P1']} of {r['KR4_outage']['assoc']} | {r['chance_control']['chance_corrected_CG_minus_P3_pp']} |")
    open(os.path.join(OUT, "kz_reviewed_table.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    {"download": download, "score": score}[sys.argv[1]]()
