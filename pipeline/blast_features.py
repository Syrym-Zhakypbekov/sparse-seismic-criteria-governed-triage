"""Waveform features at IU.MAKZ for NNC events (PREREGISTRATION_BLAST.md, commit 3f77906).
Input events.csv (time, lat, lon, depth_km, type, dist_deg, p_pred). Output features.csv (one row per event), run.log.
f1 = log10(RMS 6-12 Hz / RMS 1-4 Hz) in [p, p+6 s]; f2 = log10(RMS 2-8 Hz [p, p+5] / RMS 2-8 Hz [s, s+8]);
quality: window complete and window/noise RMS >= 3 dB (noise [p-35, p-5]).
"""
import sys, time, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.taup import TauPyModel

EV = sys.argv[1] if len(sys.argv) > 1 else "events.csv"; OUT = sys.argv[2] if len(sys.argv) > 2 else "features.csv"
model = TauPyModel("iasp91")

def rms(x): return float(np.sqrt(np.mean(x ** 2))) if len(x) else np.nan

def one(r):
    out = {"time": r.time, "type": r.type, "dist_deg": r.dist_deg}
    try:
        p = UTCDateTime(float(r.p_pred))
        arr = model.get_travel_times(source_depth_in_km=max(float(r.depth_km), 0), distance_in_degree=float(r.dist_deg), phase_list=["s", "S", "Sn", "Sg"])
        s = UTCDateTime(float(r.time)) + min(a.time for a in arr) if arr else p + float(r.dist_deg) * 111.2 * (1 / 3.6 - 1 / 6.2)
        out["s_minus_p"] = float(s - p)
        for att in range(4):
            try:
                st = Client("EARTHSCOPE", timeout=60).get_waveforms("IU", "MAKZ", "00", "BHZ", p - 120, s + 60); break
            except Exception as e:
                if "No data" in str(e) or "204" in str(e): out["err"] = "nodata"; return out
                time.sleep(5 * (att + 1)); st = None
        if st is None: out["err"] = "fetch"; return out
        gaps = len(st) > 1; st.merge(fill_value=0); tr = st[0]; sr = tr.stats.sampling_rate; out["sr"] = sr
        tr.detrend("demean"); tr.taper(0.01)
        def band(f1, f2):
            t = tr.copy(); t.filter("bandpass", freqmin=f1, freqmax=min(f2, 0.45 * sr), corners=4, zerophase=False); return t
        def win(t, a, b):
            i0 = int((a - t.stats.starttime) * sr); i1 = int((b - t.stats.starttime) * sr); return t.data[max(i0, 0):max(i1, 0)]
        hi, lo, mid = band(6, 12), band(1, 4), band(2, 8)
        nz = rms(win(mid, p - 35, p - 5)); pw = rms(win(mid, p, p + 5)); sw = rms(win(mid, s, s + 8))
        out["snr_p_db"] = 20 * np.log10(pw / nz) if nz > 0 and pw > 0 else np.nan
        out["snr_s_db"] = 20 * np.log10(sw / nz) if nz > 0 and sw > 0 else np.nan
        h, l = rms(win(hi, p, p + 6)), rms(win(lo, p, p + 6))
        out["f1_spec_ratio"] = np.log10(h / l) if h > 0 and l > 0 else np.nan
        out["f2_p_s_ratio"] = np.log10(pw / sw) if pw > 0 and sw > 0 else np.nan
        out["gaps"] = bool(gaps)
        out["q_f1"] = int((not gaps) and np.isfinite(out["f1_spec_ratio"]) and out["snr_p_db"] >= 3)
        out["q_f2"] = int((not gaps) and np.isfinite(out["f2_p_s_ratio"]) and out["snr_p_db"] >= 3 and out["snr_s_db"] >= 3)
    except Exception as e:
        out["err"] = str(e)[:120]
    return out

ev = pd.read_csv(EV); t0 = time.time(); rows = []
with ThreadPoolExecutor(8) as ex:
    for i, o in enumerate(ex.map(one, [r for _, r in ev.iterrows()])):
        rows.append(o)
        if i % 100 == 0: print(i, len(ev), round(time.time() - t0), "s", flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
print("done", len(rows), "errors", sum(1 for r in rows if "err" in r), "seconds", round(time.time() - t0), flush=True)
