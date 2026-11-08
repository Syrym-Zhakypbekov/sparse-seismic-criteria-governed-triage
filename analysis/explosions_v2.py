"""Scoring of PREREGISTRATION_EXPLOSIONS_2026-11-08.md, written and pushed BEFORE any event-type label of the study
period was downloaded or read.

Question: how do the frozen triage policies treat alarms caused by explosions (quarry / mining / other blasts)? An
explosion is a real seismic signal, so a triage rule should neither dismiss it silently as noise nor alert it
automatically as an earthquake; the defensible action is ESCALATE (an analyst decides).

PRIMARY (confirmatory, labels unseen): the AK replication (AK.CUT reference, results/ak/outAK_20*, 2024-01-08 ..
2025-07-01). Labels = USGS ComCat event type of current events within 5 degrees of AK.CUT, origin times
2024-01-07T23:50 .. 2025-07-01T00:00, all magnitudes, all statuses, monthly windows, one query per window with the
documented `eventtype` filter set to the explosion family and one with eventtype=earthquake, plus one unfiltered query
used only for the OTHER_NONEQ class. Every URL, row count and sha256 -> results/explosions/labels/download_record.json.
Event-type classes (ComCat vocabulary, fixed in the plan):
  EXPLOSION   = accidental explosion, chemical explosion, chemical_explosion, experimental explosion, explosion,
                industrial explosion, mining explosion, mining_explosion, nuclear explosion, nuclear_explosion, quarry,
                quarry blast, quarry_blast, rock burst, rock_burst, mine collapse, mine_collapse, anthropogenic_event
  EARTHQUAKE  = earthquake, eq
  OTHER_NONEQ = every other type (ice quake, landslide, acoustic noise, sonic boom, other event, volcanic ...)
Matching = the pipeline's association function: p_pred = origin + first P (iasp91; p, P, Pn, Pg, Pdiff) at AK.CUT,
residual r = p_pred - t_on in [-15 s, (t_off - t_on) + 0 s]. Episode class = the class shared by ALL its candidate
events (EXPLOSION / EARTHQUAKE / OTHER_NONEQ); MIXED if candidates of several classes; UNLABELLED if none.
Policies: action code of analysis/cgd_2024.py evaluate() (frozen: P1, P1t 8.0, P2 10.5, P3 7.5, CG, CG-D with the MAKZ
development table) + P3 at 8.0 dB (secondary). Self-checks before scoring (script stops on failure): actions reproduce
results/ak/ak_eval.json "missed" and "alert_unassoc" for P1, P1t, P2, P3, CG, CG-D; p_pred reproduces the stored p_pred of
the AK run catalog.csv to 0.01 s.
X1 CG vs P3 7.5, DISMISS share among EXPLOSION episodes: upper 95 % day-bootstrap bound of (CG - P3) <= 3 pp.
X2 CG-D vs P3 7.5, same.
X3 ALERT share among EXPLOSION episodes: CG < P1t and CG < P3 7.5 (upper 95 % bound of each paired difference < 0).
X4 CG ESCALATE share among EXPLOSION > among EARTHQUAKE episodes: lower 95 % bound of the difference > 0.
X1-X3 not exercised with < 20 EXPLOSION episodes; X4 with < 20 EXPLOSION or < 20 EARTHQUAKE episodes.
Chance control: label p_pred shifted by +-1, +-2, +-3 days; if the mean chance count of a class is >= 50 % of the real
count, results for that class are reported as dominated by chance coincidence.

SECONDARY (descriptive only; labels already seen in run 23 of EXPERIMENT_LEDGER.md): IU.MAKZ extended run 2025-01 ..
2026-02 with the NNC (KNDC) agency labels of results/nnc/episodes_nnc.csv ("mining explosion" vs "earthquake"); same
shares and differences with intervals, for P1t, P3 7.5, P3 8.0, CG, CG-D. Self-check: the recomputed P1t, P3 and CG
actions equal the action columns of results/nnc/episodes_nnc.csv episode by episode.

Day bootstrap over episode dates, 2000 resamples, seed 7 (as every earlier test).
Usage:  python analysis/explosions_v2.py selfcheck   (no label read or downloaded)
        python analysis/explosions_v2.py download    (ComCat labels -> results/explosions/labels/, sha256 recorded)
        python analysis/explosions_v2.py score       (-> results/explosions/explosions_eval.json + run.log)
"""
import os, sys, io, json, glob, re, time, hashlib, datetime as dt, urllib.request, urllib.parse
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(root, "results", "ak"); X = os.path.join(root, "results", "explosions"); L = os.path.join(X, "labels")
REF_LAT, REF_LON = 62.4058, -150.2625            # AK.CUT, as in PREREGISTRATION_AK_NETWORK.md
MAXRADIUS = 5.0
Q0, Q1 = dt.datetime(2024, 1, 7, 23, 50), dt.datetime(2025, 7, 1)
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
ASSOC = (-15.0, 0.0); MIN_N = 20; SHIFTS_D = [-3, -2, -1, 1, 2, 3]; MARGIN = 3.0
EXPLOSION_TYPES = ["accidental explosion", "chemical explosion", "chemical_explosion", "experimental explosion", "explosion",
                   "industrial explosion", "mining explosion", "mining_explosion", "nuclear explosion", "nuclear_explosion",
                   "quarry", "quarry blast", "quarry_blast", "rock burst", "rock_burst", "mine collapse", "mine_collapse",
                   "anthropogenic_event"]
