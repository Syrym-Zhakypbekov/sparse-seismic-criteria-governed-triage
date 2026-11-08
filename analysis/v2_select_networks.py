"""Network selection for the multi-network test of rule v2 (SELECTION_RULE_V2_2026-11-08.md), METADATA ONLY.
Reads: FDSN data-centre registry, fdsnws-station (channel level, text; network level, XML for restrictedStatus),
fdsnws-availability time spans or EarthScope MUSTANG percent_availability. Never requests events, waveforms or detections.
Output: results/v2/selection/{registry.json, datacentres.json, candidates.json, rejections.csv, chosen.json, raw/*}
Usage: python analysis/v2_select_networks.py            (network access; several minutes)
"""
import os, io, re, csv, json, gzip, math, time, hashlib, datetime, threading
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(root, "results", "v2", "selection"); RAW = os.path.join(OUT, "raw"); os.makedirs(RAW, exist_ok=True)
EXCLUDED_NETS = {"IU", "II", "IM", "G", "KZ", "AK"}
WINDOWS = {"W1": ("2023-07-01", "2023-07-08", "2024-07-08"),
           "W2": ("2024-01-01", "2024-01-08", "2025-01-08"),
           "W3": ("2024-07-01", "2024-07-08", "2025-07-09")}
SPAN = ("2023-07-01", "2025-07-09")
D_MERGE, R_MIN, R_MAX, THIRD_MIN = 50.0, 20.0, 700.0, 100.0
UA = {"User-Agent": "p10-v2-selection/1.0 (metadata only; s.zhakypbekov@iitu.edu.kz)"}
LOG = []; LOCK = threading.Lock()


def log(*a):
    s = " ".join(str(x) for x in a)
    with LOCK: LOG.append(s); print(s, flush=True)


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


def day_index(d):
    return (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(SPAN[0])).days


NDAYS = day_index(SPAN[1])


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


# ------------------------------------------------------------------ 1. data centres
code, b = get("https://www.fdsn.org/ws/datacenters/1/query?format=json&includedatasets=false", raw_name="registry.json")
REG = json.loads(b)
json.dump(REG, open(os.path.join(OUT, "registry.json"), "w"), indent=1)
DCS = []
for dc in REG["datacenters"]:
    for rep in dc.get("repositories", []):
        sv = {}
        for s in rep.get("services", []): sv.setdefault(s["name"], s.get("url"))
        st, ds, av = sv.get("fdsnws-station-1"), sv.get("fdsnws-dataselect-1"), sv.get("fdsnws-availability-1")
        rec = {"name": dc["name"], "repository": rep.get("name"), "station": st, "dataselect": ds, "availability": av}
        if not st or not ds:
            rec["excluded"] = "no fdsnws-station-1 and fdsnws-dataselect-1 pair"
        elif "auth" in ds.lower():
            rec["excluded"] = "dataselect requires authentication"
        if dc["name"] == "EarthScope" and not rec.get("excluded"):
            rec["availability_source"] = "MUSTANG percent_availability"
        elif av and not rec.get("excluded"):
            rec["availability_source"] = "fdsnws-availability-1"
        else:
            rec["availability_source"] = None
        DCS.append(rec)


def svc(u):
    u = u.rstrip("/")
    return u if u.endswith("query") else u + "/query"


def fetch_channels(dc):
    if dc.get("excluded"): return
    base = svc(dc["station"]); rows = []; errs = []
    for cha in ("BHZ", "HHZ"):
        q = urllib.parse.urlencode({"level": "channel", "format": "text", "channel": cha,
                                    "starttime": SPAN[0], "endtime": SPAN[1]})
        name = re.sub(r"\W", "_", dc["name"] + "_" + (dc["repository"] or "")) + f"_station_{cha}.txt"
        code, b = get(f"{base}?{q}", timeout=900, raw_name=name)
        if code is None: errs.append(f"{cha}: {b.decode(errors='ignore')}"); continue
        if code in (204, 404): continue
        txt = b.decode("utf-8", errors="ignore")
        for line in txt.splitlines():
            if not line or line.startswith("#"): continue
            p = line.split("|")
            if len(p) < 17: continue
            try:
                rows.append({"net": p[0].strip(), "sta": p[1].strip(), "loc": p[2].strip(), "cha": p[3].strip(),
                             "lat": float(p[4]), "lon": float(p[5]), "sr": float(p[14] or 0),
                             "start": ts(p[15]), "end": ts(p[16]) if len(p) > 16 else None})
            except ValueError:
                pass
    dc["channel_rows"] = len(rows); dc["errors"] = errs; dc["_rows"] = rows
    log("station", dc["name"], dc["repository"], len(rows), errs[:1])


with ThreadPoolExecutor(8) as ex: list(ex.map(fetch_channels, DCS))

