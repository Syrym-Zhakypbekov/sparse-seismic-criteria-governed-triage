"""Permanent raw-waveform archive of the 54 selected networks (authors' decision 08.11.2026): every role stream of every network of
results/v2/networks.json (batch A) and networks_batchB.json (batch B, incl. the rescue networks), every day 2024-01-01 .. 2025-01-07,
stored once in gs://p10-raw-waveforms/<NET>/<STA>.<LOC>.<CHA>/<YYYY-MM-DD>.mseed (the channel is kept in the path because a few
networks use two streams of one station name). Nothing is downloaded twice:
  1. local raw files already on this VM (~/p10raw/<ID>/<ROLE>.<YYYYMMDD>.mseed, hard-linked from the pipeline cache) are uploaded;
  2. the bucket listing of the network is read once;
  3. only missing (stream, day) pairs are requested from the network's own data centre (FDSN dataselect of the run config),
     with resume (objects already in the bucket are skipped on a rerun) and backoff on HTTP 429/503;
  4. a day the data centre answers 204/404 is recorded as "nodata" in the manifest (not retried on a rerun).
A local file is removed only after `gsutil ls -l` confirms the same byte size in the bucket.
Manifest per network: gs://p10-raw-waveforms/_manifest/<NET>.json (stream -> day -> bytes | "nodata").
authors' decision 08.11.2026: UPLOAD-ONLY by default (ARCHIVE_UPLOAD_ONLY=1): only raw files already on the VM are stored; nothing is
re-downloaded just to archive it. Set ARCHIVE_UPLOAD_ONLY=0 to fill missing days (not used).
Not part of any pre-registered analysis; it changes no code path of the pipeline or the scorer.
  python analysis/v2_fleet/archive_raw.py NET [NET ...]        (on a VM with storage read-write scope)
  python analysis/v2_fleet/archive_raw.py --plan               (laptop: streams x days per network, no network calls)
"""
import os, sys, json, glob, time, subprocess, datetime as dt, urllib.request, urllib.error, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUCKET = "gs://p10-raw-waveforms"
D0, D1 = dt.date(2024, 1, 1), dt.date(2025, 1, 8)
EARTHSCOPE = "https://service.earthscope.org/fdsnws/dataselect/1"
RAW = os.path.expanduser("~/p10raw")


def configs():
    out = {}
    for f in ("networks.json", "networks_batchB.json"):
        for c in json.load(open(os.path.join(ROOT, "results", "v2", f), encoding="utf-8"))["networks"]:
            out[c["network"]] = c
    return out


def streams(c):
    """role -> (net, sta, loc, cha), same role order as analysis/v2_fleet/run_network.stations()."""
    def sp(s): n, s_, l, ch = s.split("."); return n, s_, l, ch
    st = {"MAKZ": sp(c["reference_stream"])}
    for i, s in enumerate(c["sites"]):
        for j, m in enumerate(s["members"]):
            st[f"S{i + 1}_{j + 1}"] = sp(m["stream"])
    return st


def dataselect(c):
    u = c.get("dataselect") or EARTHSCOPE
    return u.rstrip("/") + "/query"


def days():
    d = D0
    while d < D1:
        yield d; d += dt.timedelta(days=1)


def gs(*args, check=True):
    r = subprocess.run(["gsutil", *args], capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(r.stderr[-400:])
    return r


def obj(net, s, d): return f"{BUCKET}/{net}/{s[1]}.{s[2]}.{s[3]}/{d.isoformat()}.mseed"


def listing(net):
    r = gs("ls", "-l", f"{BUCKET}/{net}/**", check=False)
    have = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) >= 3 and p[2].startswith("gs://"): have[p[2]] = int(p[0])
    return have


def fetch(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "p10-archive"}), timeout=600) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (204, 404): return e.code, b""
            time.sleep(min(600, 15 * 2 ** k))
        except Exception:
            time.sleep(min(600, 15 * 2 ** k))
    return -1, b""


