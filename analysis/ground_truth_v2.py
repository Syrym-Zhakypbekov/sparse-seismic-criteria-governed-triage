"""Scoring of PREREGISTRATION_GROUND_TRUTH_2026-11-08.md, written and pushed BEFORE any label of this test was downloaded.

Analyst ground truth for the AK replication (AK.CUT reference, results/ak/outAK_20*): USGS ComCat events within 5 degrees
of AK.CUT, 2024-01-07T23:50 .. 2025-07-01T00:00, two classes taken from ComCat's own review state:
  CONFIRMED = current event with status "reviewed" (an analyst kept it; any event type);
  REJECTED  = event returned only with includedeleted=only (an analyst deleted it) and with no current event within
              20 s and 0.5 deg (the pipeline's de-duplication rule); a deleted event with such a twin is a merged
              duplicate, counted as DELETED_DUPLICATE and not used.
Matching = the pipeline's one association function: p_pred = origin + first P (iasp91; p, P, Pn, Pg, Pdiff) at AK.CUT,
residual r = p_pred - t_on in [-15 s, (t_off - t_on) + 0 s]. An episode with any CONFIRMED candidate is CONFIRMED,
otherwise with any REJECTED candidate REJECTED, otherwise UNLABELLED.
Policies: the action code of analysis/cgd_2024.py evaluate() copied verbatim (P1, P1t 8.0, P2 10.5, P3 7.5, CG, CG-D with
the MAKZ development table), plus P3 at 8.0 dB (secondary). Self-check: the copied actions must reproduce the "missed" and
"alert_unassoc" counts of results/ak/ak_eval.json for every frozen policy, otherwise the script stops.
G1 CG vs P3 7.5, dismissed share of CONFIRMED episodes: upper 95 % day-bootstrap bound <= 3 pp.
G2 CG-D vs P3 7.5, same.
G3 ALERT share of REJECTED episodes: CG < P1t and CG < P3 7.5 (upper 95 % bound of each difference < 0).
G4 CG dismisses REJECTED more readily than CONFIRMED: lower 95 % bound of (DISMISS|REJECTED - DISMISS|CONFIRMED) > 0.
G1/G2 not exercised with < 20 CONFIRMED episodes, G3/G4 with < 20 REJECTED episodes.
Control: label times shifted by +-1, +-2, +-3 days (p_pred shifted, same matching) = chance labelling rate.
Day bootstrap over episode dates, 2000 resamples, seed 7 (as every earlier test).
Usage:  python analysis/ground_truth_v2.py download   (labels -> results/ground_truth/labels/, sha256 recorded)
        python analysis/ground_truth_v2.py score      (-> results/ground_truth/ground_truth_eval.json + run.log)
"""
import os, sys, io, json, glob, re, time, hashlib, datetime as dt, urllib.request, urllib.error
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(root, "results", "ak"); G = os.path.join(root, "results", "ground_truth"); L = os.path.join(G, "labels")
REF_LAT, REF_LON = 62.4058, -150.2625            # AK.CUT, as in PREREGISTRATION_AK_NETWORK.md
MAXRADIUS = 5.0
Q0, Q1 = dt.datetime(2024, 1, 7, 23, 50), dt.datetime(2025, 7, 1)
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
ASSOC = (-15.0, 0.0); MIN_N = 20; SHIFTS_D = [-3, -2, -1, 1, 2, 3]
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

# ---------------------------------------------------------------- labels
def fetch(t0, t1, deleted):
    q = (f"{URL}?format=csv&orderby=time-asc&starttime={t0:%Y-%m-%dT%H:%M:%S}&endtime={t1:%Y-%m-%dT%H:%M:%S}"
         f"&latitude={REF_LAT}&longitude={REF_LON}&maxradius={MAXRADIUS}" + ("&includedeleted=only" if deleted else ""))
    for k in range(6):
        try:
            with urllib.request.urlopen(q, timeout=180) as r: txt = r.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(txt)) if txt.strip() else pd.DataFrame()
            if len(df) >= 20000:                       # service limit: split the window
                mid = t0 + (t1 - t0) / 2
                return fetch(t0, mid, deleted) + fetch(mid, t1, deleted)
            return [(q, txt, df)]
        except Exception as ex:
            log("fetch error", k + 1, str(ex)[:150]); time.sleep(20 * (k + 1))
    raise SystemExit("label download failed: " + q)

