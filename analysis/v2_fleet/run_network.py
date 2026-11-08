"""Fleet runner of PREREGISTRATION_V2_NETWORKS_2026-11-08.md: one network, frozen pipeline, no parameter of its own.

Given a network id it reads that network's configuration (results/v2/networks.json, falling back to
results/v2/selection/chosen.json), then, exactly as pipeline/p10_runAK.sh did for the AK run:
  1. tuning week (the 7 days before the evaluation start) -> per-role 99.9th percentile thresholds (P10_FIXED_THR);
  2. evaluation period split into quarterly chunks run in parallel with the thresholds frozen.
Every run goes through pipeline/p10_v2_datacentre_wrapper.py, which checks the frozen pipeline sha256 and only redirects the
waveform client "EARTHSCOPE" to the network's data centre (P10_FDSN_BASE). Catalogue clients are untouched.

Roles: reference "MAKZ"; neighbours "S<site>_<member>" in the order of the configuration (S1_1 = seed of the nearest site),
which is the order the scorer (analysis/v2_networks.py) uses.

Restarts without changing the method: the pipeline caches each role-day waveform (P10_CACHE, kept OUTSIDE results/) and never
caches a failed download, so re-running a chunk resumes day by day. A chunk is re-run (max P10_MAX_ATTEMPTS) when its summary.json
is missing, or lists fetch_failures or catalog_failures; each attempt's run.log / summary.json is kept as *.attemptN.*, and a
catalogue-failure re-run is logged as a protocol deviation (prereg section 4). Nothing else differs between attempts.

Outputs: results/v2/runs/<NET>/{tune_<date>/, out_<chunkstart>/, status.json, fleet.log, DONE}
Usage:   python analysis/v2_fleet/run_network.py <NET> [--dry]      (env P10_PY = python with obspy; default sys.executable)
"""
import os, sys, json, re, math, time, socket, hashlib, subprocess, datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor
LOCK = threading.RLock()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WRAP = os.path.join(ROOT, "pipeline", "p10_v2_datacentre_wrapper.py")
PY = os.environ.get("P10_PY", sys.executable)
MAX_ATT = int(os.environ.get("P10_MAX_ATTEMPTS", "4"))
WINDOWS = {"W1": ("2023-07-08", "2024-07-08"), "W2": ("2024-01-08", "2025-01-08"), "W3": ("2024-07-08", "2025-07-09")}
EARTHSCOPE_HOSTS = ("service.iris.edu", "service.earthscope.org")


def now(): return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load_cfg(net):
    for f in [os.path.join(ROOT, "results", "v2", x) for x in ("networks.json", "networks_batchB.json", "networks_ext12.json", "networks_ext12B.json", os.path.join("selection", "chosen.json"))]:
        if not os.path.exists(f): continue
        d = json.load(open(f, encoding="utf-8"))
        items = d if isinstance(d, list) else d.get("networks", d.get("chosen", []))
        if isinstance(items, dict): items = [{"network": k, **v} for k, v in items.items()]
        for c in items:
            if c.get("network") == net or c.get("id") == net: return c, f
    sys.exit(f"network {net} not found in results/v2/networks.json or selection/chosen.json")


def split_stream(s):
    n, sta, loc, cha = s.split(".")
    return n, sta, loc, cha


def stations(cfg):
    ref = cfg.get("reference_stream") or f"{cfg['network']}.{cfg['reference']}.{cfg.get('loc', '')}.{cfg.get('cha', 'BHZ')}"
    st = {"MAKZ": [*split_stream(ref), float(cfg["lat"]), float(cfg["lon"])]}
    for i, s in enumerate(cfg["sites"]):
        for j, m in enumerate(s["members"]):
            st[f"S{i + 1}_{j + 1}"] = [*split_stream(m["stream"]), float(m["lat"]), float(m["lon"])]
    return st