def put(local, dst, size):
    gs("-q", "cp", local, dst)
    r = gs("ls", "-l", dst, check=False)
    return r.returncode == 0 and r.stdout.split() and int(r.stdout.split()[0]) == size


def archive(net, cfgs):
    c = cfgs[net]; st = streams(c); url = dataselect(c)
    man_obj = f"{BUCKET}/_manifest/{net}.json"
    r = gs("cat", man_obj, check=False); man = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    have = listing(net)
    # 1. local raw files of any run id of this network (NET, NET_EXT12, NET_EXT12B, rescue ids)
    up = 0
    for f in glob.glob(os.path.join(RAW, f"{net}*", "*.mseed")):
        role, ymd = os.path.basename(f).split(".")[:2]
        if role not in st: continue
        d = dt.date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
        if not (D0 <= d < D1): continue
        dst = obj(net, st[role], d); size = os.path.getsize(f)
        if size == 0 or dst in have: continue
        if put(f, dst, size): have[dst] = size; up += 1
    # 2. missing (stream, day) pairs from the network's data centre
    todo = [] if os.environ.get("ARCHIVE_UPLOAD_ONLY", "1") == "1" else         [(role, s, d) for role, s in st.items() for d in days()
         if obj(net, s, d) not in have and man.get(".".join(s), {}).get(d.isoformat()) != "nodata"]

    def one(job):
        role, s, d = job
        q = f"{url}?net={s[0]}&sta={s[1]}&loc={s[2] or '--'}&cha={s[3]}&start={d}T00:00:00&end={d + dt.timedelta(days=1)}T00:00:00"
        code, b = fetch(q)
        if code in (204, 404) or (code == 200 and not b): return s, d, "nodata"
        if code != 200: return s, d, None
        fd, tmp = tempfile.mkstemp(suffix=".mseed"); os.write(fd, b); os.close(fd)
        ok = put(tmp, obj(net, s, d), len(b)); os.remove(tmp)
        return s, d, len(b) if ok else None

    got = nodata = failed = 0
    with ThreadPoolExecutor(int(os.environ.get("ARCHIVE_THREADS", "4"))) as ex:
        for s, d, res in ex.map(one, todo):
            k = ".".join(s)
            if res == "nodata": man.setdefault(k, {})[d.isoformat()] = "nodata"; nodata += 1
            elif res is None: failed += 1
            else: man.setdefault(k, {})[d.isoformat()] = res; got += 1
    for o, size in have.items():   # record what the bucket already holds
        p = o[len(BUCKET) + 1:].split("/")
        if len(p) == 3: man.setdefault(p[1], {}).setdefault(p[2].replace(".mseed", ""), size)
    fd, tmp = tempfile.mkstemp(suffix=".json"); os.write(fd, json.dumps(man).encode()); os.close(fd)
    gs("-q", "cp", tmp, man_obj); os.remove(tmp)
    # 3. local raw copies removed only when the bucket size matches
    removed = 0
    have = listing(net)
    for f in glob.glob(os.path.join(RAW, f"{net}*", "*.mseed")):
        role, ymd = os.path.basename(f).split(".")[:2]
        if role not in st: continue
        d = dt.date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
        if have.get(obj(net, st[role], d)) == os.path.getsize(f): os.remove(f); removed += 1
    total = sum(have.values())
    print(json.dumps({"network": net, "uploaded_local": up, "downloaded": got, "nodata_days": nodata, "failed": failed,
                      "objects": len(have), "bytes": total, "local_removed_after_check": removed, "end_utc": dt.datetime.utcnow().isoformat()}), flush=True)


if __name__ == "__main__":
    cf = configs()
    if sys.argv[1:] == ["--plan"]:
        n = sum(len(streams(c)) for c in cf.values()) * sum(1 for _ in days())
        print(len(cf), "networks,", sum(len(streams(c)) for c in cf.values()), "streams,", n, "stream-days")
        sys.exit(0)
    for net in sys.argv[1:]: archive(net, cf)
