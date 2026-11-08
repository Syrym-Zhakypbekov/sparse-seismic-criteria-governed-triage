"""Time-disjointness check of PLAN_TIME_DISJOINT_2023_2026-11-08.md (run BEFORE the plan was written; no waveform, event or
detection of 2023 is requested by this script).

For every unit network of the planned test (the 33 reviewed-bulletin networks and the candidates A2, CA, OT) it lists every
period ever downloaded or scored for that network code, from four sources:
  1. every run artefact under results/ (status.json: stations + tune/eval period; summary.json: channel ids + params tune/dev;
     availability.csv: first and last day), including staging, rescue, replicate and Kaggle copies;
  2. the listing of the raw-waveform bucket gs://p10-raw-waveforms (gcloud storage ls -r, saved to a file and passed here);
  3. every plan file in the repository root (PREREGISTRATION*, PLAN*, SELECTION*, ANALYSIS_PLAN*, EXPERIMENT_LEDGER, MANIFEST):
     each ISO date that falls inside the planned download span is reported with its line;
  4. selection metadata windows (results/v2/selection/chosen.json, networks*.json "selection_window"), reported separately
     because they are station/availability metadata, not waveforms, events or decisions.
Output: results/tdh2023/disjoint_check.json.  Usage: python analysis/tdh2023/verify_disjoint.py <bucket_listing.txt>
"""
import os, re, sys, json, glob, datetime as dt
import csv

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UNITS = "AE AG AU AV BW C0 C1 CN EE ET FN HC HE HL IV IW JP KR MB ND NE NM NS NY OH OK PL RV SI UO UU UW WW".split() + ["A2", "CA", "OT"]
SPAN = (dt.date(2023, 5, 25), dt.date(2023, 8, 30))      # detector tuning week of A2/CA/OT + the 90-day window, end exclusive
WIN = ("2023-06-01", "2023-08-30")
OUT = os.path.join(root, "results", "tdh2023"); os.makedirs(OUT, exist_ok=True)


def d(s):
    try: return dt.date.fromisoformat(str(s)[:10])
    except Exception: return None


def overlaps(a, b):
    return a is not None and b is not None and a < SPAN[1] and b > SPAN[0]


touched = {u: [] for u in UNITS}; other_nets = {}
n_status = n_summary = n_avail = 0
for f in glob.glob(os.path.join(root, "results", "**", "status.json"), recursive=True):
    try: s = json.load(open(f, encoding="utf-8"))
    except Exception: continue
    n_status += 1
    nets = sorted({v[0] for v in (s.get("stations") or {}).values() if isinstance(v, list) and v})
    per = []
    for key in ("tune", "eval"):
        v = s.get(key)
        if isinstance(v, list) and len(v) == 2: per.append((key, d(v[0]), d(v[1])))
    for n in nets:
        for key, a, b in per:
            rec = {"source": os.path.relpath(f, root), "kind": key, "from": str(a), "to": str(b), "overlaps_span": overlaps(a, b)}
            (touched[n] if n in touched else other_nets.setdefault(n, [])).append(rec)
for f in glob.glob(os.path.join(root, "results", "**", "summary.json"), recursive=True):
    try: s = json.load(open(f, encoding="utf-8"))
    except Exception: continue
    n_summary += 1
    nets = sorted({i.split(".")[0] for v in (s.get("channel_ids") or {}).values() for i in v})
    p = s.get("params") or {}
    for key in ("tune", "dev"):
        v = p.get(key)
        if isinstance(v, list) and len(v) == 2:
            a, b = d(v[0]), d(v[1])
            for n in nets:
                rec = {"source": os.path.relpath(f, root), "kind": key, "from": str(a), "to": str(b), "overlaps_span": overlaps(a, b)}
                (touched[n] if n in touched else other_nets.setdefault(n, [])).append(rec)
avail_ranges = []
for f in glob.glob(os.path.join(root, "results", "**", "availability.csv"), recursive=True):
    try:
        days = [r["day"] for r in csv.DictReader(open(f, encoding="utf-8")) if r.get("day")]
    except Exception: continue
    if not days: continue
    n_avail += 1
    a, b = d(min(days)), d(max(days)) + dt.timedelta(days=1)
    avail_ranges.append({"source": os.path.relpath(f, root), "from": str(a), "to": str(b), "overlaps_span": overlaps(a, b)})
# network code of an availability.csv: the run dir name (results/.../<NET>/out_x/availability.csv) when it is a unit code
for r in avail_ranges:
    parts = r["source"].replace("\\", "/").split("/")
    for p in parts:
        base = p.split("_")[0]
        if base in touched and p not in ("out",):
            touched[base].append({**r, "kind": "availability.csv"}); break

