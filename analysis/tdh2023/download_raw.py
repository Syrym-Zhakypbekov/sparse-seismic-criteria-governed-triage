"""PLAN_TIME_DISJOINT_2023_2026-11-08.md section 5: download every role-day ONCE and store it in the bucket.

For each network of results/tdh2023/networks_tdh2023.json (or the ids given) and each role (reference + neighbour members, in the
order of analysis/v2_fleet/run_network.stations) and each day of the period (tuning week of a candidate + 2023-06-01 .. 08-29),
the request is the pipeline's own (pipeline/extended_stalta_criteria.py fetch, copied): Client(<data centre> or "EARTHSCOPE")
.get_waveforms(net, sta, loc, cha, day - 1800 s, day + 86400 s + 1800 s); first vertical channel id in sorted order; MiniSEED.
"No data"/204 -> empty file (true absence); 429 -> back-off, never stored as absent; other errors: 8 attempts, then "failed" (no
file; a later pass retries it). Files: <STAGE>/<NET>/<ROLE>.<YYYYMMDD>.mseed (the pipeline's cache naming). Concurrency is limited
per data centre. When a network has no job left, its directory is synced to gs://p10-raw-waveforms/tdh2023/<NET>/ and the object
sizes are read back; the manifest goes to results/tdh2023/download/<NET>.json and gs://p10-raw-waveforms/tdh2023/_manifest/<NET>.json.
Nothing is ever deleted from the bucket.
Usage: python analysis/tdh2023/download_raw.py [NET ...]     env: TDH_STAGE (default p10tdh_raw), GCLOUD (gcloud binary)
"""
import os, sys, json, time, threading, subprocess, datetime as dt, importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("rn", os.path.join(root, "analysis", "v2_fleet", "run_network.py"))
rn = importlib.util.module_from_spec(spec); spec.loader.exec_module(rn)
STAGE = os.environ.get("TDH_STAGE", "p10tdh_raw")
GCLOUD = os.environ.get("GCLOUD", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd"))
BUCKET = "gs://p10-raw-waveforms/tdh2023"
MAN = os.path.join(root, "results", "tdh2023", "download"); os.makedirs(MAN, exist_ok=True)
PAD = 1800.0
PAUSE = float(os.environ.get("TDH_PAUSE", "1"))
LIMIT = {"EARTHSCOPE": int(os.environ.get("TDH_ES", "6"))}
LOCK = threading.Lock(); SEM = {}; TL = threading.local()


def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cfgs(ids):
    d = json.load(open(os.path.join(root, "results", "tdh2023", "networks_tdh2023.json"), encoding="utf-8"))["networks"]
    return [c for c in d if not ids or c["network"] in ids]


def days(c):
    a = dt.date.fromisoformat(c["eval_start"]); b = dt.date.fromisoformat(c["eval_end"])
    t = dt.date.fromisoformat(c["tune_start"]) if c.get("tune_start") else a
    out = []; d = t
    while d < b: out.append(d); d += dt.timedelta(days=1)
    return out


def client(base):
    k = base or "EARTHSCOPE"
    cl = getattr(TL, "cl", None)
    if cl is None: cl = TL.cl = {}
    if k not in cl: cl[k] = Client(k)
    return cl[k]


def fetch(base, nslc, day, fn):
    """the pipeline's fetch(), copied; returns (state, sid or error, attempts)"""
    net, sta, loc, cha = nslc; err = ""
    for att in range(8):
        try:
            time.sleep(PAUSE)
            st = client(base).get_waveforms(net, sta, loc, cha, day - PAD, day + 86400 + PAD)
            sid = sorted({tr.id for tr in st if tr.stats.channel.endswith("Z")})[0]
            st = st.select(id=sid)
            st.write(fn + ".part", format="MSEED"); os.replace(fn + ".part", fn); return "ok", sid, att + 1
        except Exception as e:
            err = str(e)
            if "No data" in err or "204" in err:
                open(fn, "wb").close(); return "nodata", None, att + 1
            if "429" in err or "Too Many" in err or "rate limit" in err:
                time.sleep(min(600, 60 * (att + 1))); continue
            time.sleep(5 * (att + 1))
    return "failed", err[:200], 8


def job(net, base, role, nslc, day, man):
    fn = os.path.join(STAGE, net, f"{role}.{day.strftime('%Y%m%d')}.mseed")
    key = f"{role}.{day.strftime('%Y%m%d')}"
    if os.path.exists(fn):
        with LOCK: man["days"].setdefault(key, {"state": "nodata" if os.path.getsize(fn) == 0 else "ok", "bytes": os.path.getsize(fn), "from": "local"})
        return key, "skip"
    dc = base or "EARTHSCOPE"
    with SEM[dc]:
        t0 = now(); state, info, att = fetch(base, nslc, UTCDateTime(str(day)), fn)
    rec = {"state": state, "attempts": att, "requested_utc": t0, "done_utc": now()}
    if state == "ok": rec.update(bytes=os.path.getsize(fn), sid=info)
    elif state == "nodata": rec["bytes"] = 0
    else: rec["error"] = info
    with LOCK:
        man["days"][key] = rec
        if not man.get("first_request_utc") or t0 < man["first_request_utc"]: man["first_request_utc"] = t0
    return key, state


def gs(*args):
    return subprocess.run([GCLOUD, "storage", *args], capture_output=True, text=True)


def finish(net, man):
    """sync to the bucket, read sizes back, write the manifest locally and to the bucket"""
    d = os.path.join(STAGE, net)
    r = gs("rsync", d, f"{BUCKET}/{net}", "--no-clobber", "--exclude", r".*\.part$", "--quiet")
    man["bucket_sync_rc"] = r.returncode; man["bucket_sync_err"] = r.stderr[-400:] if r.returncode else ""
    ls = gs("ls", "-l", f"{BUCKET}/{net}/")
    remote = {}
    for line in ls.stdout.splitlines():
        p = line.split()
        if len(p) >= 3 and p[-1].startswith("gs://"): remote[p[-1].rsplit("/", 1)[-1]] = int(p[0])
    local = {f: os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".mseed")}
    man["bucket_objects"] = len(remote); man["local_files"] = len(local)
    man["bucket_size_mismatch"] = sorted(f for f in local if remote.get(f) != local[f])
    man["bucket_bytes"] = sum(remote.values()); man["synced_utc"] = now()
    p = os.path.join(MAN, f"{net}.json"); json.dump(man, open(p, "w"), indent=1)
    gs("cp", p, f"{BUCKET}/_manifest/{net}.json", "--quiet")
    return man


