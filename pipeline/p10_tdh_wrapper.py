"""Wrapper of PLAN_TIME_DISJOINT_2023_2026-11-08.md (section 6). Runs pipeline/extended_stalta_criteria.py UNCHANGED (sha256 checked,
the same check as pipeline/p10_v2_datacentre_wrapper.py) and adds two things that change no decision:

1. Data-centre redirect, as p10_v2_datacentre_wrapper.py: Client("EARTHSCOPE") -> P10_FDSN_BASE when set.
2. P10_OFFLINE=1: waveform requests are disabled. The pipeline reads its cache (filled from the bucket copy
   gs://p10-raw-waveforms/tdh2023/<NET>/); a role-day missing from the cache raises inside the pipeline's own fetch(), which records
   it as a fetch failure in summary.json (it is never downloaded and never cached as empty).
3. After the pipeline has finished and written episodes.csv, catalog.csv, availability.csv and summary.json, the trigger lists it
   kept in memory (variable trig: onset, end, peak STA/LTA of every role) are written to triggers.csv, and the YES window of each
   neighbour role (distance / 5.5 km/s + 5 s, the pipeline's own formula) to triggers_meta.json.
Usage: P10_STATIONS=... P10_OUT=... [P10_FDSN_BASE=...] [P10_OFFLINE=1] python pipeline/p10_tdh_wrapper.py
"""
import os, sys, json, hashlib, runpy, datetime as dt
import obspy.clients.fdsn as fdsn

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.environ.get("P10_PIPELINE", os.path.join(HERE, "extended_stalta_criteria.py"))
FROZEN_SHA256 = "4c8c9a715bdfc94c7790ac0793f85360ae6a75489ca197acc2aad92483168284"   # LF-normalised, as committed at 9a8436c
got = hashlib.sha256(open(PIPE, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
if got != FROZEN_SHA256:
    sys.exit(f"pipeline sha256 {got} differs from the frozen {FROZEN_SHA256}")

_Base = fdsn.Client
BASE = os.environ.get("P10_FDSN_BASE", "").strip()
OFFLINE = os.environ.get("P10_OFFLINE", "") == "1"


class Client(_Base):
    def __init__(self, base_url="EARTHSCOPE", *a, **k):
        if base_url == "EARTHSCOPE" and BASE:
            base_url = BASE
        super().__init__(base_url, *a, **k)

    def get_waveforms(self, *a, **k):
        if OFFLINE:
            raise RuntimeError("P10_OFFLINE: role-day not present in the bucket copy (not downloaded here)")
        return super().get_waveforms(*a, **k)


fdsn.Client = Client
g = runpy.run_path(PIPE, run_name="__main__")

# ---- after the frozen pipeline finished: dump the trigger lists it kept in memory (no decision is touched)
W = g["W"]; trig = g["trig"]; ST = g["STATIONS"]; REF = g["REF"]
with open(os.path.join(W, "triggers.csv"), "w", encoding="utf-8", newline="") as f:
    f.write("role,t_on,t_off,peak_cft\n")
    for role in ST:
        for a, b, p in trig.get(role, []):
            f.write(f"{role},{a!r},{b!r},{p!r}\n")
ref = ST[REF]; win = {}
for k, s in ST.items():
    if k == REF: continue
    dkm = g["gps2dist_azimuth"](ref[4], ref[5], s[4], s[5])[0] / 1000
    win[k] = {"distance_km": dkm, "window_s": dkm / g["V_MIN"] + g["PICK_TOL"]}
ep_sha = hashlib.sha256(open(os.path.join(W, "episodes.csv"), "rb").read()).hexdigest()
json.dump({"reference": REF, "triggers_per_role": {k: len(trig.get(k, [])) for k in ST}, "yes_window": win,
           "span": [str(g["EVAL_START"]), str(g["T1"])], "offline": OFFLINE, "episodes_csv_sha256_at_dump": ep_sha,
           "wrapper": "pipeline/p10_tdh_wrapper.py", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
          open(os.path.join(W, "triggers_meta.json"), "w"), indent=1)
print("triggers written", {k: len(trig.get(k, [])) for k in ST}, flush=True)