def download():
    os.makedirs(L, exist_ok=True); rec = []
    for deleted in (False, True):
        frames = []; t = Q0
        while t < Q1:
            t1 = min((t.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0), Q1)
            for q, txt, df in fetch(t, t1, deleted):
                frames.append(df); rec.append({"url": q, "rows": int(len(df)), "sha256": hashlib.sha256(txt.encode()).hexdigest()})
            t = t1
        df = pd.concat([f for f in frames if len(f)], ignore_index=True).drop_duplicates("id")
        name = "comcat_deleted.csv" if deleted else "comcat_current.csv"
        df.to_csv(os.path.join(L, name), index=False)
        log(name, len(df), "rows")
    for n in ("comcat_current.csv", "comcat_deleted.csv"):
        rec.append({"file": n, "sha256": hashlib.sha256(open(os.path.join(L, n), "rb").read()).hexdigest()})
    json.dump({"downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "queries": rec},
              open(os.path.join(L, "download_record.json"), "w"), indent=1)

# ---------------------------------------------------------------- travel times (pipeline rule)
def _ptt_chunk(rows):
    return _p_pred_serial(pd.DataFrame(rows, columns=["latitude", "longitude", "depth", "t"]))

def p_pred_table(df, workers=24):
    """same values as the serial function; split over processes only for speed (about 47 ms per TauP call)."""
    if len(df) < 2000: return _p_pred_serial(df)
    from concurrent.futures import ProcessPoolExecutor
    rows = df[["latitude", "longitude", "depth", "t"]].to_numpy().tolist(); n = -(-len(rows) // workers)
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_ptt_chunk, [rows[i:i + n] for i in range(0, len(rows), n)]))
    return np.concatenate(parts)

def _p_pred_serial(df):
    from obspy.taup import TauPyModel
    from obspy.geodetics import gps2dist_azimuth
    model = TauPyModel("iasp91"); out = []; cache = {}
    for la, lo, de, tt in zip(df.latitude, df.longitude, df.depth, df.t):
        deg = gps2dist_azimuth(REF_LAT, REF_LON, la, lo)[0] / 111195
        dep = max(float(de) if np.isfinite(de) else 0.0, 0.0)
        key = (round(deg, 4), round(dep, 2))
        if key not in cache:
            arr = model.get_travel_times(source_depth_in_km=dep, distance_in_degree=deg, phase_list=["p", "P", "Pn", "Pg", "Pdiff"])
            cache[key] = min(a.time for a in arr) if arr else np.nan
        out.append(tt + cache[key])
    return np.array(out)

def labels():
    cur = pd.read_csv(os.path.join(L, "comcat_current.csv")); de = pd.read_csv(os.path.join(L, "comcat_deleted.csv"))
    # epoch seconds independent of the pandas datetime resolution (pandas 3 parses these strings at microseconds; the first
    # run divided microseconds by 1e9 and matched nothing - protocol deviation 1, EXPERIMENT_LEDGER.md)
    for d in (cur, de): d["t"] = (pd.to_datetime(d["time"], utc=True) - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    for d in (cur, de):
        lo, hi = Q0.replace(tzinfo=dt.timezone.utc).timestamp(), Q1.replace(tzinfo=dt.timezone.utc).timestamp()
        if not ((d.t >= lo - 1) & (d.t <= hi + 1)).all(): raise SystemExit("label times outside the query window: unit error")
    de = de[~de.id.isin(cur.id)].copy()                      # an id returned by both queries is not deleted
    ct, cla, clo = cur.t.to_numpy(), cur.latitude.to_numpy(), cur.longitude.to_numpy()
    twin = np.array([bool(((np.abs(ct - t) < 20) & (np.abs(cla - a) < 0.5) & (np.abs(clo - o) < 0.5)).any())
                     for t, a, o in zip(de.t, de.latitude, de.longitude)])
    de["label"] = np.where(twin, "DELETED_DUPLICATE", "REJECTED")
    cur["label"] = np.where(cur.status.str.lower() == "reviewed", "CONFIRMED", "AUTOMATIC_CURRENT")
    lab = pd.concat([cur, de], ignore_index=True)
    lab["p_pred"] = p_pred_table(lab)
    return lab

def ptt_selfcheck():
    """the travel-time function must reproduce the pipeline's stored p_pred (catalog.csv of the AK run) to 0.01 s."""
    cat = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(A, "outAK_20*", "catalog.csv")))], ignore_index=True)
    cat = cat[cat.kind == "regional"].iloc[::50].head(200).rename(columns={"lat": "latitude", "lon": "longitude", "depth_km": "depth", "time": "t"})
    err = np.nanmax(np.abs(p_pred_table(cat) - cat.p_pred.to_numpy()))
    if not err < 0.01: raise SystemExit(f"p_pred self-check failed: max error {err}")
    log(f"self-check: p_pred reproduces the pipeline on {len(cat)} AK catalogue rows, max error {err:.4f} s")

