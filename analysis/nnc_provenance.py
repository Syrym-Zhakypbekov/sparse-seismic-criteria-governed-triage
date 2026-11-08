"""Provenance for the NNC analysis (review R6-M03). Re-requests the same 14 monthly ISC FDSN queries as code/15, keeps every
raw QuakeML response (results/nnc/raw/<month>.xml, sha256 + request URL + retrieval time in raw/manifest.json), and exports
per event: resource id, preferred origin id, origin agency / author, magnitude id and agency, event type and type certainty
as returned by ISC. Per associated episode: selected event id, predicted P, residual, number of qualifying candidates and
the ids of the alternatives. Checks that the event set equals results/nnc/nnc_events.csv (time match to 0.01 s).
"""
import os, json, time, hashlib, urllib.request
import numpy as np, pandas as pd
from obspy import UTCDateTime, read_events
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = os.path.join(root, "results", "nnc"); RAW = os.path.join(N, "raw"); os.makedirs(RAW, exist_ok=True)
REF = (46.808, 81.977); model = TauPyModel("iasp91"); man = {}; rows = []
m0 = UTCDateTime("2025-01-01")
while m0 < UTCDateTime("2026-03-01"):
    m1 = UTCDateTime(m0.year + (m0.month == 12), m0.month % 12 + 1, 1); tag = str(m0.date)[:7]
    url = (f"https://www.isc.ac.uk/fdsnws/event/1/query?starttime={m0.date}&endtime={m1.date}"
           f"&latitude={REF[0]}&longitude={REF[1]}&maxradius=6&contributor=NNC")
    fp = os.path.join(RAW, f"{tag}.xml")
    if not os.path.exists(fp):
        for att in range(6):
            try:
                data = urllib.request.urlopen(url, timeout=180).read(); open(fp, "wb").write(data); break
            except Exception as e:
                print(tag, "retry", att, str(e)[:80], flush=True); time.sleep(30 * (att + 1))
        man[tag] = {"url": url, "retrieved_utc": str(UTCDateTime()), "sha256": hashlib.sha256(open(fp, "rb").read()).hexdigest(), "bytes": os.path.getsize(fp)}
        time.sleep(5)
    cat = read_events(fp)
    for ev in cat:
        o = ev.preferred_origin() or ev.origins[0]; mg = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
        deg = gps2dist_azimuth(REF[0], REF[1], o.latitude, o.longitude)[0] / 111195
        arr = model.get_travel_times(source_depth_in_km=max((o.depth or 0) / 1000, 0), distance_in_degree=deg, phase_list=["p", "P", "Pn", "Pg"])
        ci = o.creation_info; mci = mg.creation_info if mg else None
        rows.append({"event_id": str(ev.resource_id), "origin_id": str(o.resource_id), "origin_agency": getattr(ci, "agency_id", None),
                     "origin_author": getattr(ci, "author", None), "magnitude_id": str(mg.resource_id) if mg else None,
                     "magnitude_agency": getattr(mci, "agency_id", None) if mci else None, "event_type": str(ev.event_type),
                     "event_type_certainty": str(ev.event_type_certainty), "time": float(o.time), "lat": o.latitude, "lon": o.longitude,
                     "depth_km": (o.depth or 0) / 1000, "mag": mg.mag if mg else np.nan, "dist_deg": deg,
                     "p_pred": float(o.time + min(a.time for a in arr)) if arr else np.nan, "month_file": f"raw/{tag}.xml"})
    print(tag, len(cat), flush=True); m0 = m1
old = json.load(open(os.path.join(RAW, "manifest.json"))) if os.path.exists(os.path.join(RAW, "manifest.json")) else {}
old.update(man)
ev = pd.DataFrame(rows)   # validated below BEFORE anything published is replaced
prev = pd.read_csv(os.path.join(N, "nnc_events.csv"))
a_ = prev.sort_values("time").reset_index(drop=True); b_ = ev.sort_values("time").reset_index(drop=True)
same = len(a_) == len(b_) and bool(np.all(np.abs(a_.time.to_numpy() - b_.time.to_numpy()) <= 0.01)) and        bool((a_.type.astype(str).to_numpy() == b_.event_type.astype(str).to_numpy()).all()) and        bool(np.allclose(a_[["lat", "lon", "p_pred"]].to_numpy(dtype=float), b_[["lat", "lon", "p_pred"]].to_numpy(dtype=float), rtol=0, atol=1e-6, equal_nan=True)) and        not ev.event_id.duplicated().any()
assert same, "refreshed NNC responses differ from results/nnc/nnc_events.csv: keep the published snapshot and report the difference"
json.dump(old, open(os.path.join(RAW, "manifest.json"), "w"), indent=1)
ev.to_csv(os.path.join(N, "nnc_events_provenance.csv"), index=False)
# episode -> event links
ep = pd.read_csv(os.path.join(N, "episodes_nnc.csv")); ep["t_on"] = [UTCDateTime(t).timestamp for t in ep.t_on_utc]
E = json.load(open(os.path.join(root, "results", "extended", "extended_eval.json")))
toff = pd.concat([pd.read_csv(os.path.join(root, c["source"], "episodes.csv"))[["t_on_utc", "t_off"]] for c in E["chunks"]]).drop_duplicates("t_on_utc").set_index("t_on_utc").t_off
ev = ev.dropna(subset=["p_pred"]).sort_values("p_pred").reset_index(drop=True); P = ev.p_pred.to_numpy(); links = []
for _, r in ep.iterrows():
    t1 = float(toff.get(r.t_on_utc, r.t_on)); lo, hi = np.searchsorted(P, r.t_on - 15), np.searchsorted(P, t1, side="right")
    if hi > lo:
        cand = list(range(lo, hi)); j = lo + int(np.argmin(np.abs(P[lo:hi] - r.t_on)))
        links.append({"t_on_utc": r.t_on_utc, "event_id": ev.event_id[j], "event_type": ev.event_type[j], "p_pred": P[j], "residual_s": P[j] - r.t_on,
                      "n_candidates": len(cand), "alternative_ids": ";".join(ev.event_id[k] for k in cand if k != j),
                      "alternative_types": ";".join(ev.event_type[k] for k in cand if k != j), "label_in_table10": r.nnc})
L = pd.DataFrame(links); L.to_csv(os.path.join(N, "episode_event_links.csv"), index=False)
summ = {"events": int(len(rows)), "same_event_set_as_nnc_events_csv": bool(same), "origin_agency_counts": ev.origin_agency.value_counts(dropna=False).to_dict(),
        "event_type_certainty_counts": ev.event_type_certainty.value_counts(dropna=False).to_dict(), "linked_episodes": int(len(L)),
        "links_with_alternatives": int((L.n_candidates > 1).sum()), "label_mismatch_vs_table10": int((L.event_type != L.label_in_table10).sum())}
json.dump(summ, open(os.path.join(N, "provenance_summary.json"), "w"), indent=1, default=str); print(json.dumps(summ, indent=1, default=str))
