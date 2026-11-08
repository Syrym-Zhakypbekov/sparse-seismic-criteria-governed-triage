"""Batch-C network selection (SELECTION_RULE_C_2026-11-08.md), METADATA ONLY.
Re-uses the station listings archived by the rule-v2 run (results/v2/selection/raw, 07.11.2026) and the archived
availability responses; availability responses that were never requested are fetched from the same services and archived
in results/v2/selection_c/raw. Never requests events, waveforms or detections.
Output: results/v2/selection_c/{candidates.json, rejections.csv, chosen.json, raw/, raw_sha256.json}
        results/v2/networks_batchC.json (run list, networks_batchB.json format)
Usage: python analysis/v2_select_networks_c.py
"""
import os, io, re, csv, json, gzip, math, time, hashlib, datetime, threading
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEL = os.path.join(root, "results", "v2", "selection"); RAW0 = os.path.join(SEL, "raw")
OUT = os.path.join(root, "results", "v2", "selection_c"); RAW = os.path.join(OUT, "raw"); os.makedirs(RAW, exist_ok=True)
SPAN = ("2023-07-01", "2025-07-09")                       # span of the archived availability requests
TUNE0, EVAL0, EVAL1 = "2024-01-01", "2024-01-08", "2024-07-08"
NEVAL = 182
D_MERGE, R_MIN, R_MAX, THIRD_MIN = 50.0, 20.0, 700.0, 100.0
N_CHOOSE = 15
UA = {"User-Agent": "p10-v2-selection-c/1.0 (metadata only; s.zhakypbekov@iitu.edu.kz)"}
LOG = []; LOCK = threading.Lock()


def log(*a):
    s = " ".join(str(x) for x in a)
    with LOCK: LOG.append(s); print(s, flush=True)


def cached(name):
    for d in (RAW, RAW0):
        p = os.path.join(d, name + ".gz")
        if os.path.exists(p):
            with gzip.open(p, "rb") as f: return f.read()
    return None


def get(url, raw_name, timeout=300, tries=3):
    b = cached(raw_name)
    if b is not None: return 200, b, "archive"
    last = None
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                b = r.read()
            with gzip.open(os.path.join(RAW, raw_name + ".gz"), "wb") as f: f.write(b)
            return 200, b, "live"
        except urllib.error.HTTPError as e:
            if e.code in (204, 404):
                with gzip.open(os.path.join(RAW, raw_name + ".gz"), "wb") as f: f.write(b"")
                return e.code, b"", "live"
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:200]
        time.sleep(5 * (t + 1))
    return None, (last or "").encode(), "live"


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
    u = u.rstrip("/"); return u if u.endswith("query") else u + "/query"


NDAYS = (datetime.date.fromisoformat(SPAN[1]) - datetime.date.fromisoformat(SPAN[0])).days
I0 = (datetime.date.fromisoformat(EVAL0) - datetime.date.fromisoformat(SPAN[0])).days

# ------------------------------------------------------------------ exclusions
USED = set()
for f in ("networks.json", "networks_batchB.json"):
    d = json.load(open(os.path.join(root, "results", "v2", f)))
    USED |= {n["network"] for n in d["networks"]}
    for k in ("eligible_not_run", "eligible_period_not_covered", "batch_A"):
        pass
EXCLUDED = USED | {"IU", "II", "IM", "G", "KZ", "AK"}
REVIEWED38 = list(json.load(open(os.path.join(root, "results", "v2_reviewed", "v2_eval_reviewed.json")))["networks"].keys())

DCS = json.load(open(os.path.join(SEL, "datacentres.json")))
REJ = []


def rej(dc, net, sta, why): REJ.append({"datacentre": dc, "network": net, "reference": sta, "reason": why})


def channels(dc):
    rows = []
    for cha in ("BHZ", "HHZ"):
        name = re.sub(r"\W", "_", dc["name"] + "_" + (dc["repository"] or "")) + f"_station_{cha}.txt"
        b = cached(name)
        if b is None: continue
        for line in b.decode("utf-8", errors="ignore").splitlines():
            if not line or line.startswith("#"): continue
            p = line.split("|")
            if len(p) < 17: continue
            try:
                rows.append({"net": p[0].strip(), "sta": p[1].strip(), "loc": p[2].strip(), "cha": p[3].strip(),
                             "lat": float(p[4]), "lon": float(p[5]), "start": ts(p[15]), "end": ts(p[16])})
            except ValueError:
                pass
    return rows