# ---------------------------------------------------------------- episodes and actions (verbatim from cgd_2024.evaluate)
def episodes_and_actions():
    spec = __import__("importlib.util").util.spec_from_file_location("m20", os.path.join(root, "analysis", "cgd_2024.py"))
    m = __import__("importlib.util").util.module_from_spec(spec)
    try: spec.loader.exec_module(m)
    except SystemExit: pass
    TAB, BINS, LAB = m.TAB, m.BINS, m.LAB
    frames, dist = [], {}
    for d in sorted(glob.glob(os.path.join(A, "outAK_20*"))):
        log_ = open(os.path.join(d, "run.log"), encoding="utf-8", errors="ignore").read()
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); av = pd.read_csv(os.path.join(d, "availability.csv"))
        ep["day"] = ep.t_on_utc.str[:10]; ep["chunk"] = os.path.basename(d); frames.append(ep)
        dist.update({mm.group(1): float(mm.group(2)) for mm in re.finditer(r"^(\w+) distance_km ([\d.]+)", log_, re.M)})
    ep = pd.concat(frames, ignore_index=True)
    NB = sorted([c[2:] for c in ep.columns if c.startswith("n_")], key=lambda k: dist.get(k, 1e9))
    W = dict(zip(NB, [0.25, 0.20, 0.15])); W["SNR"] = 0.40
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    S = {k: ep[f"n_{k}"].astype(str).to_numpy() for k in NB}
    yes = np.zeros(len(ep), bool); no = np.zeros(len(ep), bool)
    for k in NB: yes |= S[k] == "YES"; no |= S[k] == "NO"
    act = {"P1": np.where(yes, "ALERT", "DISMISS").astype(object), "P1t": np.where(yes | (ok & (snr >= 8.0)), "ALERT", "DISMISS").astype(object)}
    for n, t in [("P3", 7.5), ("P2", 10.5), ("P3_8.0", 8.0)]:
        a = np.full(len(ep), "ESCALATE", dtype=object); a[yes & ok & (snr >= t)] = "ALERT"
        d_ = (~yes) & ok & (snr < t); d_ = d_ & no if n == "P2" else d_; a[d_] = "DISMISS"; act[n] = a
    b = pd.cut(pd.Series(np.where(ok, snr, np.nan)), BINS, labels=LAB).astype(str).to_numpy()
    for name, detect in [("CG", False), ("CG-D", True)]:
        num = np.zeros(len(ep)); den = np.zeros(len(ep))
        for k in NB:
            q = np.isin(S[k], ["YES", "NO"]).astype(float)
            if detect:
                p = np.array([TAB["MAKZ"][k].get(bb, {"p": 0.5})["p"] if bb in LAB else 0.5 for bb in b])
                q = np.where(S[k] == "NO", p, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"; act[name] = a
    # self-check against the pre-registered AK scorer output
    ref = json.load(open(os.path.join(A, "ak_eval.json")))["all"]; assoc = (ep.assoc_event >= 0).to_numpy()
    for n in ["P1", "P1t", "P2", "P3", "CG", "CG-D"]:
        mine = {"missed": int(((act[n] == "DISMISS") & assoc).sum()), "alert_unassoc": int(((act[n] == "ALERT") & ~assoc).sum())}
        if mine["missed"] != ref[n]["missed"] or mine["alert_unassoc"] != ref[n]["alert_unassoc"]:
            raise SystemExit(f"self-check failed for {n}: {mine} vs {ref[n]}")
    log("self-check: actions reproduce results/ak/ak_eval.json for P1, P1t, P2, P3, CG, CG-D")
    return ep, act

def match(ep, lab, shift=0.0):
    """class per episode: CONFIRMED > REJECTED > UNLABELLED, pipeline residual window."""
    out = np.full(len(ep), "UNLABELLED", dtype=object); ev = np.full(len(ep), "", dtype=object)
    ton, toff = ep.t_on.to_numpy(), ep.t_off.to_numpy()
    for cls in ["REJECTED", "CONFIRMED"]:                    # CONFIRMED written last = precedence
        sub = lab[lab.label == cls]; P = np.sort(sub.p_pred.to_numpy() + shift); ids = sub.id.to_numpy()[np.argsort(sub.p_pred.to_numpy() + shift)]
        lo = np.searchsorted(P, ton + ASSOC[0], "left"); hi = np.searchsorted(P, toff + ASSOC[1], "right")
        hit = hi > lo; out[hit] = cls
        for i in np.flatnonzero(hit):
            r = P[lo[i]:hi[i]] - ton[i]; ev[i] = ids[lo[i] + int(np.argmin(np.abs(r)))]
    return out, ev

# ---------------------------------------------------------------- scoring
def boot(days, fn, seed=7, n=2000):
    rng = np.random.default_rng(seed); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero(days == d) for d in ud}; v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))]); x = fn(ids)
        if x is not None and np.isfinite(x): v.append(x)
    return [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)] if v else [None, None]

