"""Scoring of PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md (pushed dffacba, 2026-11-08T04:40:20Z, before any label).

download: for each of the 38 networks, the ISC FDSN events (QuakeML, preferred origin only) and USGS ComCat events (GeoJSON,
status) in the pipeline's own query circle (reference station, 15 deg, M >= 2) over the evaluation period, plus ComCat global
M >= 5.5 for teleseismic rows -> results/v2_reviewed/labels/, sha256 in labels/SHA256.txt.
score: every catalogue row of results/v2/runs/<NET>/out_*/catalog.csv labelled REVIEWED / NOT REVIEWED (source, |dt| <= 2 s,
<= 0.5 deg, nearest in time); episodes re-associated with v2_networks.assoc_vec on REVIEWED rows; the frozen decisions of
v2_networks.evaluate_network are scored on these labels -> results/v2_reviewed/v2_eval_reviewed.json + v2_reviewed_table.md.
Only the association flags and the catalogue given to the chance control change; no decision rule changes.
"""
import os, sys, re, json, glob, time, hashlib, math, importlib.util, urllib.request, urllib.error, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
spec = importlib.util.spec_from_file_location("v2", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
V = os.path.join(root, "results", "v2"); OUT = os.path.join(root, "results", "v2_reviewed"); LAB = os.path.join(OUT, "labels")
NETS = "AE AG AU AV BW C0 C1 CN CO EE ET FN HC HE HL IV IW JP KR MB N4 ND NE NM NS NY OH OK PE PL QZ RV SI TX UO UU UW WW".split()
BATCH_A = set("AU AV C1 IV JP KR OH".split()); HIGH_CHANCE = {"JP"}
MONTHS = [("2024-01-07", "2024-02-01"), ("2024-02-01", "2024-03-01"), ("2024-03-01", "2024-04-01"), ("2024-04-01", "2024-05-01"),
          ("2024-05-01", "2024-06-01"), ("2024-06-01", "2024-07-01"), ("2024-07-01", "2024-07-09")]
ISC = "http://www.isc.ac.uk/fdsnws/event/1/query"; USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def cfgs():
    out = {}
    for f in ("networks.json", "networks_batchB.json"):
        for c in json.load(open(os.path.join(V, f)))["networks"]: out[c["network"]] = c
    return out


def ref(net):
    s = json.load(open(os.path.join(V, "runs", net, "status.json")))["stations"]["MAKZ"]; return s[4], s[5]


def get(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "p10-research"}), timeout=300) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 204: return 204, b""
            time.sleep(10 * (k + 1))
        except Exception:
            time.sleep(10 * (k + 1))
    raise RuntimeError("failed: " + url)


def dl_one(job):
    kind, net, lat, lon, t0, t1 = job
    fn = os.path.join(LAB, f"{kind}_{net}_{t0}.{'xml' if kind == 'ISC' else 'json'}")
    if os.path.exists(fn) and os.path.getsize(fn) > 0: return fn
    if kind == "ISC":
        url = f"{ISC}?starttime={t0}T00:00:00&endtime={t1}T00:00:00&latitude={lat}&longitude={lon}&maxradius=15&minmagnitude=2"
    elif kind == "USGS":
        url = f"{USGS}?format=geojson&starttime={t0}&endtime={t1}&latitude={lat}&longitude={lon}&maxradius=15&minmagnitude=2"
    else:
        url = f"{USGS}?format=geojson&starttime={t0}&endtime={t1}&minmagnitude=5.5"
    st, b = get(url); open(fn + ".tmp", "wb").write(b); os.replace(fn + ".tmp", fn); return fn


def download():
    os.makedirs(LAB, exist_ok=True); jobs = []
    for n in NETS:
        la, lo = ref(n)
        for t0, t1 in MONTHS: jobs += [("ISC", n, la, lo, t0, t1), ("USGS", n, la, lo, t0, t1)]
    jobs += [("TELE", "ALL", 0, 0, t0, t1) for t0, t1 in MONTHS]
    isc = [j for j in jobs if j[0] == "ISC"]; other = [j for j in jobs if j[0] != "ISC"]
    with ThreadPoolExecutor(6) as ex: list(ex.map(dl_one, other))
    with ThreadPoolExecutor(2) as ex:
        for i, f in enumerate(ex.map(dl_one, isc)): print("ISC", i + 1, len(isc), os.path.basename(f), flush=True)
    with open(os.path.join(LAB, "SHA256.txt"), "w") as h:
        for f in sorted(glob.glob(os.path.join(LAB, "*.*"))):
            if f.endswith("SHA256.txt"): continue
            h.write(hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + os.path.basename(f) + "\n")
    print("download done", len(jobs))


