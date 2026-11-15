"""PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md section 5: download every role-day of 2023 ONCE and store it in the bucket.
Request = the pipeline's own fetch() (pipeline/extended_stalta_criteria.py, copied as in analysis/tdh2023/download_raw.py):
Client("EARTHSCOPE").get_waveforms(net, sta, loc, cha, day - 1800 s, day + 86400 s + 1800 s); first Z id in sorted order; MiniSEED.
"No data"/204 -> empty file; 429 -> back-off, never stored as absent; other errors: 8 attempts, then "failed" (no file).
A file already on disk is never requested again. Files: <STAGE>/<NET>/<ROLE>.<YYYYMMDD>.mseed (the pipeline's cache naming).
At the end of a network: rsync to gs://p10-raw-waveforms/tdh2023_p1/<NET>/, sizes read back, manifest results/tdh2023_p1/download/<NET>.json.
Usage: python analysis/tdh2023_p1/download.py [NET ...]   env TDH_STAGE (default C:/dev/p10tdh_p1_raw), TDH_ES (parallel, default 10)
"""
import os, sys, json, time, threading, subprocess, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(root, "results", "tdh2023_p1", "networks_tdh2023_p1.json"), encoding="utf-8"))
STAGE = os.environ.get("TDH_STAGE", "C:/dev/p10tdh_p1_raw")
GCLOUD = os.environ.get("GCLOUD", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd"))
BUCKET = "gs://p10-raw-waveforms/tdh2023_p1"
MAN = os.path.join(root, "results", "tdh2023_p1", "download"); os.makedirs(MAN, exist_ok=True)
PAD = 1800.0; PAUSE = float(os.environ.get("TDH_PAUSE", "0.5")); PAR = int(os.environ.get("TDH_ES", "10"))
LOCK = threading.Lock(); TL = threading.local()


def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def client():
    if getattr(TL, "cl", None) is None: TL.cl = Client("EARTHSCOPE")
    return TL.cl


def fetch(nslc, day, fn):
    net, sta, loc, cha = nslc; err = ""
    for att in range(8):
        try:
            time.sleep(PAUSE)
            st = client().get_waveforms(net, sta, loc, cha, day - PAD, day + 86400 + PAD)
            sid = sorted({tr.id for tr in st if tr.stats.channel.endswith("Z")})[0]
            st = st.select(id=sid)
            st.write(fn + ".part", format="MSEED"); os.replace(fn + ".part", fn); return "ok", sid, att + 1
        except Exception as e:
            err = str(e)
            if "No data" in err or "204" in err:
                open(fn, "wb").close(); return "nodata", None, att + 1
            if "429" in err or "Too Many" in err or "rate limit" in err:
                time.sleep(min(600, 60 * (att + 1))); continue
            TL.cl = None
            time.sleep(5 * (att + 1))
    return "failed", err[:200], 8


def job(net, role, nslc, day, man):
    key = f"{role}.{day.strftime('%Y%m%d')}"; fn = os.path.join(STAGE, net, key + ".mseed")
    if os.path.exists(fn):
        with LOCK: man["days"].setdefault(key, {"state": "nodata" if os.path.getsize(fn) == 0 else "ok", "bytes": os.path.getsize(fn), "from": "local"})
        return "skip"
    t0 = now(); state, info, att = fetch(nslc, UTCDateTime(str(day)), fn)
    rec = {"state": state, "attempts": att, "requested_utc": t0, "done_utc": now()}
    if state == "ok": rec.update(bytes=os.path.getsize(fn), sid=info)
    elif state == "nodata": rec["bytes"] = 0
    else: rec["error"] = info
    with LOCK:
        man["days"][key] = rec
        with open(os.path.join(MAN, f"{net}.requests.jsonl"), "a") as f: f.write(json.dumps({"key": key, **rec}) + "\n")
    return state


def gs(*a): return subprocess.run([GCLOUD, "storage", *a], capture_output=True, text=True)


def finish(net, man):
    d = os.path.join(STAGE, net)
    r = gs("rsync", d, f"{BUCKET}/{net}", "--no-clobber", "--exclude", r".*\.part$", "--quiet")
    man["bucket_sync_rc"] = r.returncode; man["bucket_sync_err"] = r.stderr[-400:] if r.returncode else ""
    remote = {}
    for line in gs("ls", "-l", f"{BUCKET}/{net}/").stdout.splitlines():
        p = line.split()
        if len(p) >= 3 and p[-1].startswith("gs://"): remote[p[-1].rsplit("/", 1)[-1]] = int(p[0])
    local = {f: os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".mseed")}
    man.update(bucket_objects=len(remote), local_files=len(local), bucket_bytes=sum(remote.values()), synced_utc=now(),
               bucket_size_mismatch=sorted(f for f in local if remote.get(f) != local[f]),
               failed=sorted(k for k, v in man["days"].items() if v["state"] == "failed"))
    fr = [v["requested_utc"] for v in man["days"].values() if v.get("requested_utc")]
    if fr: man["first_request_utc"] = min(fr)
    p = os.path.join(MAN, f"{net}.json"); json.dump(man, open(p, "w"), indent=1)
    gs("cp", p, f"{BUCKET}/_manifest/{net}.json", "--quiet")
    print(now(), "NETWORK", net, "files", len(local), "bucket", len(remote), "mismatch", len(man["bucket_size_mismatch"]),
          "failed", len(man["failed"]), "MB", round(man["bucket_bytes"] / 1e6, 1), flush=True)


def main(ids):
    a, b = (dt.date.fromisoformat(x) for x in CFG["period"])
    days = [a + dt.timedelta(days=i) for i in range((b - a).days)]
    for net, c in CFG["networks"].items():
        if ids and net not in ids: continue
        os.makedirs(os.path.join(STAGE, net), exist_ok=True)
        p = os.path.join(MAN, f"{net}.json")
        man = json.load(open(p)) if os.path.exists(p) else {"network": net, "datacentre": "EARTHSCOPE", "days": {}}
        for k, v in list(man["days"].items()):
            if v["state"] == "failed": del man["days"][k]          # requested again in this pass (no file was stored)
        man["roles"] = {r: ".".join(v[:4]) for r, v in c["stations"].items()}; man["period"] = CFG["period"]
        jobs = [(net, r, tuple(v[:4]), d, man) for d in days for r, v in c["stations"].items()]
        print(now(), net, "jobs", len(jobs), flush=True); n = 0
        with ThreadPoolExecutor(PAR) as ex:
            for f in as_completed([ex.submit(job, *j) for j in jobs]):
                n += 1
                if n % 200 == 0: print(now(), net, "done", n, "of", len(jobs), flush=True)
        finish(net, man)


if __name__ == "__main__":
    main(sys.argv[1:])