def covers(epochs, t0, t1):
    cur = None
    for s, e in sorted(epochs, key=lambda e: e[0]):
        e = e or datetime.datetime(2100, 1, 1)
        if cur is None:
            if s > t0: return False
            cur = e
        elif s <= cur + datetime.timedelta(days=1):
            cur = max(cur, e)
        if cur >= t1: return True
    return cur is not None and cur >= t1


NETS = {}
seen = []
for dc in DCS:
    if dc.get("excluded"): continue
    rows = channels(dc)
    by = {}
    for r in rows: by.setdefault(r["net"], []).append(r)
    for net, rr in sorted(by.items()):
        seen.append({"datacentre": dc["name"], "network": net, "channels": len(rr)})
        if net in EXCLUDED: rej(dc["name"], net, "", "network already used in the study"); continue
        if net[0].isdigit() or net[0] in "XYZ": rej(dc["name"], net, "", "temporary network code"); continue
        if dc["name"] == "RASPISHAKE": rej(dc["name"], net, "", "citizen network data centre excluded"); continue
        if net in NETS: rej(dc["name"], net, "", f"network already taken from data centre {NETS[net]['dc']['name']}"); continue
        if not dc.get("availability_source"): rej(dc["name"], net, "", "no daily availability metadata at this data centre"); continue
        st = {}
        for r in rr:
            st.setdefault((r["sta"], r["loc"], r["cha"]), {"lat": r["lat"], "lon": r["lon"], "epochs": []})["epochs"].append((r["start"], r["end"]))
        NETS[net] = {"dc": dc, "streams": st}

T0 = datetime.datetime.fromisoformat(TUNE0); T1 = datetime.datetime.fromisoformat(EVAL1)


def window_streams(net):
    best = {}
    for (sta, loc, cha), v in NETS[net]["streams"].items():
        if not covers(v["epochs"], T0, T1): continue
        key = (0 if cha == "BHZ" else 1, loc)
        if sta not in best or key < best[sta][0]:
            best[sta] = (key, {"sta": sta, "loc": loc, "cha": cha, "lat": v["lat"], "lon": v["lon"]})
    return {s: b[1] for s, b in best.items()}


def geometry(streams, ref):
    R = streams[ref]; pos = (R["lat"], R["lon"])
    d = sorted(((km(pos, (v["lat"], v["lon"])), s) for s, v in streams.items() if s != ref))
    if d and d[0][0] < R_MIN: return None, "another eligible station of the network within 20 km of the reference"
    sites = []
    for x, s in [(x, s) for x, s in d if R_MIN <= x <= R_MAX]:
        p = (streams[s]["lat"], streams[s]["lon"])
        for site in sites:
            seed = site["members"][0][1]
            if km(p, (streams[seed]["lat"], streams[seed]["lon"])) <= D_MERGE: site["members"].append((x, s)); break
        else:
            sites.append({"dist": x, "members": [(x, s)]})
    sites = sorted(sites, key=lambda z: z["dist"])[:3]
    if len(sites) < 3: return None, f"fewer than 3 neighbour sites within 20-700 km ({len(sites)})"
    if sites[2]["dist"] < THIRD_MIN: return None, f"third site closer than 100 km ({sites[2]['dist']:.1f})"
    for s_ in sites: s_["members"] = sorted(s_["members"])[:2]
    if sum(len(s_["members"]) for s_ in sites) == 6: sites[2]["members"] = sites[2]["members"][:1]
    return [{"dist_km": round(s_["dist"], 1), "members": [{"sta": m, "dist_km": round(x, 1)} for x, m in s_["members"]]}
            for s_ in sites], None