def parse_isc(fn):
    s = open(fn, encoding="utf-8", errors="replace").read(); rows = []
    for ev in re.findall(r"<event .*?</event>", s, re.S):
        m = re.search(r"<preferredOriginID>(.*?)</preferredOriginID>", ev)
        if not m: continue
        o = re.search(r'<origin publicID="' + re.escape(m.group(1)) + r'".*?</origin>', ev, re.S)
        if not o: continue
        o = o.group(0)
        t = re.search(r"<time>\s*<value>(.*?)</value>", o); la = re.search(r"<latitude>\s*<value>(.*?)</value>", o); lo = re.search(r"<longitude>\s*<value>(.*?)</value>", o)
        if not (t and la and lo): continue
        stt = re.search(r"<evaluationStatus>(.*?)</evaluationStatus>", o)
        rows.append((pd.Timestamp(t.group(1).rstrip("Z"), tz="UTC").timestamp(), float(la.group(1)), float(lo.group(1)),
                     (stt.group(1) if stt else "") == "reviewed"))
    return rows


def parse_usgs(fn):
    d = json.load(open(fn)); return [(f["properties"]["time"] / 1000.0, f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0],
                                     f["properties"].get("status") == "reviewed") for f in d.get("features", [])]


def label_rows(cat, bull, src):
    """cat rows of one source -> (reviewed flag, matched flag). bull: array (t, lat, lon, reviewed) sorted by t."""
    rev = np.zeros(len(cat), bool); hit = np.zeros(len(cat), bool)
    if not len(bull) or not len(cat): return rev, hit
    bt = bull[:, 0]
    for i, (t, la, lo) in enumerate(zip(cat.time.to_numpy(float), cat.lat.to_numpy(float), cat.lon.to_numpy(float))):
        a, b = np.searchsorted(bt, t - 2.0), np.searchsorted(bt, t + 2.0, side="right")
        best = None
        for j in range(a, b):
            if abs(bull[j, 1] - la) <= 0.5 and abs(((bull[j, 2] - lo + 180) % 360) - 180) <= 0.5 / max(math.cos(math.radians(la)), 0.1) * 1.0 + 1e-9:
                if best is None or abs(bt[j] - t) < abs(bt[best] - t): best = j
        if best is not None: hit[i] = True; rev[i] = bool(bull[best, 3])
    return rev, hit


def arr(rows):
    a = np.array(rows, float) if rows else np.zeros((0, 4)); return a[np.argsort(a[:, 0])] if len(a) else a