def share(a, m, what):
    return float((a[m] == what).mean() * 100) if m.any() else np.nan

def score():
    ep, act = episodes_and_actions(); ptt_selfcheck()
    lab = labels(); log("labels:", lab.label.value_counts().to_dict())
    cls, evid = match(ep, lab); ep["gt"] = cls; ep["gt_event"] = evid
    typ = lab.set_index("id")["type"].to_dict(); ep["gt_type"] = [typ.get(e, "") if e else "" for e in evid]
    days = ep.day.to_numpy(); C = cls == "CONFIRMED"; R = cls == "REJECTED"; assoc = (ep.assoc_event >= 0).to_numpy()
    POL = ["P1", "P1t", "P2", "P3", "P3_8.0", "CG", "CG-D"]
    res = {"preregistration": "PREREGISTRATION_GROUND_TRUTH_2026-11-08.md", "scorer": "analysis/ground_truth_v2.py",
           "episodes": int(len(ep)), "calendar_days_with_episodes": int(len(set(days))),
           "label_counts": {k: int(v) for k, v in lab.label.value_counts().items()},
           "episode_classes": {k: int((cls == k).sum()) for k in ["CONFIRMED", "REJECTED", "UNLABELLED"]},
           "confirmed_by_event_type": {k: int(v) for k, v in pd.Series(ep.gt_type[C]).value_counts().items()},
           "cross_with_original_association": {k: {"associated": int(((cls == k) & assoc).sum()), "unassociated": int(((cls == k) & ~assoc).sum())}
                                               for k in ["CONFIRMED", "REJECTED", "UNLABELLED"]}}
    res["action_share_within_class_pct"] = {n: {k: {w: round(share(act[n], cls == k, w), 2) for w in ["DISMISS", "ESCALATE", "ALERT"]}
                                                for k in ["CONFIRMED", "REJECTED", "UNLABELLED"]} for n in POL}
    res["class_counts_within_action"] = {n: {w: {k: int(((act[n] == w) & (cls == k)).sum()) for k in ["CONFIRMED", "REJECTED", "UNLABELLED"]}
                                             for w in ["DISMISS", "ESCALATE", "ALERT"]} for n in POL}
    for n in POL:
        for w in ["DISMISS", "ESCALATE", "ALERT"]:
            c = res["class_counts_within_action"][n][w]; t = c["CONFIRMED"] + c["REJECTED"]
            c["confirmed_share_of_labelled_pct"] = round(100 * c["CONFIRMED"] / t, 2) if t else None
    def pdiff(a, b, m, w):                               # paired difference of shares within class m, resampled ids (with repeats)
        def f(ids):
            ids = ids[m[ids]]
            return ((act[a][ids] == w).mean() - (act[b][ids] == w).mean()) * 100 if len(ids) else None
        return f
    nC, nR = int(C.sum()), int(R.sum())
    def ni(a):
        if nC < MIN_N: return {"exercised": False, "confirmed": nC}
        obs = (share(act[a], C, "DISMISS") - share(act["P3"], C, "DISMISS")); ci = boot(days, pdiff(a, "P3", C, "DISMISS"))
        return {"diff_pp": round(obs, 2), "ci95_pp": ci, "holds": ci[1] is not None and ci[1] <= 3.0, "confirmed": nC}
    res["G1_CG_vs_P3_confirmed_dismissed"] = ni("CG"); res["G2_CGD_vs_P3_confirmed_dismissed"] = ni("CG-D")
    if nR < MIN_N:
        res["G3_rejected_alert_share"] = {"exercised": False, "rejected": nR}; res["G4_CG_separation"] = {"exercised": False, "rejected": nR}
    else:
        g3 = {}
        for comp in ["P1t", "P3"]:
            obs = share(act["CG"], R, "ALERT") - share(act[comp], R, "ALERT"); ci = boot(days, pdiff("CG", comp, R, "ALERT"))
            g3[comp] = {"CG_pct": round(share(act["CG"], R, "ALERT"), 2), f"{comp}_pct": round(share(act[comp], R, "ALERT"), 2),
                        "diff_pp": round(obs, 2), "ci95_pp": ci, "holds": ci[1] is not None and ci[1] < 0}
        g3["holds"] = all(g3[c]["holds"] for c in ["P1t", "P3"]); g3["rejected"] = nR; res["G3_rejected_alert_share"] = g3
        def sep(n):
            def f(ids):
                c, r = ids[C[ids]], ids[R[ids]]
                return ((act[n][r] == "DISMISS").mean() - (act[n][c] == "DISMISS").mean()) * 100 if len(c) and len(r) else None
            return f
        g4 = {}
        for n in POL:
            obs = share(act[n], R, "DISMISS") - share(act[n], C, "DISMISS"); g4[n] = {"diff_pp": round(obs, 2), "ci95_pp": boot(days, sep(n))}
        g4["holds"] = g4["CG"]["ci95_pp"][0] is not None and g4["CG"]["ci95_pp"][0] > 0; g4["rejected"] = nR; g4["confirmed"] = nC
        res["G4_CG_separation"] = g4
    # control: chance labelling with shifted label times
    ctrl = {}
    for s in SHIFTS_D:
        c2, _ = match(ep, lab, shift=s * 86400.0); ctrl[str(s)] = {k: int((c2 == k).sum()) for k in ["CONFIRMED", "REJECTED"]}
    mc = {k: float(np.mean([ctrl[s][k] for s in ctrl])) for k in ["CONFIRMED", "REJECTED"]}
    res["control_shifted_labels"] = {"per_shift_days": ctrl, "mean": mc,
        "chance_fraction": {k: (round(mc[k] / res["episode_classes"][k], 3) if res["episode_classes"][k] else None) for k in mc},
        "rejected_dominated_by_chance": (mc["REJECTED"] >= 0.5 * nR) if nR else None,
        "confirmed_dominated_by_chance": (mc["CONFIRMED"] >= 0.5 * nC) if nC else None}
    os.makedirs(G, exist_ok=True)
    ep[["chunk", "t_on_utc", "t_off_utc", "snr_db", "assoc_event", "gt", "gt_event", "gt_type"] + [f"n_{k}" for k in ["MK31", "KURK", "WUS"]]] \
        .assign(**{f"act_{n}": act[n] for n in POL}).to_csv(os.path.join(G, "episodes_labelled.csv.gz"), index=False, compression="gzip")
    json.dump(res, open(os.path.join(G, "ground_truth_eval.json"), "w"), indent=1, default=str)
    log(json.dumps({k: res[k] for k in ["episode_classes", "G1_CG_vs_P3_confirmed_dismissed", "G2_CGD_vs_P3_confirmed_dismissed",
                                        "G3_rejected_alert_share", "control_shifted_labels"]}, indent=1, default=str))

if __name__ == "__main__":
    os.makedirs(G, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "score"
    log(f"ground_truth_v2.py {mode} start {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    download() if mode == "download" else score()
    open(os.path.join(G, f"run_{mode}.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