def region(lat, lon):
    if lat < -60: return "Antarctica"
    if 25 <= lat <= 45 and 26 <= lon <= 63: return "Middle East-Caucasus-Turkey-Iran"
    if 30 <= lat <= 56 and 45 <= lon <= 100: return "Central Asia"
    if 35 <= lat <= 44.5 and -10 <= lon <= 4: return "Iberia"
    if 55 <= lat <= 75 and -45 <= lon <= 32: return "Scandinavia-Iceland-North Atlantic"
    if 34 <= lat <= 56 and 13 <= lon <= 45: return "Eastern Europe-Balkans"
    if 34 <= lat <= 72 and -25 <= lon <= 45: return "Western-Central Europe"
    if -40 <= lat <= 37 and -20 <= lon <= 55: return "Africa"
    if -11 <= lat <= 56 and 95 <= lon <= 160: return "South-East Asia-East Asia"
    if (-60 <= lat <= -11 and 110 <= lon <= 180) or (lon < -170 and lat < 0): return "Oceania"
    if lat >= 50 and -180 <= lon <= -50: return "Alaska-Aleutians-Canada"
    if 13 <= lat <= 50 and -130 <= lon <= -60: return "USA-Mexico"
    if 5 <= lat <= 25 and -95 <= lon <= -55: return "Central America-Caribbean"
    if -60 <= lat <= 13 and -95 <= lon <= -30: return "South America"
    return "Other"


GEOM, need = {}, {}
for net in sorted(NETS):
    ws = window_streams(net)
    if len(ws) < 4: rej(NETS[net]["dc"]["name"], net, "", f"fewer than 4 eligible stations covering the window ({len(ws)})"); continue
    for ref in sorted(ws):
        if region(ws[ref]["lat"], ws[ref]["lon"]) in ("USA-Mexico", "Alaska-Aleutians-Canada"):
            rej(NETS[net]["dc"]["name"], net, ref, "reference in North America (excluded for batch C)"); continue
        g, why = geometry(ws, ref)
        if g is None: rej(NETS[net]["dc"]["name"], net, ref, why); continue
        GEOM.setdefault(net, []).append({"reference": ref, "sites": g, "streams": ws})
        need.setdefault(net, set()).update([ref] + [m["sta"] for s in g for m in s["members"]])
log("networks seen", len(seen), "eligible", len(NETS), "with geometry", len(GEOM))

AV, SRC = {}, {}


