"""Rescue runner of PREREGISTRATION_V2_RESCUE_2026-11-08.md (post hoc extension of the rule-v2 multi-network test).

Uses the frozen fleet runner (run_network.Net) unchanged except for three run-list settings fixed in the rescue plan:
  1. tuning window: the FIRST 7-day window [t, t+7 d), t = 2024-01-01 .. 2024-03-25 in steps of one day, in which EVERY role
     has data on >= 5 of the 7 days ("data on a day" = FDSN availability extents of that stream cover >= 12 h of the day; if the
     data centre has no availability service, a 5-min dataselect probe at 00:00 and at 12:00 UTC: data if either returns samples).
     If the pipeline still gives a non-finite threshold for that window, the next qualifying window is tried, at most 3 windows.
     No qualifying window -> the network stays excluded ("rescue_failed_no_window").
  2. evaluation period: [max(2024-01-08, t + 7 d), 2024-07-08), thresholds frozen from the tuning window.
  3. output: results/v2/runs_rescue/<NET>/ (never results/v2/runs/).
CZ only: env P10_RATE_FIX=1 (pipeline/p10_v2_rescue_wrapper.py resamples traces whose sampling rate differs from the nominal by
< 0.01 % before the pipeline's merge). SC: rerun unchanged (tuning 2024-01-01..2024-01-08, the batch-B setting).
Usage: python analysis/v2_fleet/run_rescue.py <NET> [--dry]
"""
import os, sys, json, math, time, datetime as dt, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_network as rn

ROOT = rn.ROOT
RESCUE_WRAP = os.path.join(ROOT, "pipeline", "p10_v2_rescue_wrapper.py")
EVAL_START, EVAL_END, SEARCH_FIRST, SEARCH_LAST = dt.date(2024, 1, 8), dt.date(2024, 7, 8), dt.date(2024, 1, 1), dt.date(2024, 3, 25)
UNCHANGED = {"SC"}                       # rerun with the batch-B setting
RATE_FIX = {"CZ"}
AVAIL_EARTHSCOPE = "https://service.earthscope.org/fdsnws/availability/1/query"


def http(url, timeout=120, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "p10-research"}), timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (204, 404): return e.code, b""
            time.sleep(5 * (k + 1))
        except Exception:
            time.sleep(5 * (k + 1))
    return None, b""


def avail_days(base, stream, t0, t1):
    """{date: covered_seconds} from the FDSN availability service, or None if the service is not usable."""
    n, s, l, c = stream.split(".")
    url = (AVAIL_EARTHSCOPE if not base else base.rstrip("/") + "/fdsnws/availability/1/query")
    url += f"?net={n}&sta={s}&loc={l or '--'}&cha={c}&start={t0}T00:00:00&end={t1}T00:00:00&format=text&merge=quality,samplerate"
    st, b = http(url)
    if st is None or st not in (200, 204): return None          # 404 = no usable availability service -> dataselect probe
    cov = {}
    for line in b.decode("utf-8", "replace").splitlines():
        if not line.strip() or line.startswith("#"): continue
        p = line.split()
        try:
            a = dt.datetime.fromisoformat(p[-2].rstrip("Z")); z = dt.datetime.fromisoformat(p[-1].rstrip("Z"))
        except Exception:
            continue
        while a < z:
            d = a.date(); e = min(z, dt.datetime.combine(d + dt.timedelta(days=1), dt.time()))
            cov[d] = cov.get(d, 0) + (e - a).total_seconds(); a = e
    return cov


def probe_day(base, stream, d):
    n, s, l, c = stream.split(".")
    root = (base.rstrip("/") if base else "https://service.earthscope.org")
    for hh in ("00", "12"):
        url = f"{root}/fdsnws/dataselect/1/query?net={n}&sta={s}&loc={l or '--'}&cha={c}&start={d}T{hh}:00:00&end={d}T{hh}:05:00"
        st, b = http(url, timeout=60, tries=2)
        if st == 200 and len(b) > 0: return True
    return False