EARTHQUAKE_TYPES = ["earthquake", "eq"]
POL = ["P1", "P1t", "P2", "P3", "P3_8.0", "CG", "CG-D"]
CLASSES = ["EXPLOSION", "EARTHQUAKE", "OTHER_NONEQ", "MIXED", "UNLABELLED"]
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

def type_class(t):
    t = str(t).strip().lower()
    return "EXPLOSION" if t in EXPLOSION_TYPES else ("EARTHQUAKE" if t in EARTHQUAKE_TYPES else "OTHER_NONEQ")

# ---------------------------------------------------------------- labels
def fetch(t0, t1, eventtype):
    q = (f"{URL}?format=csv&orderby=time-asc&starttime={t0:%Y-%m-%dT%H:%M:%S}&endtime={t1:%Y-%m-%dT%H:%M:%S}"
         f"&latitude={REF_LAT}&longitude={REF_LON}&maxradius={MAXRADIUS}" + (f"&eventtype={urllib.parse.quote(eventtype)}" if eventtype else ""))
    for k in range(6):
        try:
            with urllib.request.urlopen(q, timeout=180) as r: txt = r.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(txt)) if txt.strip() else pd.DataFrame()
            if len(df) >= 20000:
                mid = t0 + (t1 - t0) / 2
                return fetch(t0, mid, eventtype) + fetch(mid, t1, eventtype)
            return [(q, txt, df)]
        except Exception as ex:
            log("fetch error", k + 1, str(ex)[:150]); time.sleep(20 * (k + 1))
    raise SystemExit("label download failed: " + q)

def download():
    os.makedirs(L, exist_ok=True); rec = []
    for name, et in [("comcat_explosion_family.csv", ",".join(EXPLOSION_TYPES)), ("comcat_earthquake.csv", "earthquake"), ("comcat_all_types.csv", "")]:
        frames = []; t = Q0
        while t < Q1:
            t1 = min((t.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0), Q1)
            for q, txt, df in fetch(t, t1, et):
                frames.append(df); rec.append({"file": name, "url": q, "rows": int(len(df)), "sha256": hashlib.sha256(txt.encode()).hexdigest()})
            t = t1
        nonempty = [f for f in frames if len(f)]
        df = pd.concat(nonempty, ignore_index=True).drop_duplicates("id") if nonempty else pd.DataFrame(columns=["id", "time", "latitude", "longitude", "depth", "mag", "type", "status"])
        df.to_csv(os.path.join(L, name), index=False); log(name, len(df), "rows")
    for n in ("comcat_explosion_family.csv", "comcat_earthquake.csv", "comcat_all_types.csv"):
        rec.append({"file": n, "sha256_file": hashlib.sha256(open(os.path.join(L, n), "rb").read()).hexdigest()})
    json.dump({"downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "queries": rec},
              open(os.path.join(L, "download_record.json"), "w"), indent=1)
    open(os.path.join(X, "run_download.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

# ---------------------------------------------------------------- travel times (pipeline rule)
def p_pred_table(df):
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

def ptt_selfcheck():
    cat = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(A, "outAK_20*", "catalog.csv")))], ignore_index=True)
    cat = cat[cat.kind == "regional"].iloc[::50].head(200).rename(columns={"lat": "latitude", "lon": "longitude", "depth_km": "depth", "time": "t"})
    err = np.nanmax(np.abs(p_pred_table(cat) - cat.p_pred.to_numpy()))
    if not err < 0.01: raise SystemExit(f"p_pred self-check failed: max error {err}")
    log(f"self-check: p_pred reproduces the pipeline on {len(cat)} AK catalogue rows, max error {err:.4f} s")