# ------------------------------------------------------------------ 2-3. networks, streams per window
REJ = []  # (dc, net, station or "", window, reason)


def rej(dc, net, sta, w, why): REJ.append({"datacentre": dc, "network": net, "reference": sta, "window": w, "reason": why})


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


NETS = {}   # net -> {"dc": dcrec, "stations": {sta: {...}}}
seen = []
for dc in DCS:
    if dc.get("excluded") or not dc.get("_rows"): continue
    by = {}
    for r in dc["_rows"]: by.setdefault(r["net"], []).append(r)
    for net, rows in sorted(by.items()):
        seen.append({"datacentre": dc["name"], "network": net, "channels": len(rows)})
        if net in EXCLUDED_NETS: rej(dc["name"], net, "", "", "network already used in the study"); continue
        if net[0].isdigit() or net[0] in "XYZ": rej(dc["name"], net, "", "", "temporary network code"); continue
        if net in NETS: rej(dc["name"], net, "", "", f"network already taken from data centre {NETS[net]['dc']['name']}"); continue
        if not dc["availability_source"]:
            rej(dc["name"], net, "", "", "data centre offers no daily availability metadata (later data centre may)"); continue
        st = {}
        for r in rows:
            k = (r["sta"], r["loc"], r["cha"])
            st.setdefault(k, {"lat": r["lat"], "lon": r["lon"], "epochs": []})["epochs"].append((r["start"], r["end"]))
        NETS[net] = {"dc": dc, "streams": st}


def window_streams(net, w):
    t0 = datetime.datetime.fromisoformat(WINDOWS[w][0]); t1 = datetime.datetime.fromisoformat(WINDOWS[w][2])
    best = {}
    for (sta, loc, cha), v in NETS[net]["streams"].items():
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


GEOM = {}  # net -> w -> list of configs
need = {}  # net -> set of station codes needing availability
for net in sorted(NETS):
    for w in WINDOWS:
        ws = window_streams(net, w)
        if len(ws) < 4: rej(NETS[net]["dc"]["name"], net, "", w, f"fewer than 4 eligible stations covering the window ({len(ws)})"); continue
        for ref in sorted(ws):
            g, why = geometry(ws, ref)
            if g is None: rej(NETS[net]["dc"]["name"], net, ref, w, why); continue
            GEOM.setdefault(net, {}).setdefault(w, []).append({"reference": ref, "sites": g, "streams": ws})
            need.setdefault(net, set()).update([ref] + [m["sta"] for s in g for m in s["members"]])
log("networks seen", len(seen), "eligible", len(NETS), "with geometry", len(GEOM))

# ------------------------------------------------------------------ 5. availability (metadata)
AV = {}  # net -> sta -> list of daily shares over SPAN


