"""PLAN_TIME_DISJOINT_2023_2026-11-08.md section 3: the frozen selection rule (SELECTION_RULE_V2_2026-11-08.md sections 3-6)
applied to the candidates A2, CA, OT for the 2023 window. METADATA ONLY (station epochs and coordinates, daily availability,
restriction status); never requests events, waveforms or detections.

Functions get, ts, km, covers, window_streams, geometry, the availability parser, restricted, channel_closed and the pass/rank
logic are copied from analysis/v2_select_networks.py. The only changes, as the plan states: one window T23 (tuning week
2023-05-25 .. 06-01, 90 evaluation days 2023-06-01 .. 08-30) and the availability proportions computed on 90 days (reference share
>= 0.90 on >= 90 % of days, a site with >= 3 days < 0.10, every neighbour > 0 on >= 45 days). Each candidate is read from the data
centre the frozen rule chose for it (results/v2/selection/candidates.json).
Output: results/tdh2023/candidates_2023.json (+ raw responses, gzipped, in results/tdh2023/selection_raw/).
"""
import os, io, re, csv, json, gzip, math, time, datetime, urllib.request, urllib.parse, urllib.error

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(root, "results", "tdh2023"); RAW = os.path.join(OUT, "selection_raw"); os.makedirs(RAW, exist_ok=True)
WINDOWS = {"T23": ("2023-05-25", "2023-06-01", "2023-08-30")}
SPAN = ("2023-05-25", "2023-08-30")
NEVAL = 90
D_MERGE, R_MIN, R_MAX, THIRD_MIN = 50.0, 20.0, 700.0, 100.0
UA = {"User-Agent": "p10-tdh2023-selection/1.0 (metadata only; s.zhakypbekov@iitu.edu.kz)"}
DC = {"EarthScope": {"station": "https://service.earthscope.org/fdsnws/station/1/", "availability": None, "mustang": True},
      "INGV": {"station": "https://webservices.ingv.it/fdsnws/station/1/", "availability": "https://webservices.ingv.it/fdsnws/availability/1/", "mustang": False}}
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)


def get(url, timeout=300, tries=3, raw_name=None):
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read(); code = r.status
            if raw_name:
                with gzip.open(os.path.join(RAW, raw_name + ".gz"), "wb") as f: f.write(b)
            return code, b
        except urllib.error.HTTPError as e:
            if e.code in (204, 404): return e.code, b""
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:200]
        time.sleep(5 * (t + 1))
    return None, last.encode() if isinstance(last, str) else b""


def ts(s):
    s = s.strip().replace("Z", "")
    if not s: return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try: return datetime.datetime.strptime(s, fmt)
        except ValueError: pass
    return None


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


def svc(u):
    u = u.rstrip("/")
    return u if u.endswith("query") else u + "/query"


def covers(epochs, t0, t1):
    ep = sorted(epochs, key=lambda e: e[0])
    cur = None
    for s, e in ep:
        e = e or datetime.datetime(2100, 1, 1)
        if cur is None:
            if s > t0: return False
            cur = e
        elif s <= cur + datetime.timedelta(days=1):
            cur = max(cur, e)
        if cur >= t1: return True
    return cur is not None and cur >= t1


def fetch_streams(net, dcn):
    base = svc(DC[dcn]["station"]); rows = []
    for cha in ("BHZ", "HHZ"):
        q = urllib.parse.urlencode({"network": net, "level": "channel", "format": "text", "channel": cha, "starttime": SPAN[0], "endtime": SPAN[1]})
        code, b = get(f"{base}?{q}", timeout=900, raw_name=f"{net}_station_{cha}.txt")
        if code is None: raise RuntimeError(f"station request failed {net} {cha}: {b[:150]!r}")
        for line in b.decode("utf-8", errors="ignore").splitlines():
            if not line or line.startswith("#"): continue
            p = line.split("|")
            if len(p) < 17: continue
            try:
                rows.append({"net": p[0].strip(), "sta": p[1].strip(), "loc": p[2].strip(), "cha": p[3].strip(), "lat": float(p[4]),
                             "lon": float(p[5]), "start": ts(p[15]), "end": ts(p[16]) if len(p) > 16 else None})
            except ValueError:
                pass
    st = {}
    for r in rows:
        if r["net"] != net: continue
        k = (r["sta"], r["loc"], r["cha"])
        st.setdefault(k, {"lat": r["lat"], "lon": r["lon"], "epochs": []})["epochs"].append((r["start"], r["end"]))
    return st


def window_streams(streams, w):
    t0 = datetime.datetime.fromisoformat(WINDOWS[w][0]); t1 = datetime.datetime.fromisoformat(WINDOWS[w][2])
    best = {}
    for (sta, loc, cha), v in streams.items():
        if not covers(v["epochs"], t0, t1): continue
        key = (0 if cha == "BHZ" else 1, loc)
        if sta not in best or key < best[sta][0]:
            best[sta] = (key, {"sta": sta, "loc": loc, "cha": cha, "lat": v["lat"], "lon": v["lon"]})
    return {s: b[1] for s, b in best.items()}


