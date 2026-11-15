"""PREREGISTRATION_TDH2023_PAPER1_2026-11-09.md sections 3-5, 9: compute (laptop, offline).
For each network: every local raw file is checked against its bucket object (size + MD5) -> runs/<NET>/bucket_verify.json; then the
four quarterly chunks run in parallel through pipeline/p10_tdh_wrapper.py with P10_OFFLINE=1 (no waveform request), the frozen
detector thresholds (P10_FIXED_THR) and, for AK, P10_STATIONS as pipeline/p10_runAK.sh. A failed chunk is run once more.
Usage: python analysis/tdh2023_p1/run.py [NET ...]"""
import os, sys, json, base64, hashlib, subprocess, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(root, "results", "tdh2023_p1", "networks_tdh2023_p1.json"), encoding="utf-8"))
STAGE = os.environ.get("TDH_STAGE", "C:/dev/p10tdh_p1_raw"); PY = os.environ.get("P10_PY", sys.executable)
GCLOUD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
OUT = os.path.join(root, "results", "tdh2023_p1", "runs"); CUTOFF = dt.datetime(2026, 11, 10, tzinfo=dt.timezone.utc)


def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def verify(net):
    r = subprocess.run([GCLOUD, "storage", "objects", "list", f"gs://p10-raw-waveforms/tdh2023_p1/{net}/*", "--format=json(name,size,md5_hash)"],
                       capture_output=True, text=True)
    remote = {o["name"].rsplit("/", 1)[-1]: o for o in json.loads(r.stdout or "[]")}
    d = os.path.join(STAGE, net); bad = []; n = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".mseed"): continue
        n += 1; b = open(os.path.join(d, f), "rb").read(); md5 = base64.b64encode(hashlib.md5(b).digest()).decode(); o = remote.get(f)
        if o is None or int(o.get("size", -1)) != len(b) or o.get("md5_hash") != md5: bad.append(f)
    res = {"network": net, "local_files": n, "bucket_objects": len(remote), "mismatch_or_missing_in_bucket": bad,
           "verified": not bad and n == len(remote), "checked_utc": now()}
    os.makedirs(os.path.join(OUT, net), exist_ok=True); json.dump(res, open(os.path.join(OUT, net, "bucket_verify.json"), "w"), indent=1)
    return res["verified"]


def chunk(net, t0, t1):
    c = CFG["networks"][net]; w = os.path.join(OUT, net, f"out_{t0}"); os.makedirs(w, exist_ok=True)
    env = {**os.environ, "P10_NO_PIP": "1", "P10_OFFLINE": "1", "P10_FIXED_THR": json.dumps(c["frozen_thresholds"]),
           "P10_T0": t0, "P10_TUNE_END": t0, "P10_EVAL_START": t0, "P10_T1": t1, "P10_OUT": w, "P10_CACHE": os.path.join(STAGE, net),
           "PYTHONIOENCODING": "utf-8"}
    if net != "IU_MAKZ": env["P10_STATIONS"] = json.dumps(c["stations"])
    att = []
    for k in range(2):
        if dt.datetime.now(dt.timezone.utc) >= CUTOFF: break
        s = time.time()
        with open(os.path.join(w, "run.log"), "w", encoding="utf-8") as log:
            rc = subprocess.run([PY, "-u", os.path.join(root, "pipeline", "p10_tdh_wrapper.py")], env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        ok = rc == 0 and os.path.exists(os.path.join(w, "episodes.csv"))
        att.append({"attempt": k + 1, "rc": rc, "seconds": round(time.time() - s), "end_utc": now(), "ok": ok})
        if ok: break
    json.dump({"network": net, "chunk": [t0, t1], "attempts": att, "ok": bool(att and att[-1]["ok"])}, open(os.path.join(w, "status.json"), "w"), indent=1)
    print(now(), net, t0, att[-1] if att else "cutoff", flush=True)
    return att and att[-1]["ok"]


def main(ids):
    ch = CFG["chunks"]; jobs = []
    for net in CFG["networks"]:
        if ids and net not in ids: continue
        if not verify(net): print(now(), net, "BUCKET VERIFY FAILED", flush=True); continue
        jobs += [(net, a, b) for a, b in zip(ch[:-1], ch[1:])]
    with ThreadPoolExecutor(8) as ex:
        fs = []
        for j in jobs: fs.append(ex.submit(chunk, *j)); time.sleep(30)   # stagger the catalogue queries
        print(now(), "results", [f.result() for f in fs], flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