def labels():
    ex = pd.read_csv(os.path.join(L, "comcat_explosion_family.csv")); eq = pd.read_csv(os.path.join(L, "comcat_earthquake.csv"))
    al = pd.read_csv(os.path.join(L, "comcat_all_types.csv"))
    # the unfiltered query is the reference; the filtered queries must agree with it on the ids of their class
    al["cls"] = al["type"].map(type_class)
    chk = {"explosion_filter_rows": int(len(ex)), "explosion_in_unfiltered": int((al.cls == "EXPLOSION").sum()),
           "explosion_filter_ids_missing_from_unfiltered": int((~ex.id.isin(al.id)).sum()) if len(ex) else 0,
           "earthquake_filter_rows": int(len(eq)), "earthquake_in_unfiltered": int((al.cls == "EARTHQUAKE").sum())}
    log("label consistency:", chk)
    lab = pd.concat([al, ex[~ex.id.isin(al.id)].assign(cls=lambda d: d["type"].map(type_class)) if len(ex) else None,
                     eq[~eq.id.isin(al.id)].assign(cls=lambda d: d["type"].map(type_class)) if len(eq) else None], ignore_index=True)
    # seconds since 1970 without assuming the datetime unit (pandas 3 parses to microseconds; the first scoring run divided
    # the integer by 1e9 as if it were nanoseconds, so no label time could match any episode -> results/explosions/first_run_unit_error/)
    ts = pd.to_datetime(lab["time"], utc=True)
    lab["t"] = (ts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    from obspy import UTCDateTime
    chk_t = np.array([UTCDateTime(x).timestamp for x in lab["time"].iloc[::max(len(lab) // 500, 1)]])
    err_t = float(np.max(np.abs(chk_t - lab["t"].iloc[::max(len(lab) // 500, 1)].to_numpy())))
    if not err_t < 0.001: raise SystemExit(f"label time self-check failed: max error {err_t} s")
    log(f"self-check: label times equal ObsPy UTCDateTime on {len(chk_t)} rows, max error {err_t:.6f} s")
    lab["p_pred"] = p_pred_table(lab)
    return lab, chk

# ---------------------------------------------------------------- episodes and actions (verbatim from cgd_2024.evaluate)
def _cgd():
    import importlib.util
    spec = importlib.util.spec_from_file_location("m20", os.path.join(root, "analysis", "cgd_2024.py")); m = importlib.util.module_from_spec(spec)
    try: spec.loader.exec_module(m)
    except SystemExit: pass
    return m

def actions(ep, dist, table_ref="MAKZ"):
    m = _cgd(); TAB, BINS, LAB = m.TAB, m.BINS, m.LAB
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
                p = np.array([TAB[table_ref][k].get(bb, {"p": 0.5})["p"] if bb in LAB else 0.5 for bb in b])
                q = np.where(S[k] == "NO", p, q)
            num += W[k] * (S[k] == "YES") * q; den += W[k] * q
        num += W["SNR"] * np.clip(snr / 30, 0, 1) * ok; den += W["SNR"] * ok
        dd = den >= 0.45; D = np.where(dd, num / np.where(den > 0, den, 1), np.nan)
        a = np.full(len(ep), "ESCALATE", dtype=object); a[dd & (D >= 0.60)] = "ALERT"; a[dd & (D <= 0.16)] = "DISMISS"; act[name] = a
    return act

def load_dirs(dirs):
    frames, dist = [], {}
    for d in dirs:
        txt = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(os.path.join(d, "*.log")))
        ep = pd.read_csv(os.path.join(d, "episodes.csv")); ep["day"] = ep.t_on_utc.str[:10]; ep["chunk"] = os.path.basename(d); frames.append(ep)
        dist.update({mm.group(1): float(mm.group(2)) for mm in re.finditer(r"^(\w+) distance_km ([\d.]+)", txt, re.M)})
    return pd.concat(frames, ignore_index=True), dist

def ak_episodes():
    ep, dist = load_dirs(sorted(glob.glob(os.path.join(A, "outAK_20*"))))
    act = actions(ep, dist)
    ref = json.load(open(os.path.join(A, "ak_eval.json")))["all"]; assoc = (ep.assoc_event >= 0).to_numpy()
    for n in ["P1", "P1t", "P2", "P3", "CG", "CG-D"]:
        mine = {"missed": int(((act[n] == "DISMISS") & assoc).sum()), "alert_unassoc": int(((act[n] == "ALERT") & ~assoc).sum())}
        if mine["missed"] != ref[n]["missed"] or mine["alert_unassoc"] != ref[n]["alert_unassoc"]:
            raise SystemExit(f"AK self-check failed for {n}: {mine} vs {ref[n]}")
    log(f"self-check: AK actions reproduce results/ak/ak_eval.json for P1, P1t, P2, P3, CG, CG-D ({len(ep)} episodes)")
    return ep, act

def makz_episodes():
    """IU.MAKZ extended run, same chunk set as analysis/posthoc_extended.py, restricted to the NNC window."""
    E = os.path.join(root, "results", "extended")
    rerun = {os.path.basename(d).replace("outA_", "out_"): d for d in glob.glob(os.path.join(E, "vm_2025_rerun", "outA_*"))}
    dirs = [rerun.get(os.path.basename(d), d) for d in sorted(glob.glob(os.path.join(E, "vm_2025", "out_*")))] + [os.path.join(E, "kaggle_2026h1")]
    ep, dist = load_dirs(dirs)
    act = actions(ep, dist)
    nnc = pd.read_csv(os.path.join(root, "results", "nnc", "episodes_nnc.csv"))
    key = ep.t_on_utc.to_numpy(); pos = {k: i for i, k in enumerate(key)}
    if len(pos) != len(key): log("note: duplicate t_on_utc in MAKZ extended episodes:", len(key) - len(pos))
    idx = np.array([pos.get(k, -1) for k in nnc.t_on_utc])
    if (idx < 0).any(): raise SystemExit(f"MAKZ self-check failed: {(idx < 0).sum()} NNC episodes not found")
    for n in ["P1", "P1t", "P3", "P2", "CG"]:
        bad = int((act[n][idx] != nnc[f"action_{n}"].to_numpy()).sum())
        if bad: raise SystemExit(f"MAKZ self-check failed for {n}: {bad} episodes differ from results/nnc/episodes_nnc.csv")
    log(f"self-check: MAKZ actions equal results/nnc/episodes_nnc.csv for P1, P1t, P3, P2, CG ({len(idx)} episodes)")
    sub = ep.iloc[idx].reset_index(drop=True)
    return sub, {n: a[idx] for n, a in act.items()}, nnc.nnc.to_numpy()

# ---------------------------------------------------------------- matching
def match(ep, lab, shift=0.0):
    ton, toff = ep.t_on.to_numpy(), ep.t_off.to_numpy()
    sets = [set() for _ in range(len(ep))]; ev = np.full(len(ep), "", dtype=object); evtype = np.full(len(ep), "", dtype=object)
    P = lab.p_pred.to_numpy() + shift; o = np.argsort(P); P = P[o]; cls = lab.cls.to_numpy()[o]; ids = lab.id.to_numpy()[o]; typ = lab["type"].astype(str).to_numpy()[o]
    lo = np.searchsorted(P, ton + ASSOC[0], "left"); hi = np.searchsorted(P, toff + ASSOC[1], "right")
    for i in np.flatnonzero(hi > lo):
        sets[i] = set(cls[lo[i]:hi[i]]); j = lo[i] + int(np.argmin(np.abs(P[lo[i]:hi[i]] - ton[i]))); ev[i] = ids[j]; evtype[i] = typ[j]
    out = np.array(["UNLABELLED" if not s else (next(iter(s)) if len(s) == 1 else "MIXED") for s in sets], dtype=object)
    return out, ev, evtype

# ---------------------------------------------------------------- statistics
def boot(days, fn, seed=7, n=2000):
    rng = np.random.default_rng(seed); ud = np.array(sorted(set(days))); idx = {d: np.flatnonzero(days == d) for d in ud}; v = []
    for _ in range(n):
        ids = np.concatenate([idx[d] for d in rng.choice(ud, len(ud))]); x = fn(ids)
        if x is not None and np.isfinite(x): v.append(x)
    return [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)] if v else [None, None]

def sh(a, m, w): return float((a[m] == w).mean() * 100) if m.any() else np.nan

def pdiff(act, cls, days, a, b, k, w):
    """paired difference of the share of action w within class k: policy a - policy b, day bootstrap."""
    m = cls == k; obs = sh(act[a], m, w) - sh(act[b], m, w)
    def f(ids):
        mm = m[ids]
        return ((act[a][ids][mm] == w).mean() - (act[b][ids][mm] == w).mean()) * 100 if mm.any() else None
    return {"diff_pp": round(obs, 2) if np.isfinite(obs) else None, "ci95_pp": boot(days, f)}

def cdiff(act, cls, days, p, k1, k2, w):
    """difference of the share of action w for one policy between classes k1 and k2, days resampled jointly."""
    m1, m2 = cls == k1, cls == k2; obs = sh(act[p], m1, w) - sh(act[p], m2, w)
    def f(ids):
        a = act[p][ids]; x1, x2 = m1[ids], m2[ids]
        return ((a[x1] == w).mean() - (a[x2] == w).mean()) * 100 if x1.any() and x2.any() else None
    return {"diff_pp": round(obs, 2) if np.isfinite(obs) else None, "ci95_pp": boot(days, f)}

def shares(act, cls, classes, pols):
    return {n: {k: {"n": int((cls == k).sum()), **{w: round(sh(act[n], cls == k, w), 2) if (cls == k).any() else None
                                                   for w in ["DISMISS", "ESCALATE", "ALERT"]}} for k in classes} for n in pols}

def share_ci(act, cls, days, pols, k):
    out = {}
    for n in pols:
        m = cls == k
        out[n] = {w: boot(days, lambda ids, n=n, w=w: ((act[n][ids][m[ids]] == w).mean() * 100) if m[ids].any() else None)
                  for w in ["DISMISS", "ESCALATE", "ALERT"]}
    return out

# ---------------------------------------------------------------- scoring
def score():
    os.makedirs(X, exist_ok=True)
    ep, act = ak_episodes(); ptt_selfcheck()
    lab, chk = labels(); log("label classes:", lab.cls.value_counts().to_dict())
    cls, evid, evtype = match(ep, lab); ep["xcls"] = cls; ep["x_event"] = evid; ep["x_type"] = evtype
    days = ep.day.to_numpy(); assoc = (ep.assoc_event >= 0).to_numpy(); E = cls == "EXPLOSION"; Q = cls == "EARTHQUAKE"
    nE, nQ = int(E.sum()), int(Q.sum())
    res = {"preregistration": "PREREGISTRATION_EXPLOSIONS_2026-11-08.md", "scorer": "analysis/explosions_v2.py",
           "primary": "AK replication, AK.CUT, results/ak/outAK_20*", "episodes": int(len(ep)), "calendar_days_with_episodes": int(len(set(days))),
           "label_consistency": chk,
           "labels_by_class": {k: int(v) for k, v in lab.cls.value_counts().items()},
           "labels_by_type": {k: int(v) for k, v in lab["type"].astype(str).value_counts().items()},
           "explosion_labels_by_status": {k: int(v) for k, v in lab[lab.cls == "EXPLOSION"].status.astype(str).value_counts().items()},
           "explosion_label_magnitude_quantiles": {q: round(float(lab[lab.cls == "EXPLOSION"].mag.quantile(q)), 2) for q in [0.1, 0.5, 0.9]} if (lab.cls == "EXPLOSION").any() else None,
           "episode_classes": {k: int((cls == k).sum()) for k in CLASSES},
           "explosion_episodes_by_type": {k: int(v) for k, v in pd.Series(evtype[E]).value_counts().items()},
           "cross_with_original_association": {k: {"associated": int(((cls == k) & assoc).sum()), "unassociated": int(((cls == k) & ~assoc).sum())} for k in CLASSES}}
    # chance control
    ch = {k: [] for k in CLASSES}
    for s in SHIFTS_D:
        c2, _, _ = match(ep, lab, shift=s * 86400.0)
        for k in CLASSES: ch[k].append(int((c2 == k).sum()))
    res["chance_control"] = {k: {"real": int((cls == k).sum()), "shifted_counts": ch[k], "mean": round(float(np.mean(ch[k])), 2),
                                 "dominated_by_chance": bool(np.mean(ch[k]) >= 0.5 * max(int((cls == k).sum()), 1)) if (cls == k).any() else None}
                             for k in ["EXPLOSION", "EARTHQUAKE", "OTHER_NONEQ"]}
    res["action_share_within_class_pct"] = shares(act, cls, CLASSES, POL)
    res["explosion_share_ci95"] = share_ci(act, cls, days, POL, "EXPLOSION") if nE else None
    res["unassociated_alerts_by_class"] = {n: {k: int(((act[n] == "ALERT") & ~assoc & (cls == k)).sum()) for k in CLASSES} for n in POL}
    res["explosion_episode_hour_utc"] = {int(h): int(v) for h, v in pd.to_datetime(ep.t_on_utc[E]).dt.hour.value_counts().sort_index().items()} if nE else {}
    res["explosion_episode_snr_db_quantiles"] = {q: round(float(ep.snr_db[E].quantile(q)), 2) for q in [0.1, 0.5, 0.9]} if nE else None
    res["earthquake_episode_snr_db_quantiles"] = {q: round(float(ep.snr_db[Q].quantile(q)), 2) for q in [0.1, 0.5, 0.9]} if nQ else None
    exE = nE >= MIN_N
    x1 = pdiff(act, cls, days, "CG", "P3", "EXPLOSION", "DISMISS"); x2 = pdiff(act, cls, days, "CG-D", "P3", "EXPLOSION", "DISMISS")
    x3a = pdiff(act, cls, days, "CG", "P1t", "EXPLOSION", "ALERT"); x3b = pdiff(act, cls, days, "CG", "P3", "EXPLOSION", "ALERT")
    x4 = cdiff(act, cls, days, "CG", "EXPLOSION", "EARTHQUAKE", "ESCALATE")
    hi = lambda d: d["ci95_pp"][1]; lo = lambda d: d["ci95_pp"][0]
    res["X1_CG_vs_P3_dismiss_explosion"] = {**x1, "margin_pp": MARGIN, "exercised": exE, "holds": (hi(x1) is not None and hi(x1) <= MARGIN) if exE else None}
    res["X2_CGD_vs_P3_dismiss_explosion"] = {**x2, "margin_pp": MARGIN, "exercised": exE, "holds": (hi(x2) is not None and hi(x2) <= MARGIN) if exE else None}
    res["X3_alert_explosion"] = {"CG_minus_P1t": x3a, "CG_minus_P3": x3b, "exercised": exE,
                                 "holds": (hi(x3a) is not None and hi(x3b) is not None and hi(x3a) < 0 and hi(x3b) < 0) if exE else None}
    ex4 = nE >= MIN_N and nQ >= MIN_N
    res["X4_CG_escalate_explosion_minus_earthquake"] = {**x4, "exercised": ex4, "holds": (lo(x4) is not None and lo(x4) > 0) if ex4 else None}
    res["descriptive_all_policies"] = {
        "dismiss_vs_P3_explosion": {n: pdiff(act, cls, days, n, "P3", "EXPLOSION", "DISMISS") for n in POL if n != "P3"},
        "escalate_explosion_minus_earthquake": {n: cdiff(act, cls, days, n, "EXPLOSION", "EARTHQUAKE", "ESCALATE") for n in POL},
        "dismiss_explosion_minus_earthquake": {n: cdiff(act, cls, days, n, "EXPLOSION", "EARTHQUAKE", "DISMISS") for n in POL}} if nE else None
    res["chance_note"] = ("EXPLOSION results are dominated by chance coincidence" if res["chance_control"]["EXPLOSION"]["dominated_by_chance"] else "")
    # secondary: IU.MAKZ + NNC labels (descriptive, labels seen before)
    sub, mact, nnc = makz_episodes()
    mcls = np.where(nnc == "mining explosion", "EXPLOSION", np.where(nnc == "earthquake", "EARTHQUAKE", "NO_NNC_EVENT")).astype(object)
    mdays = sub.day.to_numpy(); SP = ["P1t", "P3", "P3_8.0", "CG", "CG-D"]
    res["secondary_MAKZ_NNC_descriptive"] = {
        "status": "descriptive; NNC labels already seen in run 23 (dismiss/alert counts of P1, P1t, P2, P3, CG published in results/nnc/nnc_eval.json); new here: ESCALATE shares, CG-D, P3 8.0, intervals",
        "episodes": int(len(sub)), "classes": {k: int((mcls == k).sum()) for k in ["EXPLOSION", "EARTHQUAKE", "NO_NNC_EVENT"]},
        "action_share_within_class_pct": shares(mact, mcls, ["EXPLOSION", "EARTHQUAKE"], SP),
        "explosion_share_ci95": share_ci(mact, mcls, mdays, SP, "EXPLOSION"),
        "CG_minus_P3_dismiss_explosion": pdiff(mact, mcls, mdays, "CG", "P3", "EXPLOSION", "DISMISS"),
        "CGD_minus_P3_dismiss_explosion": pdiff(mact, mcls, mdays, "CG-D", "P3", "EXPLOSION", "DISMISS"),
        "CG_minus_P1t_alert_explosion": pdiff(mact, mcls, mdays, "CG", "P1t", "EXPLOSION", "ALERT"),
        "CG_minus_P3_alert_explosion": pdiff(mact, mcls, mdays, "CG", "P3", "EXPLOSION", "ALERT"),
        "CG_escalate_explosion_minus_earthquake": cdiff(mact, mcls, mdays, "CG", "EXPLOSION", "EARTHQUAKE", "ESCALATE"),
        "CGD_escalate_explosion_minus_earthquake": cdiff(mact, mcls, mdays, "CG-D", "EXPLOSION", "EARTHQUAKE", "ESCALATE")}
    json.dump(res, open(os.path.join(X, "explosions_eval.json"), "w"), indent=1, default=str)
    cols = ["t_on_utc", "day", "snr_db", "assoc_event", "xcls", "x_event", "x_type"]
    out = ep[cols].copy()
    for n in POL: out["action_" + n] = act[n]
    out[out.xcls != "UNLABELLED"].to_csv(os.path.join(X, "episodes_labelled.csv.gz"), index=False, compression="gzip")
    log(json.dumps({k: res[k] for k in ["episode_classes", "chance_control", "X1_CG_vs_P3_dismiss_explosion", "X2_CGD_vs_P3_dismiss_explosion",
                                         "X3_alert_explosion", "X4_CG_escalate_explosion_minus_earthquake"]}, indent=1, default=str))
    open(os.path.join(X, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "selfcheck":
        ak_episodes(); ptt_selfcheck(); makz_episodes()
    elif cmd == "download": download()
    elif cmd == "score": score()
    else: raise SystemExit(__doc__)