def geometry(streams, ref):
    R = streams[ref]; pos = (R["lat"], R["lon"])
    d = sorted(((km(pos, (v["lat"], v["lon"])), s) for s, v in streams.items() if s != ref))
    if d and d[0][0] < R_MIN: return None, "another eligible station of the network within 20 km of the reference"
    cand = [(x, s) for x, s in d if R_MIN <= x <= R_MAX]
    sites = []
    for x, s in cand:
        p = (streams[s]["lat"], streams[s]["lon"])
        for site in sites:
            seed = site["members"][0][1]
            if km(p, (streams[seed]["lat"], streams[seed]["lon"])) <= D_MERGE:
                site["members"].append((x, s)); break
        else:
            sites.append({"dist": x, "members": [(x, s)]})
    sites = sorted(sites, key=lambda z: z["dist"])[:3]
    if len(sites) < 3: return None, f"fewer than 3 neighbour sites within 20-700 km ({len(sites)})"
    if sites[2]["dist"] < THIRD_MIN: return None, f"third site closer than 100 km ({sites[2]['dist']:.1f})"
    for s_ in sites: s_["members"] = sorted(s_["members"])[:2]
    if sum(len(s_["members"]) for s_ in sites) == 6: sites[2]["members"] = sites[2]["members"][:1]
    return [{"dist_km": round(s_["dist"], 1), "members": [{"sta": m, "dist_km": round(x, 1)} for x, m in s_["members"]]}
            for s_ in sites], None