def day_table(base, streams):
    t0, t1 = SEARCH_FIRST, SEARCH_LAST + dt.timedelta(days=7)
    out, method = {}, {}
    for role, stream in streams.items():
        cov = avail_days(base, stream, t0, t1)
        if cov is not None:
            out[role] = {str(t0 + dt.timedelta(days=i)): cov.get(t0 + dt.timedelta(days=i), 0) >= 43200 for i in range((t1 - t0).days)}
            method[role] = "availability"
        else:
            from concurrent.futures import ThreadPoolExecutor
            days = [t0 + dt.timedelta(days=i) for i in range((t1 - t0).days)]
            with ThreadPoolExecutor(8) as ex: got = list(ex.map(lambda d: probe_day(base, stream, d), days))
            out[role] = {str(d): g for d, g in zip(days, got)}
            method[role] = "dataselect_probe"
    return out, method


def qualifying_windows(tab):
    w, t = [], SEARCH_FIRST
    while t <= SEARCH_LAST:
        days = [str(t + dt.timedelta(days=i)) for i in range(7)]
        if all(sum(tab[r][d] for d in days) >= 5 for r in tab): w.append(t)
        t += dt.timedelta(days=1)
    return w


class Rescue(rn.Net):
    def __init__(self, net):
        super().__init__(net)
        code = self.cfg["network"]
        self.dir = os.path.join(ROOT, "results", "v2", "runs_rescue", code); os.makedirs(self.dir, exist_ok=True)
        self.status.update({"rescue_plan": "PREREGISTRATION_V2_RESCUE_2026-11-08.md", "rate_fix": net in RATE_FIX})

    def env(self, *a, **k):
        e = super().env(*a, **k)
        if self.net in RATE_FIX: e["P10_RATE_FIX"] = "1"
        return e


def main():
    net = sys.argv[1]; dry = "--dry" in sys.argv
    r = Rescue(net)
    rn.WRAP = RESCUE_WRAP                                   # rate fix active only when P10_RATE_FIX=1
    streams = {k: ".".join(v[:4]) for k, v in r.st.items()}
    if net in UNCHANGED:
        cands = [SEARCH_FIRST]; r.status["rescue_window_rule"] = "unchanged (batch-B tuning week)"
    else:
        tab, meth = day_table(r.base, streams)
        cands = qualifying_windows(tab)
        r.status["rescue_day_table"] = {k: [d for d, ok in v.items() if ok] for k, v in tab.items()}
        r.status["rescue_day_method"] = meth; r.status["rescue_qualifying_windows"] = [str(c) for c in cands]
    r.log(f"rescue candidates {[str(c) for c in cands[:3]]}"); r.save()
    if not cands:
        r.status["state"] = "rescue_failed_no_window"; r.save(); r.log("RESCUE: no qualifying tuning window"); return
    if dry: return
    for k, t in enumerate(cands[:3]):
        r.tune = t; r.a = max(EVAL_START, t + dt.timedelta(days=7)); r.b = EVAL_END
        r.status.update({"tune": [str(r.tune), str(r.a)], "eval": [str(r.a), str(r.b)], "rescue_window_try": k + 1})
        tdir = os.path.join(r.dir, f"tune_{r.tune}")
        okt = r.run_tune(r.env(r.tune, r.a, r.a, r.a + dt.timedelta(days=1), tdir), tdir)
        thr = r.thresholds(tdir)
        if okt and thr and all(math.isfinite(v) for v in thr.values()):
            r.status["thresholds"] = thr; r.log(f"rescue thresholds {thr} (window {r.tune})"); r.save()
            ch = rn.chunks(r.a, r.b, int(os.environ.get("P10_CHUNK_MONTHS", "3")))
            r.status["chunk_plan"] = [[str(x), str(y)] for x, y in ch]; r.save()
            return r.run_eval(ch, thr)
        r.log(f"rescue window {r.tune}: non-finite thresholds {thr}")
    r.status["state"] = "rescue_failed_thresholds"; r.save()


if __name__ == "__main__":
    main()
