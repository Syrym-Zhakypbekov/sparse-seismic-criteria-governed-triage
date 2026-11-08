# P10 Sensors — stage 1, v3 (07.11.2026): measurement chain repaired after Codex review R1 (phase A of FIX_PLAN.md).
# Fixes:
#   M05 — no zero fill; padded day windows (continuity across midnight); split at gaps; warm-up masked; validity mask.
#   M04 — SNR = RMS(signal)/RMS(noise) in dB with a guard gap; INVALID when either window touches a gap.
#   M06 — neighbour evidence per episode window: YES / NO (valid & silent) / MISSING.
#   M07 — window |dt| <= d/5.5 km/s + 5 s (max differential P time between two stations for any source).
#   M09/M10 — one association function (signed residual), regional (ISC + USGS, <=15 deg) and teleseismic (USGS M>=5.5) separate.
#   explicit channels; real NSLC ids recorded.
# Period: development = 2026-07-01..09-30 (tuning = first 7 days, threshold only). Held-out test is NOT run here.
import subprocess, sys, os
if not os.environ.get("P10_NO_PIP"):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "obspy==1.5.1"], check=True)

import os, json, time
import numpy as np, pandas as pd
from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.signal.trigger import recursive_sta_lta
from obspy.geodetics import gps2dist_azimuth
from obspy.taup import TauPyModel

T0 = UTCDateTime(os.environ.get("P10_T0", "2026-07-01"))
TUNE_END = UTCDateTime(os.environ.get("P10_TUNE_END", "2026-07-08"))
T1 = UTCDateTime(os.environ.get("P10_T1", "2026-10-01"))
# evaluation starts here (held-out run: 2026-10-01); days between TUNE_END and EVAL_START are skipped
EVAL_START = UTCDateTime(os.environ.get("P10_EVAL_START", str(TUNE_END)))
W = os.environ.get("P10_OUT", "/kaggle/working")
CACHE = os.environ.get("P10_CACHE", "/kaggle/tmp/p10cache" if W == "/kaggle/working" else os.path.join(W, "cache"))
os.makedirs(CACHE, exist_ok=True)   # outside /kaggle/working: the 1.5 GB waveform cache must not be returned as output
STATIONS = {"MAKZ": ("IU", "MAKZ", "00", "BHZ", 46.808, 81.977),
            "MK31": ("IM", "MK31", "*", "?HZ", 46.793682, 82.290565),
            "KURK": ("II", "KURK", "00", "BHZ", 50.7154, 78.6202),
            "WUS": ("G", "WUS", "00", "BHZ", 41.200716, 79.216498)}
if os.environ.get("P10_STATIONS"):   # role -> [net, sta, loc, cha, lat, lon]; roles keep their names (second-network replication)
    STATIONS = {k: tuple(v) for k, v in json.loads(os.environ["P10_STATIONS"]).items()}
REF = os.environ.get("P10_REF", "MAKZ")   # reference station (second-reference experiment: KURK)
STA, LTA, Q, GAP, FMIN, FMAX = 1.0, 30.0, 99.9, 20.0, 1.0, 8.0
PAD = 1800.0            # s of padding each side of a day
WARM = 3 * LTA          # s masked after the start of every continuous segment
V_MIN, PICK_TOL = 5.5, 5.0
NOISE = (-35.0, -5.0); SIGNAL = (0.0, 10.0)       # s relative to t_on
COVER_MIN = 0.9         # share of valid seconds needed to call a neighbour window "observed"
ASSOC = (-15.0, 0.0)    # predicted P in [t_on - 15 s, t_off + 0 s]
wf, usgs = Client("EARTHSCOPE"), Client("USGS")
model = TauPyModel("iasp91")
ids_seen = {}

FETCH_FAIL = []