def availability(net, dcn, stas, ws):
    """daily shares over the 90 evaluation days per (sta, loc, cha); MUSTANG for EarthScope, fdsnws-availability otherwise."""
    E0 = WINDOWS["T23"][1]; base = datetime.datetime.fromisoformat(E0); daily = {}
    chunks = [stas[i:i + 25] for i in range(0, len(stas), 25)]
    for ci, ch in enumerate(chunks):
        if DC[dcn]["mustang"]:
            q = urllib.parse.urlencode({"metric": "percent_availability", "net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ",
                                        "timewindow": f"{E0}T00:00:00,{WINDOWS['T23'][2]}T00:00:00", "format": "text"})
            code, b = get(f"https://service.earthscope.org/mustang/measurements/1/query?{q}", raw_name=f"avail_{net}_{ci}.txt")
            if code is None: raise RuntimeError(f"availability request failed: {b[:150]!r}")
            for row in csv.reader(io.StringIO(b.decode("utf-8", errors="ignore"))):
                if len(row) < 3 or not re.match(r"^[\d.]+$", row[0]): continue
                n_, s_, l_, c_ = row[1].split(".")[:4]
                t = ts(row[2]); i = (t.date() - base.date()).days if t else -1
                if 0 <= i < NEVAL: daily.setdefault((s_, l_, c_), [0.0] * NEVAL)[i] = float(row[0]) / 100.0
        else:
            q = urllib.parse.urlencode({"net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ", "start": E0, "end": WINDOWS["T23"][2],
                                        "format": "text", "mergegaps": "1.0", "merge": "quality,samplerate"})
            code, b = get(f"{svc(DC[dcn]['availability'])}?{q}", raw_name=f"avail_{net}_{ci}.txt")
            if code is None: raise RuntimeError(f"availability request failed: {b[:150]!r}")
            for line in b.decode("utf-8", errors="ignore").splitlines():
                if not line or line.startswith("#"): continue
                p = line.split()
                if len(p) < 6: continue
                s_, l_, c_ = p[1], ("" if p[2] == "--" else p[2]), p[3]
                t0, t1 = ts(p[-2]), ts(p[-1])
                if not t0 or not t1: continue
                arr = daily.setdefault((s_, l_, c_), [0.0] * NEVAL)
                a = max(0.0, (t0 - base).total_seconds()); z = min(NEVAL * 86400.0, (t1 - base).total_seconds())
                while a < z:
                    i = int(a // 86400); e = min(z, (i + 1) * 86400.0); arr[i] += (e - a) / 86400.0; a = e
    out = {}
    for s in stas:
        v = ws[s]; k = (s, v["loc"], v["cha"])
        if k in daily: out[s] = [min(1.0, x) for x in daily[k]]
    return out


def restricted(net, dcn):
    code, b = get(f"{svc(DC[dcn]['station'])}?" + urllib.parse.urlencode({"network": net, "level": "network", "format": "xml"}),
                  raw_name=f"network_{net}.xml")
    m = re.search(rb"<Network[^>]*restrictedStatus=\"(\w+)\"", b or b"")
    return m.group(1).decode() if m else "unknown"


def channel_closed(net, dcn, cfg):
    stas = [cfg["reference"]] + [m["sta"] for s in cfg["sites"] for m in s["members"]]
    code, b = get(f"{svc(DC[dcn]['station'])}?" + urllib.parse.urlencode({"network": net, "station": ",".join(stas), "channel": "BHZ,HHZ",
                                                                          "level": "channel", "format": "xml", "starttime": SPAN[0], "endtime": SPAN[1]}))
    return b"restrictedStatus=\"closed\"" in (b or b"")


def select(net, dcn):
    rec = {"network": net, "datacentre": dcn, "window": WINDOWS["T23"], "rejections": []}
    streams = fetch_streams(net, dcn); ws = window_streams(streams, "T23")
    rec["eligible_streams_covering_window"] = sorted(f"{net}.{s}.{v['loc']}.{v['cha']}" for s, v in ws.items())
    if len(ws) < 4:
        rec["result"] = f"not included: fewer than 4 eligible stations covering the window ({len(ws)})"; return rec
    geo = []
    for ref in sorted(ws):
        g, why = geometry(ws, ref)
        if g is None: rec["rejections"].append({"reference": ref, "reason": why}); continue
        geo.append({"reference": ref, "sites": g})
    if not geo:
        rec["result"] = "not included: no reference with a valid geometry"; return rec
    need = sorted({c["reference"] for c in geo} | {m["sta"] for c in geo for s in c["sites"] for m in s["members"]})
    av = availability(net, dcn, need, ws)
    passing = []
    for cfg in geo:
        ref = cfg["reference"]; r = av.get(ref)
        if r is None: rec["rejections"].append({"reference": ref, "reason": "no availability metadata for the reference stream"}); continue
        good_ref = sum(x >= 0.9 for x in r) / float(NEVAL)
        if good_ref < 0.9: rec["rejections"].append({"reference": ref, "reason": f"reference share>=0.90 on {good_ref:.1%} of days (< 90 %)"}); continue
        site_out, dead = [], None
        for s in cfg["sites"]:
            mem = []
            for m in s["members"]:
                a = av.get(m["sta"])
                if a is None: dead = f"no availability metadata for neighbour {m['sta']}"; break
                if sum(x > 0 for x in a) < NEVAL // 2: dead = f"neighbour {m['sta']} has data on fewer than 50 % of days"; break
                mem.append(a)
            if dead: break
            site = [max(col) for col in zip(*mem)]
            site_out.append(sum(x < 0.1 for x in site))
        if dead: rec["rejections"].append({"reference": ref, "reason": dead}); continue
        if max(site_out) < 3: rec["rejections"].append({"reference": ref, "reason": f"no site with >= 3 outage days (site outage days {site_out})"}); continue
        pair = any(len(s["members"]) == 2 for s in cfg["sites"])
        key = (-int(pair), -min(site_out[0], 60), -min(sum(site_out), 120), -good_ref, ref)
        R = ws[ref]
        passing.append({"window": "T23", "reference": ref, "key": key, "pair": pair, "site_outage_days": site_out,
                        "reference_good_day_share": round(good_ref, 3), "reference_stream": f"{net}.{ref}.{R['loc']}.{R['cha']}",
                        "lat": R["lat"], "lon": R["lon"],
                        "sites": [{**s, "members": [{**m, "stream": f"{net}.{m['sta']}.{ws[m['sta']]['loc']}.{ws[m['sta']]['cha']}",
                                                      "lat": ws[m["sta"]]["lat"], "lon": ws[m["sta"]]["lon"]} for m in s["members"]]}
                                  for s in cfg["sites"]]})
    if not passing:
        rec["result"] = "not included: no configuration passes sections 4-5 in the 2023 window"; return rec
    ranked = sorted(passing, key=lambda p: p["key"]); rs = restricted(net, dcn); rec["restrictedStatus"] = rs
    if rs == "closed": rec["result"] = "not included: network restrictedStatus closed"; return rec
    for p in ranked:
        if rs == "partial" and channel_closed(net, dcn, {"reference": p["reference"], "sites": p["sites"]}):
            rec["rejections"].append({"reference": p["reference"], "reason": "a selected stream is restricted (closed)"}); continue
        rec["chosen"] = p; rec["passing_configurations"] = len(ranked); rec["result"] = "included"; return rec
    rec["result"] = "not included: every passing configuration has a closed stream"; return rec


if __name__ == "__main__":
    cands = json.load(open(os.path.join(root, "results", "v2", "selection", "candidates.json"), encoding="utf-8"))["candidates_passing"]
    cands = cands if isinstance(cands, list) else list(cands.values())
    res = {"plan": "PLAN_TIME_DISJOINT_2023_2026-11-08.md section 3", "run_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "window": WINDOWS["T23"], "evaluation_days": NEVAL, "candidates": {}}
    for c in cands:
        if c["network"] not in ("A2", "CA", "OT"): continue
        try: r = select(c["network"], c["datacentre"])
        except Exception as e: r = {"network": c["network"], "result": f"not included: metadata request failed ({str(e)[:160]})"}
        r["w3_configuration_reference"] = c["reference_stream"]
        res["candidates"][c["network"]] = r; log(c["network"], r["result"], r.get("chosen", {}).get("reference_stream", ""))
    res["log"] = LOG
    json.dump(res, open(os.path.join(OUT, "candidates_2023.json"), "w"), indent=1, default=str)
