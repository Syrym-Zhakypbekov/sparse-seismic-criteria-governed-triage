"""PLAN_TIME_DISJOINT_2023_2026-11-08.md section 3: the run list results/tdh2023/networks_tdh2023.json.
- 33 reviewed-bulletin networks: frozen configuration (results/v2/networks.json / networks_batchB.json), roles and streams of
  results/v2/runs/<NET>/status.json (checked equal to analysis/v2_fleet/run_network.stations(cfg)), frozen detector thresholds of
  that status.json (no re-tuning), period 2023-06-01 .. 2023-08-30.
- Candidates: the configuration chosen in results/tdh2023/candidates_2023.json (result "included"); no frozen thresholds, so the
  detector is tuned on 2023-05-25 .. 05-31 (frozen procedure).
No network access."""
import os, sys, json, math, importlib.util
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("rn", os.path.join(root, "analysis", "v2_fleet", "run_network.py"))
rn = importlib.util.module_from_spec(spec); spec.loader.exec_module(rn)
UNITS = "AE AG AU AV BW C0 C1 CN EE ET FN HC HE HL IV IW JP KR MB ND NE NM NS NY OH OK PL RV SI UO UU UW WW".split()
EVAL = ("2023-06-01", "2023-08-30"); TUNE = "2023-05-25"
V = os.path.join(root, "results", "v2")
cfg = {}
for f in ("networks.json", "networks_batchB.json"):
    for c in json.load(open(os.path.join(V, f), encoding="utf-8"))["networks"]: cfg[c["network"]] = c
out = []
for n in UNITS:
    c = dict(cfg[n]); st = json.load(open(os.path.join(V, "runs", n, "status.json"), encoding="utf-8"))
    roles = rn.stations(c)
    assert {k: [str(x) for x in v] for k, v in roles.items()} == {k: [str(x) for x in v] for k, v in st["stations"].items()}, n
    thr = st["thresholds"]; assert set(thr) == set(roles) and all(math.isfinite(v) for v in thr.values()), n
    c.update({"id": f"{n}_TDH23", "eval_start": EVAL[0], "eval_end": EVAL[1], "tune_start": None, "frozen_thresholds": thr,
              "thresholds_source": f"results/v2/runs/{n}/status.json", "detector": "frozen (no re-tuning)", "unit": "reviewed-33"})
    out.append(c)
cand = json.load(open(os.path.join(root, "results", "tdh2023", "candidates_2023.json"), encoding="utf-8"))["candidates"]
excluded = {}
for n, r in sorted(cand.items()):
    if r.get("result") != "included": excluded[n] = r.get("result"); continue
    ch = r["chosen"]
    c = {"network": n, "id": f"{n}_TDH23", "datacentre": r["datacentre"], "dataselect": "https://service.earthscope.org/fdsnws/dataselect/1"
         if r["datacentre"] == "EarthScope" else None, "fdsn_base": "", "reference_stream": ch["reference_stream"], "lat": ch["lat"],
         "lon": ch["lon"], "sites": [{"rank": i + 1, **s} for i, s in enumerate(ch["sites"])], "selection_window": "T23",
         "eval_start": EVAL[0], "eval_end": EVAL[1], "tune_start": TUNE, "frozen_thresholds": None,
         "detector": "tuned once on 2023-05-25 .. 05-31 (frozen procedure)", "unit": "candidate"}
    assert r["datacentre"] == "EarthScope", "only EarthScope candidates are handled here"
    out.append(c)
json.dump({"plan": "PLAN_TIME_DISJOINT_2023_2026-11-08.md", "networks": out, "candidates_not_included": excluded},
          open(os.path.join(root, "results", "tdh2023", "networks_tdh2023.json"), "w"), indent=1)
print(len(out), [c["network"] for c in out], excluded)