def fetch(key, day):
    net, sta, loc, cha = STATIONS[key][:4]
    fn = os.path.join(CACHE, f"{key}.{day.strftime('%Y%m%d')}.mseed")
    if os.path.exists(fn):
        return read(fn) if os.path.getsize(fn) else None
    for att in range(8):
        try:
            time.sleep(float(os.environ.get("P10_FETCH_PAUSE", "0")))
            st = wf.get_waveforms(net, sta, loc, cha, day - PAD, day + 86400 + PAD)
            # explicit single stream: first Z channel id in sorted order, recorded
            sid = sorted({tr.id for tr in st if tr.stats.channel.endswith("Z")})[0]
            st = st.select(id=sid)
            ids_seen.setdefault(key, set()).add(sid)
            st.write(fn, format="MSEED"); return st
        except Exception as e:
            err = str(e)
            if "No data" in err or "204" in err:
                open(fn, "wb").close(); return None          # true absence: cached as empty
            if "429" in err or "Too Many" in err or "rate limit" in err:
                time.sleep(min(600, 60 * (att + 1))); continue   # rate limiting: back off, never cache as missing
            time.sleep(5 * (att + 1))
    FETCH_FAIL.append(f"{key} {day.date}")                  # download failed: NOT cached; reported in summary.json
    return None

def process(st, day):
    """Return 1 Hz arrays over [day, day+86400): cft (nan where invalid), valid (bool), and filtered segments for SNR."""
    n = 86400
    cft = np.full(n, np.nan); valid = np.zeros(n, bool); segs = []
    if st is None:
        return cft, valid, segs
    st = st.copy(); st.merge(method=1)          # masked where gaps; no fill
    for tr in st.split():                       # contiguous pieces only
        df = tr.stats.sampling_rate
        if tr.stats.npts < (LTA + WARM) * df:
            continue
        tr.detrend("demean"); tr.taper(0.01)
        tr.filter("bandpass", freqmin=FMIN, freqmax=min(FMAX, 0.45 * df), corners=4, zerophase=False)
        c = recursive_sta_lta(tr.data.astype(float), int(STA * df), int(LTA * df))
        t0 = float(tr.stats.starttime)
        first_ok = t0 + WARM
        secs = np.arange(int(np.ceil(first_ok)), int(np.floor(float(tr.stats.endtime))))
        secs = secs[(secs >= float(day)) & (secs < float(day) + n)]
        if not len(secs):
            continue
        idx = ((secs - t0) * df).astype(int)
        step = int(df)
        vals = np.array([c[i:i + step].max() for i in idx])
        k = (secs - int(float(day))).astype(int)
        cft[k] = vals; valid[k] = True
        segs.append(tr)
    return cft, valid, segs

def snr_db(segs, t_on):
    for tr in segs:
        a, b = float(tr.stats.starttime), float(tr.stats.endtime)
        if a + WARM <= t_on + NOISE[0] and t_on + SIGNAL[1] <= b:
            df = tr.stats.sampling_rate
            nz = tr.data[int((t_on + NOISE[0] - a) * df):int((t_on + NOISE[1] - a) * df)].astype(float)
            sg = tr.data[int((t_on + SIGNAL[0] - a) * df):int((t_on + SIGNAL[1] - a) * df)].astype(float)
            rn, rs = np.sqrt(np.mean(nz ** 2)), np.sqrt(np.mean(sg ** 2))
            if rn <= 0 or not np.isfinite(rn) or not np.isfinite(rs):
                return np.nan, "INVALID"
            return float(20 * np.log10(rs / rn)), "OK"
    return np.nan, "INVALID"

def episodes_from(cft, valid, day, thr):
    out = []; base = float(day)
    idx = np.flatnonzero(valid & (cft > thr))
    if not len(idx):
        return out
    start = prev = idx[0]
    for i in list(idx[1:]) + [None]:
        if i is None or i - prev > GAP:
            if prev > start:                      # >= 2 seconds
                out.append((base + start, base + prev + 1, float(np.nanmax(cft[start:prev + 1]))))
            if i is not None:
                start = i
        if i is not None:
            prev = i
    return out

days = []
d = T0
while d < T1:
    if d < TUNE_END or d >= EVAL_START:
        days.append(d)
    d += 86400