def main(ids):
    C = cfgs(ids); mans = {}; jobs = []
    for c in C:
        net = c["network"]; os.makedirs(os.path.join(STAGE, net), exist_ok=True)
        base = rn.fdsn_base(c); dc = base or "EARTHSCOPE"
        SEM.setdefault(dc, threading.Semaphore(LIMIT.get(dc, int(os.environ.get("TDH_OTHER", "3")))))
        st = rn.stations(c)
        old = os.path.join(MAN, f"{net}.json")
        man = json.load(open(old)) if os.path.exists(old) else {"network": net, "datacentre": dc, "days": {}}
        man["roles"] = {k: ".".join(v[:4]) for k, v in st.items()}; man["period"] = [str(days(c)[0]), c["eval_end"]]
        mans[net] = man
        for d in days(c):
            for role, v in st.items(): jobs.append((net, base, role, tuple(v[:4]), d, man))
    left = {}
    for j in jobs: left[j[0]] = left.get(j[0], 0) + 1
    print(now(), "jobs", len(jobs), "networks", len(mans), flush=True)
    # one pool per data centre (its own concurrency), network-major inside a data centre: networks finish one after another
    by_dc = {}
    for j in jobs: by_dc.setdefault(j[1] or "EARTHSCOPE", []).append(j)
    cnt = {"done": 0}

    def run_dc(dc, js):
        js = sorted(js, key=lambda j: (j[0], j[4], j[2]))
        with ThreadPoolExecutor(LIMIT.get(dc, int(os.environ.get("TDH_OTHER", "3")))) as ex:
            futs = {ex.submit(job, *j): j[0] for j in js}
            for f in as_completed(futs):
                net = futs[f]; key, state = f.result()
                with LOCK:
                    cnt["done"] += 1; left[net] -= 1; last = left[net] == 0; dn = cnt["done"]
                if dn % 200 == 0: print(now(), "done", dn, "of", len(jobs), flush=True)
                if last:
                    m = finish(net, mans[net]); n_f = sum(1 for v in m["days"].values() if v["state"] == "failed")
                    print(now(), "NETWORK", net, "files", m["local_files"], "bucket", m["bucket_objects"], "mismatch",
                          len(m["bucket_size_mismatch"]), "failed", n_f, "MB", round(m["bucket_bytes"] / 1e6, 1), flush=True)

    with ThreadPoolExecutor(len(by_dc)) as top:
        list(top.map(lambda kv: run_dc(*kv), by_dc.items()))


if __name__ == "__main__":
    main(sys.argv[1:])