# 2. bucket listing
bucket = {"listing_file": None, "objects": 0, "objects_with_2023_in_path": [], "unit_network_prefixes": {}}
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    lines = [l.strip() for l in open(sys.argv[1], encoding="utf-8-sig") if l.strip().startswith("gs://")]
    bucket["listing_file"] = os.path.basename(sys.argv[1]); bucket["objects"] = len(lines)
    bucket["objects_with_2023_in_path"] = [l for l in lines if "2023" in l]
    for u in UNITS:
        hits = [l for l in lines if re.search(rf"/{u}/", l) or re.search(rf"/{u}_EXT", l)]
        if hits:
            days = sorted({m.group(0) for l in hits for m in [re.search(r"20\d\d-?\d\d-?\d\d", l.split("/")[-1])] if m})
            bucket["unit_network_prefixes"][u] = {"objects": len(hits), "raw_mseed": sum(l.endswith(".mseed") for l in hits),
                                                   "dated_names_first_last": [days[0], days[-1]] if days else None}

# 3. plan files: ISO dates inside the span
plans = sorted(set(glob.glob(os.path.join(root, "PREREGISTRATION*.md")) + glob.glob(os.path.join(root, "PLAN*.md")) +
                   glob.glob(os.path.join(root, "SELECTION*.md")) + glob.glob(os.path.join(root, "ANALYSIS_PLAN*.md")) +
                   [os.path.join(root, "EXPERIMENT_LEDGER.md"), os.path.join(root, "MANIFEST.md")]))
plan_hits = []
for f in plans:
    if not os.path.exists(f) or os.path.basename(f).startswith("PLAN_TIME_DISJOINT_2023"): continue
    for i, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
        for m in re.finditer(r"\b(20\d\d)-(\d\d)-(\d\d)\b", line):
            x = d(m.group(0))
            if x and SPAN[0] <= x < SPAN[1]:
                plan_hits.append({"file": os.path.basename(f), "line": i, "date": m.group(0), "text": line.strip()[:220]})

# 4. selection metadata windows
sel = {}
for f in ("networks.json", "networks_batchB.json"):
    p = os.path.join(root, "results", "v2", f)
    for c in json.load(open(p, encoding="utf-8"))["networks"]:
        if c["network"] in touched: sel[c["network"]] = c.get("selection_window")
cand = json.load(open(os.path.join(root, "results", "v2", "selection", "candidates.json"), encoding="utf-8"))["candidates_passing"]
cand = cand if isinstance(cand, list) else list(cand.values())
for c in cand:
    if c.get("network") in ("A2", "CA", "OT"): sel[c["network"]] = c.get("window")

res = {"plan": "PLAN_TIME_DISJOINT_2023_2026-11-08.md", "checked_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
       "download_span_checked": [str(SPAN[0]), str(SPAN[1])], "window": WIN,
       "artefacts_scanned": {"status.json": n_status, "summary.json": n_summary, "availability.csv": n_avail, "plan_files": len(plans)},
       "units": {}, "bucket": bucket, "plan_file_dates_inside_span": plan_hits,
       "selection_metadata_windows": {u: sel.get(u) for u in UNITS},
       "note_selection_windows": "W1 = metadata (station epochs + daily availability) over 2023-07-01 .. 2024-07-08, read by "
                                 "analysis/v2_select_networks.py; no waveform, event or decision. W2 = 2024-01-01 .. 2025-01-08, W3 = 2024-07-01 .. 2025-07-09."}
for u in UNITS:
    recs = touched[u]
    lo = min((d(r["from"]) for r in recs if d(r["from"])), default=None); hi = max((d(r["to"]) for r in recs if d(r["to"])), default=None)
    res["units"][u] = {"records": len(recs), "earliest_day_touched": str(lo) if lo else None, "latest_day_touched": str(hi) if hi else None,
                       "any_overlap_with_span": any(r["overlaps_span"] for r in recs),
                       "bucket_objects": bucket["unit_network_prefixes"].get(u, {}).get("objects", 0),
                       "bucket_raw_mseed": bucket["unit_network_prefixes"].get(u, {}).get("raw_mseed", 0)}
res["all_disjoint"] = (not any(v["any_overlap_with_span"] for v in res["units"].values()) and not bucket["objects_with_2023_in_path"]
                       and not any(v["bucket_raw_mseed"] for v in res["units"].values()))
res["any_run_artefact_in_span_any_network"] = sorted({r["source"] for r in avail_ranges if r["overlaps_span"]})
json.dump(res, open(os.path.join(OUT, "disjoint_check.json"), "w"), indent=1)
print(json.dumps({"all_disjoint": res["all_disjoint"], "plan_hits": len(plan_hits), "bucket_objects": bucket["objects"],
                  "artefacts": res["artefacts_scanned"], "runs_in_span_any_network": res["any_run_artefact_in_span_any_network"][:10],
                  "units": {u: (v["earliest_day_touched"], v["latest_day_touched"], v["any_overlap_with_span"]) for u, v in res["units"].items()}}, indent=0))