# pass 1: thresholds on the tuning week only
tune_vals = {k: [] for k in STATIONS}
for day in [x for x in days if x < TUNE_END]:
    for k in STATIONS:
        c, v, _ = process(fetch(k, day), day)
        tune_vals[k].append(c[v])
thr = {k: float(np.percentile(np.concatenate(v), Q)) if sum(len(x) for x in v) else float("nan") for k, v in tune_vals.items()}
if os.environ.get("P10_FIXED_THR"):
    thr = {k: float(v) for k, v in json.loads(os.environ["P10_FIXED_THR"]).items()}   # frozen detector (extended run)
print("thresholds", thr, flush=True)

# pass 2: development days
trig = {k: [] for k in STATIONS}; valid_all = {k: {} for k in STATIONS}; avail = []; ref_eps = []
for day in [x for x in days if x >= TUNE_END]:
    row = {"day": str(day.date)}
    for k in STATIONS:
        c, v, segs = process(fetch(k, day), day)
        valid_all[k][str(day.date)] = v
        row[k + "_valid_share"] = round(float(v.mean()), 4)
        eps = episodes_from(c, v, day, thr[k])
        trig[k] += eps
        if k == REF:
            for a, b, p in eps:
                s, st_ = snr_db(segs, a)
                ref_eps.append({"t_on": a, "t_off": b, "peak_cft": p, "snr_db": s, "snr_status": st_})
    avail.append(row); print(row, flush=True)

def valid_share(k, a, b):
    tot = ok = 0
    t = int(a)
    while t < int(b):
        day = str(UTCDateTime(t).date); v = valid_all[k].get(day)
        sec = t - int(float(UTCDateTime(day)))
        tot += 1; ok += bool(v[sec]) if v is not None and 0 <= sec < 86400 else 0
        t += 1
    return ok / max(1, tot)

ref = STATIONS[REF]
for k in STATIONS:
    if k == REF: continue
    s = STATIONS[k]; dkm = gps2dist_azimuth(ref[4], ref[5], s[4], s[5])[0] / 1000
    win = dkm / V_MIN + PICK_TOL
    starts = np.array(sorted(a for a, _, _ in trig[k]))
    for e in ref_eps:
        lo, hi = e["t_on"] - win, e["t_on"] + win
        j = np.searchsorted(starts, lo); yes = bool(j < len(starts) and starts[j] <= hi)
        cov = valid_share(k, lo, hi)
        e["n_" + k] = "YES" if yes else ("NO" if cov >= COVER_MIN else "MISSING")
        e["cov_" + k] = round(cov, 3)
    print(k, "distance_km", round(dkm, 1), "window_s", round(win, 1), flush=True)

# catalogues: regional (ISC preferred, USGS added) and teleseismic (USGS)
crow = []
def add(cat, src, kind):
    for ev in cat:
        o = ev.preferred_origin() or ev.origins[0]
        m = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
        deg = gps2dist_azimuth(ref[4], ref[5], o.latitude, o.longitude)[0] / 111195
        arr = model.get_travel_times(source_depth_in_km=max((o.depth or 0) / 1000, 0), distance_in_degree=deg, phase_list=["p", "P", "Pn", "Pg", "Pdiff"])
        crow.append({"kind": kind, "source": src, "time": float(o.time), "lat": o.latitude, "lon": o.longitude,
                     "depth_km": (o.depth or 0) / 1000, "mag": m.mag if m else np.nan, "mag_type": m.magnitude_type if m else "",
                     "dist_deg": deg, "p_pred": float(o.time + min(a.time for a in arr)) if arr else np.nan})
CAT_FAIL = []
for src, cl in (("ISC", "ISC"), ("USGS", "USGS")):
    for attempt in range(8):   # ISC rate-limits parallel clients: retry with back-off, never continue silently
        try:
            add(Client(cl).get_events(starttime=EVAL_START, endtime=T1, latitude=ref[4], longitude=ref[5], maxradius=15, minmagnitude=2.0), src, "regional")
            break
        except Exception as ex:
            print(src, "regional catalog error (attempt", attempt + 1, ")", str(ex)[:200], flush=True)
            time.sleep(60 * (attempt + 1))
    else:
        CAT_FAIL.append(src)