def avail_net(net):
    dc = NETS[net]["dc"]; stas = sorted(need[net]); daily = {}
    loc_cha = {}
    for w in WINDOWS:
        for s, v in window_streams(net, w).items():
            if s in need[net]: loc_cha.setdefault(s, set()).add((v["loc"], v["cha"]))
    chunks = [stas[i:i + 25] for i in range(0, len(stas), 25)]
    for ci, ch in enumerate(chunks):
        if dc["availability_source"].startswith("MUSTANG"):
            q = urllib.parse.urlencode({"metric": "percent_availability", "net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ",
                                        "timewindow": f"{SPAN[0]}T00:00:00,{SPAN[1]}T00:00:00", "format": "text"})
            code, b = get(f"https://service.earthscope.org/mustang/measurements/1/query?{q}", raw_name=f"avail_{net}_{ci}.txt")
            if code is None: return net, f"availability request failed: {b[:150]!r}"
            for row in csv.reader(io.StringIO(b.decode("utf-8", errors="ignore"))):
                if len(row) < 3 or not re.match(r"^[\d.]+$", row[0]): continue
                n_, s_, l_, c_ = row[1].split(".")[:4]
                t = ts(row[2]); i = (t.date() - datetime.date.fromisoformat(SPAN[0])).days if t else -1
                if 0 <= i < NDAYS: daily.setdefault((s_, l_, c_), [0.0] * NDAYS)[i] = float(row[0]) / 100.0
        else:
            q = urllib.parse.urlencode({"net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ", "start": SPAN[0], "end": SPAN[1],
                                        "format": "text", "mergegaps": "1.0", "merge": "quality,samplerate"})
            code, b = get(f"{svc(dc['availability'])}?{q}", raw_name=f"avail_{net}_{ci}.txt")
            if code is None: return net, f"availability request failed: {b[:150]!r}"
            for line in b.decode("utf-8", errors="ignore").splitlines():
                if not line or line.startswith("#"): continue
                p = line.split()
                if len(p) < 6: continue
                s_, l_, c_ = p[1], ("" if p[2] == "--" else p[2]), p[3]
                t0, t1 = ts(p[-2]), ts(p[-1])
                if not t0 or not t1: continue
                arr = daily.setdefault((s_, l_, c_), [0.0] * NDAYS)
                base = datetime.datetime.fromisoformat(SPAN[0])
                a = max(0.0, (t0 - base).total_seconds()); z = min(NDAYS * 86400.0, (t1 - base).total_seconds())
                while a < z:
                    i = int(a // 86400); e = min(z, (i + 1) * 86400.0); arr[i] += (e - a) / 86400.0; a = e
    out = {}
    for s, lc in loc_cha.items():
        for l_, c_ in lc:
            if (s, l_, c_) in daily: out[(s, l_, c_)] = [min(1.0, x) for x in daily[(s, l_, c_)]]
    return net, out


with ThreadPoolExecutor(12) as ex:
    for net, res in ex.map(avail_net, sorted(GEOM)):
        if isinstance(res, str): rej(NETS[net]["dc"]["name"], net, "", "", res); continue
        AV[net] = res
        log("availability", net, len(res), "streams")


def shares(net, w, sta, ws):
    v = ws[sta]; a = AV.get(net, {}).get((sta, v["loc"], v["cha"]))
    if a is None: return None
    i0 = day_index(WINDOWS[w][1]); return a[i0:i0 + 366]


def restricted(net):
    dc = NETS[net]["dc"]
    code, b = get(f"{svc(dc['station'])}?" + urllib.parse.urlencode({"network": net, "level": "network", "format": "xml"}),
                  raw_name=f"network_{net}.xml")
    m = re.search(rb"<Network[^>]*restrictedStatus=\"(\w+)\"", b or b"")
    return m.group(1).decode() if m else "unknown"


def channel_closed(net, cfg):
    dc = NETS[net]["dc"]; stas = [cfg["reference"]] + [m["sta"] for s in cfg["sites"] for m in s["members"]]
    code, b = get(f"{svc(dc['station'])}?" + urllib.parse.urlencode({"network": net, "station": ",".join(stas), "channel": "BHZ,HHZ",
                                                                      "level": "channel", "format": "xml", "starttime": SPAN[0], "endtime": SPAN[1]}))
    return b"restrictedStatus=\"closed\"" in (b or b"")


CAND = {}
for net in sorted(GEOM):
    if net not in AV: continue
    passing = []
    for w in WINDOWS:
        for cfg in GEOM[net].get(w, []):
            ws = cfg["streams"]; ref = cfg["reference"]
            r = shares(net, w, ref, ws)
            if r is None: rej(NETS[net]["dc"]["name"], net, ref, w, "no availability metadata for the reference stream"); continue
            good_ref = sum(x >= 0.9 for x in r) / 366.0
            if good_ref < 0.9: rej(NETS[net]["dc"]["name"], net, ref, w, f"reference share>=0.90 on {good_ref:.1%} of days (< 90 %)"); continue
            site_out, dead = [], None
            for s in cfg["sites"]:
                mem = []
                for m in s["members"]:
                    a = shares(net, w, m["sta"], ws)
                    if a is None: dead = f"no availability metadata for neighbour {m['sta']}"; break
                    if sum(x > 0 for x in a) < 183: dead = f"neighbour {m['sta']} has data on fewer than 50 % of days"; break
                    mem.append(a)
                if dead: break
                site = [max(col) for col in zip(*mem)]
                site_out.append(sum(x < 0.1 for x in site))
            if dead: rej(NETS[net]["dc"]["name"], net, ref, w, dead); continue
            if max(site_out) < 3: rej(NETS[net]["dc"]["name"], net, ref, w, f"no site with >= 3 outage days (site outage days {site_out})"); continue
            pair = any(len(s["members"]) == 2 for s in cfg["sites"])
            key = (-int(pair), -min(site_out[0], 60), -min(sum(site_out), 120), -good_ref, ref)
            R = ws[ref]
            passing.append({"window": w, "reference": ref, "key": key, "pair": pair, "site_outage_days": site_out,
                            "reference_good_day_share": round(good_ref, 3),
                            "reference_stream": f"{net}.{ref}.{R['loc']}.{R['cha']}", "lat": R["lat"], "lon": R["lon"],
                            "sites": [{**s, "members": [{**m, "stream": f"{net}.{m['sta']}.{ws[m['sta']]['loc']}.{ws[m['sta']]['cha']}",
                                                          "lat": ws[m["sta"]]["lat"], "lon": ws[m["sta"]]["lon"]} for m in s["members"]]}
                                      for s in cfg["sites"]]})
    if not passing: continue
    win = min(p["window"] for p in passing)                  # earliest passing window (section 2)
    ranked = sorted([p for p in passing if p["window"] == win], key=lambda p: p["key"])
    rs = restricted(net)
    if rs == "closed": rej(NETS[net]["dc"]["name"], net, "", win, "network restrictedStatus closed"); continue
    chosen = None
    for p in ranked:
        if rs == "partial" and channel_closed(net, {"reference": p["reference"], "sites": p["sites"]}):
            rej(NETS[net]["dc"]["name"], net, p["reference"], win, "a selected stream is restricted (closed)"); continue
        chosen = p; break
    if chosen:
        chosen.update({"network": net, "datacentre": NETS[net]["dc"]["name"], "dataselect": NETS[net]["dc"]["dataselect"],
                       "restrictedStatus": rs, "passing_configurations_in_window": len(ranked)})
        CAND[net] = chosen


def region(lat, lon):
    if lat < -60: return "Antarctica"
    if 55 <= lat <= 75 and -45 <= lon <= -5: return "Iceland-North Atlantic"
    if 25 <= lat <= 45 and 26 <= lon <= 63: return "Caucasus-Turkey-Iran"
    if 30 <= lat <= 56 and 45 <= lon <= 100: return "Central Asia"
    if 34 <= lat <= 72 and -25 <= lon <= 45: return "Europe incl. Alps-Balkans"
    if -40 <= lat <= 37 and -20 <= lon <= 55: return "Africa"
    if -11 <= lat <= 56 and 95 <= lon <= 160: return "East Asia-West Pacific"
    if (-60 <= lat <= -11 and 110 <= lon <= 180) or (lon < -170 and lat < 0): return "New Zealand-SW Pacific"
    if lat >= 50 and -180 <= lon <= -50: return "Alaska-Aleutians-Canada"
    if 13 <= lat <= 50 and -130 <= lon <= -60: return "USA-Mexico"
    if 5 <= lat <= 25 and -95 <= lon <= -55: return "Central America-Caribbean"
    if -60 <= lat <= 13 and -95 <= lon <= -30: return "South America"
    return "Other"


byreg = {}
for net, c in CAND.items():
    c["region"] = region(c["lat"], c["lon"]); byreg.setdefault(c["region"], []).append(c)
for r in byreg.values(): r.sort(key=lambda c: c["key"])
order = sorted(byreg, key=lambda r: byreg[r][0]["key"])
CHOSEN = []
i = 0
while len(CHOSEN) < 24 and any(i < len(byreg[r]) for r in order):
    for r in order:
        if i < len(byreg[r]) and len(CHOSEN) < 24: CHOSEN.append(byreg[r][i])
    i += 1
for c in CAND.values():
    if c not in CHOSEN: rej(c["datacentre"], c["network"], c["reference"], c["window"], "passed the rule but not chosen (24-network cap, round-robin)")

for dc in DCS: dc.pop("_rows", None)
json.dump(DCS, open(os.path.join(OUT, "datacentres.json"), "w"), indent=1)
json.dump({"networks_seen": seen, "candidates_passing": {k: {kk: vv for kk, vv in v.items() if kk != "key"} for k, v in CAND.items()}},
          open(os.path.join(OUT, "candidates.json"), "w"), indent=1, default=str)
with open(os.path.join(OUT, "rejections.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["datacentre", "network", "reference", "window", "reason"]); w.writeheader(); w.writerows(REJ)
summary = {"rule": "SELECTION_RULE_V2_2026-11-08.md", "run_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
           "datacentres": len(DCS), "datacentres_usable": sum(1 for d in DCS if not d.get("excluded")),
           "networks_seen": len(seen), "networks_eligible": len(NETS), "networks_with_geometry": len(GEOM),
           "networks_passing": len(CAND), "networks_chosen": len(CHOSEN), "regions_chosen": sorted({c["region"] for c in CHOSEN}),
           "rejection_reason_counts": {}, "chosen": [{k: v for k, v in c.items() if k != "key"} for c in CHOSEN]}
for r in REJ:
    k = re.sub(r"[\d.]+%?|\(.*?\)|\[.*?\]", "#", r["reason"]); summary["rejection_reason_counts"][k] = summary["rejection_reason_counts"].get(k, 0) + 1
json.dump(summary, open(os.path.join(OUT, "chosen.json"), "w"), indent=1, default=str)
open(os.path.join(OUT, "selection.log"), "w", encoding="utf-8").write("\n".join(LOG))
sha = {f: hashlib.sha256(open(os.path.join(RAW, f), "rb").read()).hexdigest() for f in sorted(os.listdir(RAW))}
json.dump(sha, open(os.path.join(OUT, "raw_sha256.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "chosen"}, indent=1))
for c in CHOSEN:
    print(c["region"], c["network"], c["datacentre"], c["window"], c["reference_stream"], c["site_outage_days"],
          [[m["stream"] + f" {m['dist_km']}" for m in s["members"]] for s in c["sites"]])