def score():
    C = cfgs(); tele = arr([r for f in glob.glob(os.path.join(LAB, "TELE_ALL_*.json")) for r in parse_usgs(f)])
    out = {"preregistration": "PREREGISTRATION_REVIEWED_BULLETIN_38NET_2026-11-08.md (dffacba)", "networks": {}}
    data_all, outage_all = {}, {}
    orig_load = v2.load_network
    for n in NETS:
        isc = arr([r for f in glob.glob(os.path.join(LAB, f"ISC_{n}_*.xml")) for r in parse_isc(f)])
        usg = arr([r for f in glob.glob(os.path.join(LAB, f"USGS_{n}_*.json")) for r in parse_usgs(f)])
        info = {}

        def load(net, cfg, _n=n, _isc=isc, _usg=usg, _info=info):
            got = orig_load(net, cfg)
            if got is None or got == "incomplete": return got
            ep, av, cat, fails = got
            cat = cat.reset_index(drop=True); rev = np.zeros(len(cat), bool); hit = np.zeros(len(cat), bool)
            for src, bull in (("ISC", _isc), ("USGS", None)):
                m = (cat.source == src).to_numpy()
                if src == "USGS":
                    for kind, b in (("regional", _usg), ("tele", tele)):
                        mm = m & (cat.kind == kind).to_numpy(); r, h = label_rows(cat[mm], b, src); rev[mm] = r; hit[mm] = h
                else:
                    r, h = label_rows(cat[m], bull, src); rev[m] = r; hit[m] = h
            t_on, t_off = ep.t_on.to_numpy(), ep.t_off.to_numpy()
            stored = (ep.assoc_event >= 0).to_numpy(); recomputed = v2.assoc_vec(cat.p_pred.to_numpy(float), t_on, t_off)
            agree = float((stored == recomputed).mean()) if len(ep) else 1.0
            ra = v2.assoc_vec(cat.p_pred.to_numpy(float)[rev], t_on, t_off)
            _info.update({"catalogue_rows": int(len(cat)), "rows_reviewed": int(rev.sum()), "rows_matched": int(hit.sum()),
                          "rows_by_source_reviewed": {s: [int(((cat.source == s).to_numpy() & rev).sum()), int((cat.source == s).sum())] for s in ("ISC", "USGS")},
                          "selfcheck_assoc_agreement": round(agree, 5), "episodes_assoc_catalogue": int(stored.sum()),
                          "episodes_reviewed_associated": int(ra.sum())})
            if agree < 0.995: raise SystemExit(f"self-check failed {_n}: agreement {agree}")
            ep = ep.copy(); ep["assoc_event"] = np.where(ra, 0, -1)
            return ep, av, cat[rev].reset_index(drop=True), fails

        v2.load_network = load
        r = v2.evaluate_network(n, C[n]); v2.load_network = orig_load
        if isinstance(r, dict): out["networks"][n] = {**r, **info}; continue
        res, data, outage = r; res.update(info); res["batch"] = "A" if n in BATCH_A else "B"
        out["networks"][n] = res
        if res["included_in_pooled"]: data_all[n] = data
        outage_all[n] = res["outage_nearest_site"]
        print(n, info, "included", res["included_in_pooled"], flush=True)

    def pooled(sel):
        d = {k: v for k, v in data_all.items() if k in sel}
        if not d: return {"networks": 0}
        o = {"R1_CG_minus_P3": v2.cluster_boot(d, "CG", "P3"), "R2_CGD_minus_P3": v2.cluster_boot(d, "CG-D", "P3"),
             "R3_CGc05_minus_P3": v2.cluster_boot(d, "CG_c05", "P3"), "CG_v2_minus_v1": v2.cluster_boot(d, "CG", "CG_v1"),
             "per_network_holm_CG_minus_P3": v2.holm({k: out["networks"][k]["H_noninferiority"]["CG-P3"]["p_one_sided_H0_ge_margin"] for k in d})}
        op = {"assoc": 0, "CG": 0, "P1": 0, "networks": 0}
        for k in sel:
            if k not in outage_all: continue
            q = outage_all[k]
            if q["CG"]["assoc"]: op["networks"] += 1; op["assoc"] += q["CG"]["assoc"]; op["CG"] += q["CG"]["dismissed_assoc"]; op["P1"] += q["P1"]["dismissed_assoc"]
        ex = op["assoc"] >= 10 and op["networks"] >= 2
        o["R7_outage"] = {**op, "exercised": ex, "holds": (op["CG"] < op["P1"]) if ex else None}
        o["V6_unassoc_alerts"] = {p: int(sum(out["networks"][k]["H_unassoc_alerts"][p] for k in d)) for p in ("CG", "P3", "P1t")}
        return o

    out["PRIMARY_all38"] = pooled(set(NETS))
    out["SECONDARY_without_high_chance"] = pooled(set(NETS) - HIGH_CHANCE)
    out["batch_A"] = pooled(BATCH_A); out["batch_B"] = pooled(set(NETS) - BATCH_A)
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "v2_eval_reviewed.json"), "w"), indent=1, default=str)
    L = ["| network | batch | rows reviewed / all | ISC rev/all | USGS rev/all | episodes assoc (catalogue) | reviewed-assoc | included | CG−P3 pp [95%] | Holm p | chance share (reviewed) |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    holm = out["PRIMARY_all38"].get("per_network_holm_CG_minus_P3", {})
    for n in NETS:
        r = out["networks"][n]
        if "H_noninferiority" not in r: L.append(f"| {n} | {'A' if n in BATCH_A else 'B'} | {r.get('status','')} |||||||||"); continue
        h = r["H_noninferiority"]["CG-P3"]; cc = r["chance_control"]; ra = r["episodes_reviewed_associated"]
        L.append(f"| {n} | {r['batch']} | {r['rows_reviewed']}/{r['catalogue_rows']} | {r['rows_by_source_reviewed']['ISC'][0]}/{r['rows_by_source_reviewed']['ISC'][1]} | "
                 f"{r['rows_by_source_reviewed']['USGS'][0]}/{r['rows_by_source_reviewed']['USGS'][1]} | {r['episodes_assoc_catalogue']} | {ra} | {r['included_in_pooled']} | "
                 f"{h['diff_pp']} {h['ci95_pp']} | {holm.get(n, '-')} | {round(cc['chance_associated_mean'] / ra, 3) if ra else '-'} |")
    open(os.path.join(OUT, "v2_reviewed_table.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "networks"}, indent=1, default=str))


if __name__ == "__main__":
    {"download": download, "score": score}[sys.argv[1]]()