def period(cfg):
    a = cfg.get("eval_start") or cfg.get("start"); b = cfg.get("eval_end") or cfg.get("end")
    if not (a and b): a, b = WINDOWS[cfg["window"]]
    a = dt.date.fromisoformat(str(a)[:10]); b = dt.date.fromisoformat(str(b)[:10])
    t = cfg.get("tune_start"); t = dt.date.fromisoformat(str(t)[:10]) if t else a - dt.timedelta(days=7)
    return t, a, b


def add_months(d, k):
    m = d.month - 1 + k; y = d.year + m // 12; m = m % 12 + 1
    return dt.date(y, m, min(d.day, 28 if m == 2 else 30 if m in (4, 6, 9, 11) else 31))


def chunks(a, b, months=3):
    out, c = [], a
    while c < b:
        n = min(add_months(c, months), b); out.append((c, n)); c = n
    return out


def fdsn_base(cfg):
    u = cfg.get("fdsn_base") or cfg.get("dataselect") or ""
    m = re.match(r"(https?://[^/]+)", u)
    if not m or any(h in m.group(1) for h in EARTHSCOPE_HOSTS): return ""
    return m.group(1)


class Net:
    def __init__(self, net):
        self.net = net; self.cfg, self.cfg_file = load_cfg(net)
        _id = self.cfg.get("id", "")
        self.ext = _id.endswith("_EXT12") or _id.endswith("_EXT12B")   # ext12 / ext12B: frozen thresholds of runs/<NET>, own output tree
        code = self.cfg["network"]
        self.dir = os.path.join(ROOT, "results", "v2", "runs_ext12B" if _id.endswith("_EXT12B") else "runs_ext12" if self.ext else "runs", code); os.makedirs(self.dir, exist_ok=True)
        self.cache = os.environ.get("P10_CACHE_ROOT", os.path.join(os.path.expanduser("~"), "p10v2cache")) + "/" + net
        os.makedirs(self.cache, exist_ok=True)
        self.st = stations(self.cfg); self.tune, self.a, self.b = period(self.cfg)
        self.base = fdsn_base(self.cfg)
        self.status = {"network": net, "config_file": os.path.relpath(self.cfg_file, ROOT), "host": socket.gethostname(),
                       "platform": os.environ.get("P10_PLATFORM", socket.gethostname()), "fdsn_base": self.base or "EARTHSCOPE",
                       "stations": self.st, "tune": [str(self.tune), str(self.a)], "eval": [str(self.a), str(self.b)],
                       "chunks": {}, "deviations": [], "started_utc": now(), "state": "running"}

    def log(self, msg):
        line = f"{now()} {self.net} {msg}"
        with LOCK: print(line, flush=True); open(os.path.join(self.dir, "fleet.log"), "a", encoding="utf-8").write(line + "\n")

    def save(self):
        with LOCK:
            txt = json.dumps(self.status, indent=1, default=str)
        open(os.path.join(self.dir, "status.json"), "w").write(txt)

    def env(self, t0, tune_end, ev, t1, out, thr=None):
        e = dict(os.environ, P10_NO_PIP=os.environ.get("P10_NO_PIP", "1"), P10_FETCH_PAUSE=os.environ.get("P10_FETCH_PAUSE", "2"),
                 P10_STATIONS=json.dumps(self.st), P10_REF="MAKZ", P10_T0=str(t0), P10_TUNE_END=str(tune_end),
                 P10_EVAL_START=str(ev), P10_T1=str(t1), P10_OUT=out, P10_CACHE=self.cache, P10_FDSN_BASE=self.base)
        e.pop("P10_FIXED_THR", None)
        if thr: e["P10_FIXED_THR"] = json.dumps(thr)
        return e

    def run_once(self, name, env):
        out = env["P10_OUT"]; os.makedirs(out, exist_ok=True)
        t = time.time()
        with open(os.path.join(out, "run.log"), "w", encoding="utf-8") as f:
            rc = subprocess.run([PY, WRAP], env=env, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT).returncode
        sp = os.path.join(out, "summary.json")
        s = json.load(open(sp)) if os.path.exists(sp) else None
        return rc, s, round(time.time() - t)

    def run_chunk(self, name, env):
        out = env["P10_OUT"]
        with LOCK: rec = self.status["chunks"].setdefault(name, {"attempts": []})
        if os.path.exists(os.path.join(out, "summary.json")) and rec.get("ok"): return True
        for att in range(1, MAX_ATT + 1):
            rc, s, sec = self.run_once(name, env)
            info = {"attempt": att, "rc": rc, "seconds": sec, "end_utc": now(),
                    "summary": bool(s), "fetch_failures": len(s["fetch_failures"]) if s else None,
                    "catalog_failures": s["catalog_failures"] if s else None}
            rec["attempts"].append(info)
            for fn in ("run.log", "summary.json"):
                p = os.path.join(out, fn)
                if os.path.exists(p):
                    b, x = os.path.splitext(fn); open(os.path.join(out, f"{b}.attempt{att}{x}"), "wb").write(open(p, "rb").read())
            self.log(f"{name} attempt {att}: rc={rc} {sec}s summary={bool(s)} fetch_fail={info['fetch_failures']} cat_fail={info['catalog_failures']}")
            ok = bool(s) and not s["fetch_failures"] and not s["catalog_failures"]
            if s and s["catalog_failures"]:
                self.status["deviations"].append(f"{name}: catalogue failure on attempt {att} -> chunk reprocessed (prereg s.4)")
            if ok:
                rec["ok"] = True; self.save(); return True
            self.save(); time.sleep(30 * att)
        rec["ok"] = False; rec["final"] = "summary missing" if not s else ("catalogue failure" if s["catalog_failures"] else "fetch failures")
        if s and not s["catalog_failures"]: rec["usable_with_fetch_failures"] = True   # days not fetched stay unprocessed, reported
        self.save(); return False

    def run_tune(self, env, out):
        """Tuning week: the pipeline prints the per-role thresholds before it touches the one evaluation day and the catalogue.
        Only the thresholds are used (as in p10_runAK.sh), so the process is stopped once that line is written: a quiet region
        whose one-day catalogue is empty (USGS 204, retried by the frozen pipeline for ~36 min) must not hold the network."""
        os.makedirs(out, exist_ok=True)
        for att in range(1, MAX_ATT + 1):
            t = time.time(); log = os.path.join(out, "run.log")
            with open(log, "w", encoding="utf-8") as f:
                pr = subprocess.Popen([PY, WRAP], env=env, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)
                while pr.poll() is None:
                    time.sleep(5)
                    if self.thresholds(out) is not None:
                        time.sleep(2); pr.terminate()
                        try: pr.wait(30)
                        except Exception: pr.kill()
                        break
            thr = self.thresholds(out)
            ev = self.tune_evidence(thr) if thr else {}
            if thr and any(v["fetch_failed_days"] for v in ev.values()):
                self.log(f"tune attempt {att}: NaN role(s) with download failures (not 'no data'): {ev} -> retry")
                self.status.setdefault("tune_evidence_attempts", []).append(ev); thr = None
            elif ev: self.status["tune_nan_evidence"] = ev
            with LOCK: self.status["chunks"].setdefault("tune", {"attempts": []})["attempts"].append(
                {"attempt": att, "rc": pr.returncode, "seconds": round(time.time() - t), "end_utc": now(), "thresholds_line": thr is not None,
                 "stopped_after_thresholds": thr is not None})
            open(os.path.join(out, f"run.attempt{att}.log"), "wb").write(open(log, "rb").read())
            self.log(f"tune attempt {att}: rc={pr.returncode} {round(time.time() - t)}s thresholds={'yes' if thr else 'no'}")
            self.save()
            if thr is not None: return True
            time.sleep(30 * att)
        return False

    def tune_evidence(self, thr):
        """For each role with a NaN threshold: per tuning day, was the waveform file cached EMPTY (the data centre answered
        'no data', HTTP 204/404) or MISSING (download failed, transient: the tuning run is retried)?"""
        ev = {}
        for k, v in thr.items():
            if math.isfinite(v): continue
            empty, failed, data = [], [], []
            d = self.tune
            while d < self.a:
                fn = os.path.join(self.cache, f"{k}.{d.strftime('%Y%m%d')}.mseed")
                (failed if not os.path.exists(fn) else empty if os.path.getsize(fn) == 0 else data).append(str(d)); d += dt.timedelta(days=1)
            ev[k] = {"stream": ".".join(self.st[k][:4]), "no_data_days": empty, "fetch_failed_days": failed, "data_days": data}
        return ev

    def thresholds(self, out):
        line = [l for l in open(os.path.join(out, "run.log"), encoding="utf-8", errors="replace").read().splitlines() if l.startswith("thresholds")]
        if not line: return None
        d = {k: float(v) for k, v in re.findall(r"'(\w+)': (?:np\.float64\()?(nan|-?inf|-?[\d.]+(?:e[-+]?\d+)?)", line[-1])}
        return d if set(d) == set(self.st) else None

    def run(self, dry=False):
        ch = chunks(self.a, self.b, int(os.environ.get("P10_CHUNK_MONTHS", "3")))
        self.status["chunk_plan"] = [[str(x), str(y)] for x, y in ch]
        self.log(f"plan base={self.base or 'EARTHSCOPE'} tune {self.tune}..{self.a} eval {self.a}..{self.b} chunks={len(ch)} roles={list(self.st)}")
        self.save()
        if dry: return
        if self.ext:   # PREREGISTRATION_V2_EXT12: no re-tuning; thresholds = batch-A status.json of the same network
            sa = os.path.join(ROOT, "results", "v2", "runs", self.cfg["network"], "status.json")
            thr = json.load(open(sa)).get("thresholds") if os.path.exists(sa) else None
            if not thr or set(thr) != set(self.st) or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in thr.values()):
                self.status.update({"thresholds": thr, "state": "not_run_no_batchA_thresholds", "batchA_status": sa}); self.save()
                self.log(f"EXT12 NOT RUN: no finite batch-A thresholds ({sa})"); return
            self.status.update({"thresholds": thr, "thresholds_source": os.path.relpath(sa, ROOT), "tune": "none (frozen batch-A)"})
            self.log(f"EXT12 frozen batch-A thresholds {thr}"); self.save()
            return self.run_eval(ch, thr)
        tdir = os.path.join(self.dir, f"tune_{self.tune}")
        okt = self.run_tune(self.env(self.tune, self.a, self.a, self.a + dt.timedelta(days=1), tdir), tdir)
        thr = self.thresholds(tdir)
        if not okt or not thr or not all(math.isfinite(v) for v in thr.values()):
            self.status["thresholds"] = thr; self.status["state"] = "tuning_failed"; self.save()
            self.log(f"TUNING FAILED thr={thr}"); return
        self.status["thresholds"] = thr; self.log(f"thresholds {thr}"); self.save()
        self.run_eval(ch, thr)

    def run_eval(self, ch, thr):
        par = int(os.environ.get("P10_CHUNK_PAR", str(len(ch))))
        def go(i_c):
            i, (x, y) = i_c; time.sleep(60 * (i % par))                    # stagger as in the AK run
            return self.run_chunk(f"out_{x}", self.env(x, x, x, y, os.path.join(self.dir, f"out_{x}"), thr))
        with ThreadPoolExecutor(par) as ex: res = list(ex.map(go, enumerate(ch)))
        self.status["finished_utc"] = now()
        self.status["state"] = "done" if all(res) else "incomplete"
        self.save()
        if all(res): open(os.path.join(self.dir, "DONE"), "w").write(now() + "\n")
        self.log(f"FINISHED state={self.status['state']}")


if __name__ == "__main__":
    n = Net(sys.argv[1]); n.run(dry="--dry" in sys.argv)