try:
    add(usgs.get_events(starttime=EVAL_START, endtime=T1, minmagnitude=5.5), "USGS", "tele")
except Exception as ex:
    print("tele catalog error", str(ex)[:200], flush=True)
cat = pd.DataFrame(crow)
if len(cat):
    cat = cat.sort_values("time")
    # de-duplicate the same event from two agencies: within 20 s and 0.5 deg
    keep, last = [], []
    for _, r in cat.iterrows():
        if any(abs(r.time - x.time) < 20 and abs(r.lat - x.lat) < 0.5 and abs(r.lon - x.lon) < 0.5 for x in last):
            continue
        keep.append(r); last = [x for x in last if r.time - x.time < 60] + [r]
    cat = pd.DataFrame(keep)
    cat["kind"] = np.where(cat.dist_deg <= 15, "regional", "tele")   # one definition by distance

# ONE association function for every metric: signed residual r = p_pred - t_on, inside [ASSOC0, (t_off - t_on) + ASSOC1]
ep = pd.DataFrame(ref_eps)
ep["assoc_event"] = -1; ep["assoc_residual_s"] = np.nan; ep["assoc_kind"] = ""
cat = cat.reset_index(drop=True)
cat["assoc_episode"] = -1
P = cat.p_pred.to_numpy() if len(cat) else np.array([])
for i, e in ep.iterrows():
    r = P - e.t_on
    ok = np.flatnonzero((r >= ASSOC[0]) & (r <= (e.t_off - e.t_on) + ASSOC[1]))
    if len(ok):
        j = ok[np.argmin(np.abs(r[ok]))]
        ep.at[i, "assoc_event"] = int(j); ep.at[i, "assoc_residual_s"] = float(r[j]); ep.at[i, "assoc_kind"] = cat.at[j, "kind"]
        if cat.at[j, "assoc_episode"] < 0:
            cat.at[j, "assoc_episode"] = int(i)
# MAKZ valid at the predicted arrival? (an event during a MAKZ gap is not a miss)
cat["makz_valid_at_p"] = [valid_share(REF, p - 15, p + 15) >= COVER_MIN if np.isfinite(p) else False for p in cat.p_pred]

for c in ("t_on", "t_off"):
    ep[c + "_utc"] = [str(UTCDateTime(x)) for x in ep[c]]
ep.to_csv(f"{W}/episodes.csv", index=False); cat.to_csv(f"{W}/catalog.csv", index=False)
pd.DataFrame(avail).to_csv(f"{W}/availability.csv", index=False)
summ = {"version": "v3", "dev_days": len(avail), "thresholds_q99.9": thr, "channel_ids": {k: sorted(v) for k, v in ids_seen.items()},
        "episodes": {k: len(v) for k, v in trig.items()}, "ref_episodes_per_day": len(ep) / max(1, len(avail)),
        "catalog_failures": CAT_FAIL, "fetch_failures": FETCH_FAIL, "reference": REF, "snr_invalid": int((ep.snr_status == "INVALID").sum()) if len(ep) else 0,
        "catalog": {"regional": int((cat.kind == "regional").sum()) if len(cat) else 0, "tele": int((cat.kind == "tele").sum()) if len(cat) else 0},
        "params": {"sta": STA, "lta": LTA, "q": Q, "gap_s": GAP, "band": [FMIN, FMAX], "pad_s": PAD, "warm_s": WARM,
                   "v_min": V_MIN, "pick_tol": PICK_TOL, "noise": NOISE, "signal": SIGNAL, "cover_min": COVER_MIN, "assoc": ASSOC,
                   "tune": [str(T0), str(TUNE_END)], "dev": [str(EVAL_START), str(T1)]}}
json.dump(summ, open(f"{W}/summary.json", "w"), indent=1, default=str); print(json.dumps(summ, indent=1, default=str))