def avail_net(net):
    dc = NETS[net]["dc"]; stas = sorted(need[net]); daily = {}; src = set()
    ws = window_streams(net)
    loc_cha = {s: (ws[s]["loc"], ws[s]["cha"]) for s in stas}
    for ci, ch in enumerate([stas[i:i + 25] for i in range(0, len(stas), 25)]):
        mustang = dc["availability_source"].startswith("MUSTANG")
        if mustang:
            q = urllib.parse.urlencode({"metric": "percent_availability", "net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ",
                                        "timewindow": f"{SPAN[0]}T00:00:00,{SPAN[1]}T00:00:00", "format": "text"})
            url = f"https://service.earthscope.org/mustang/measurements/1/query?{q}"
        else:
            q = urllib.parse.urlencode({"net": net, "sta": ",".join(ch), "cha": "BHZ,HHZ", "start": SPAN[0], "end": SPAN[1],
                                        "format": "text", "mergegaps": "1.0", "merge": "quality,samplerate"})
            url = f"{svc(dc['availability'])}?{q}"
        # archived names from the rule-v2 run are keyed by chunk index of a possibly different station list; use a
        # station-list-specific name for new requests and fall back to the rule-v2 name only when its list is identical
        name = f"avail_{net}_{hashlib.sha1(','.join(ch).encode()).hexdigest()[:10]}.txt"
        code, b, s = get(url, name)
        if code is None: return net, f"availability request failed: {b[:150]!r}", src
        src.add(s)
        txt = b.decode("utf-8", errors="ignore")
        if mustang:
            for row in csv.reader(io.StringIO(txt)):
                if len(row) < 3 or not re.match(r"^[\d.]+$", row[0]): continue
                n_, s_, l_, c_ = row[1].split(".")[:4]
                t = ts(row[2]); i = (t.date() - datetime.date.fromisoformat(SPAN[0])).days if t else -1
                if 0 <= i < NDAYS: daily.setdefault((s_, l_, c_), [0.0] * NDAYS)[i] = float(row[0]) / 100.0
        else:
            base = datetime.datetime.fromisoformat(SPAN[0])
            for line in txt.splitlines():
                if not line or line.startswith("#"): continue
                p = line.split()
                if len(p) < 6: continue
                s_, l_, c_ = p[1], ("" if p[2] == "--" else p[2]), p[3]
                t0, t1 = ts(p[-2]), ts(p[-1])
                if not t0 or not t1: continue
                arr = daily.setdefault((s_, l_, c_), [0.0] * NDAYS)
                a = max(0.0, (t0 - base).total_seconds()); z = min(NDAYS * 86400.0, (t1 - base).total_seconds())
                while a < z:
                    i = int(a // 86400); e = min(z, (i + 1) * 86400.0); arr[i] += (e - a) / 86400.0; a = e
    out = {}
    for s, (l_, c_) in loc_cha.items():
        if (s, l_, c_) in daily: out[s] = [min(1.0, x) for x in daily[(s, l_, c_)]][I0:I0 + NEVAL]
    return net, out, src


with ThreadPoolExecutor(10) as ex:
    for net, res, src in ex.map(avail_net, sorted(GEOM)):
        if isinstance(res, str): rej(NETS[net]["dc"]["name"], net, "", res); continue
        AV[net] = res; SRC[net] = sorted(src)
        log("availability", net, len(res), "streams", SRC[net])


def restricted(net):
    dc = NETS[net]["dc"]
    code, b, _ = get(f"{svc(dc['station'])}?" + urllib.parse.urlencode({"network": net, "level": "network", "format": "xml"}),
                     f"network_{net}.xml")
    m = re.search(rb"<Network[^>]*restrictedStatus=\"(\w+)\"", b or b"")
    return m.group(1).decode() if m else "unknown"


CAND = {}
for net in sorted(GEOM):
    if net not in AV: continue
    passing = []
    for cfg in GEOM[net]:
        ref = cfg["reference"]; ws = cfg["streams"]
        r = AV[net].get(ref)
        if r is None: rej(NETS[net]["dc"]["name"], net, ref, "no availability metadata for the reference stream"); continue
        good = sum(x >= 0.9 for x in r) / NEVAL
        if good < 0.9: rej(NETS[net]["dc"]["name"], net, ref, f"reference share>=0.90 on {good:.1%} of days (< 90 %)"); continue
        dead, site_out = None, []
        for s in cfg["sites"]:
            mem = []
            for m in s["members"]:
                a = AV[net].get(m["sta"])
                if a is None: dead = f"no availability metadata for neighbour {m['sta']}"; break
                if sum(x > 0 for x in a) < NEVAL / 2: dead = f"neighbour {m['sta']} has data on fewer than 50 % of days"; break
                mem.append(a)
            if dead: break
            site_out.append(sum(x < 0.1 for x in [max(col) for col in zip(*mem)]))
        if dead: rej(NETS[net]["dc"]["name"], net, ref, dead); continue
        pair = any(len(s["members"]) == 2 for s in cfg["sites"])
        dc = NETS[net]["dc"]["name"]
        key = (int(dc == "EarthScope"), -int(pair), -good, ref)
        R = ws[ref]
        passing.append({"reference": ref, "key": key, "pair": pair, "site_outage_days": site_out,
                        "reference_good_day_share": round(good, 3),
                        "reference_stream": f"{net}.{ref}.{R['loc']}.{R['cha']}", "lat": R["lat"], "lon": R["lon"],
                        "sites": [{**s, "members": [{**m, "stream": f"{net}.{m['sta']}.{ws[m['sta']]['loc']}.{ws[m['sta']]['cha']}",
                                                      "lat": ws[m["sta"]]["lat"], "lon": ws[m["sta"]]["lon"]} for m in s["members"]]}
                                  for s in cfg["sites"]]})
    if not passing: continue
    ranked = sorted(passing, key=lambda p: p["key"])
    rs = restricted(net)
    if rs == "closed": rej(NETS[net]["dc"]["name"], net, "", "network restrictedStatus closed"); continue
    c = ranked[0]
    c.update({"network": net, "datacentre": NETS[net]["dc"]["name"], "dataselect": NETS[net]["dc"]["dataselect"],
              "station_service": NETS[net]["dc"]["station"], "restrictedStatus": rs,
              "passing_configurations": len(ranked), "region": region(c["lat"], c["lon"]),
              "n_streams": 1 + sum(len(s["members"]) for s in c["sites"])})
    c["expected_raw_GB_6mo"] = round(0.45 * c["n_streams"], 2)
    CAND[net] = c

covered = set()
for f in ("networks.json", "networks_batchB.json"):
    for n in json.load(open(os.path.join(root, "results", "v2", f)))["networks"]:
        if n["network"] in REVIEWED38: covered.add(region(n["lat"], n["lon"]))
byreg = {}
for c in CAND.values(): byreg.setdefault(c["region"], []).append(c)
for r in byreg.values(): r.sort(key=lambda c: c["key"])
order = sorted(byreg, key=lambda r: (int(r in covered), byreg[r][0]["key"]))
CHOSEN, i = [], 0
while len(CHOSEN) < N_CHOOSE and any(i < len(byreg[r]) for r in order):
    for r in order:
        if i < len(byreg[r]) and len(CHOSEN) < N_CHOOSE: CHOSEN.append(byreg[r][i])
    i += 1
for c in CAND.values():
    if c not in CHOSEN: rej(c["datacentre"], c["network"], c["reference"], "passed rule C but not chosen (15-network cap, round-robin)")

json.dump({"networks_seen": seen, "candidates_passing": {k: {kk: vv for kk, vv in v.items() if kk != "key"} for k, v in CAND.items()}},
          open(os.path.join(OUT, "candidates.json"), "w"), indent=1, default=str)
with open(os.path.join(OUT, "rejections.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["datacentre", "network", "reference", "reason"]); w.writeheader(); w.writerows(REJ)
summary = {"rule": "SELECTION_RULE_C_2026-11-08.md", "run_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
           "networks_seen": len(seen), "networks_eligible": len(NETS), "networks_with_geometry": len(GEOM),
           "networks_passing": len(CAND), "networks_chosen": len(CHOSEN), "regions_covered_by_reviewed_A_B": sorted(covered),
           "region_order": order, "regions_chosen": sorted({c["region"] for c in CHOSEN}),
           "expected_raw_GB_6mo_total": round(sum(c["expected_raw_GB_6mo"] for c in CHOSEN), 1),
           "chosen": [{k: v for k, v in c.items() if k != "key"} for c in CHOSEN]}
rc = {}
for r in REJ:
    k = re.sub(r"[\d.]+%?|\(.*?\)|\[.*?\]", "#", r["reason"]); rc[k] = rc.get(k, 0) + 1
summary["rejection_reason_counts"] = rc
json.dump(summary, open(os.path.join(OUT, "chosen.json"), "w"), indent=1, default=str)
open(os.path.join(OUT, "selection.log"), "w", encoding="utf-8").write("\n".join(LOG))
json.dump({f: hashlib.sha256(open(os.path.join(RAW, f), "rb").read()).hexdigest() for f in sorted(os.listdir(RAW))},
          open(os.path.join(OUT, "raw_sha256.json"), "w"), indent=1)

# run list in the networks_batchB.json format
nets = []
for k, c in enumerate(CHOSEN, start=1):
    roles = {"MAKZ": c["reference_stream"]}
    for si, s in enumerate(c["sites"], start=1):
        for mi, m in enumerate(s["members"], start=1): roles[f"S{si}_{mi}"] = m["stream"]
    nets.append({"rule_order": 100 + k, "network": c["network"], "region": c["region"], "datacentre": c["datacentre"],
                 "dataselect": c["dataselect"], "fdsn_base": "" if c["datacentre"] == "EarthScope" else c["dataselect"].split("/fdsnws")[0],
                 "reference_stream": c["reference_stream"], "lat": c["lat"], "lon": c["lon"], "selection_window": "C182",
                 "site_outage_days_in_selection_window": c["site_outage_days"],
                 "reference_good_day_share": c["reference_good_day_share"], "has_merged_pair": c["pair"],
                 "sites": [{"rank": i + 1, **s} for i, s in enumerate(c["sites"])],
                 "tune_start": TUNE0, "eval_start": EVAL0, "eval_end": EVAL1, "roles": roles,
                 "expected_raw_GB_6mo": c["expected_raw_GB_6mo"]})
json.dump({"amendment": "PREREGISTRATION_V2_BATCHC_2026-11-08.md", "rule": "SELECTION_RULE_C_2026-11-08.md",
           "period": {"tune_start": TUNE0, "eval_start": EVAL0, "eval_end": EVAL1}, "networks": nets},
          open(os.path.join(root, "results", "v2", "networks_batchC.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in summary.items() if k not in ("chosen", "rejection_reason_counts")}, indent=1))
for c in CHOSEN:
    print(c["region"], c["network"], c["datacentre"], c["reference_stream"], c["n_streams"], c["expected_raw_GB_6mo"],
          [[m["stream"] + f" {m['dist_km']}" for m in s["members"]] for s in c["sites"]])
