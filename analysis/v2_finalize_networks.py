"""Amendment A1 of SELECTION_RULE_V2_2026-11-08.md (PREREGISTRATION_V2_NETWORKS_2026-11-08.md, section 4), written before any
data: fixed compute budget -> uniform 6-month period and 10 networks. Reads results/v2/selection/{chosen.json, candidates.json}
(metadata-only output of analysis/v2_select_networks.py) and writes results/v2/networks.json, the run list read by the fleet.
- Period for every network: tuning 2024-01-01 .. 2024-01-08, evaluation 2024-01-08 .. 2024-07-08 (182 days). Only networks whose
  passing configuration is in window W1 or W2 are eligible (their stream epochs cover 2024-01-01 .. 2024-07-08 by construction);
  W3-only networks: "eligible, period not covered by metadata".
- 10 networks by the pushed rule's ranking (section 6 key) and round-robin over regions (section 7), cap 10 instead of 24.
- Every other passing network: "eligible, not run (compute budget)".
"""
import os, json
from urllib.parse import urlparse

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(root, "results", "v2", "selection")
TUNE, EV0, EV1 = "2024-01-01", "2024-01-08", "2024-07-08"
cand = json.load(open(os.path.join(S, "candidates.json")))["candidates_passing"]
chosen24 = [c["network"] for c in json.load(open(os.path.join(S, "chosen.json")))["chosen"]]
# rebuild the ranking key exactly as in v2_select_networks.py section 6
def key(c):
    so = c["site_outage_days"]
    return (-int(c["pair"]), -min(so[0], 60), -min(sum(so), 120), -c["reference_good_day_share"], c["reference"])

region_of = {}
for c in json.load(open(os.path.join(S, "chosen.json")))["chosen"]: region_of[c["network"]] = c["region"]
import importlib.util
src = open(os.path.join(root, "analysis", "v2_select_networks.py"), encoding="utf-8").read()
fn = src[src.index("def region(lat, lon):"):src.index("byreg = {}")]
ns = {}; exec(fn, ns); region = ns["region"]

elig, other = {}, {}
for net, c in cand.items():
    c = dict(c); c["region"] = region(c["lat"], c["lon"])
    (elig if c["window"] in ("W1", "W2") else other)[net] = c
byreg = {}
for c in elig.values(): byreg.setdefault(c["region"], []).append(c)
for r in byreg.values(): r.sort(key=key)
order = sorted(byreg, key=lambda r: key(byreg[r][0]))
# full rule order: round-robin over regions (regions ordered by their best candidate), within a region by the ranking key
full, i = [], 0
while any(i < len(byreg[r]) for r in order):
    for r in order:
        if i < len(byreg[r]): full.append(byreg[r][i])
    i += 1
pick = full[:10]                 # batch A (amendment A1), unchanged
batchB = full[10:]               # batch B (PREREGISTRATION_V2_BATCHB_2026-11-08.md): every remaining eligible network, same order


def base(ds):
    u = urlparse(ds); return "" if "earthscope" in u.netloc else f"{u.scheme}://{u.netloc}"


def entry(c, k_rule):
    return {"rule_order": k_rule, "network": c["network"], "region": c["region"], "datacentre": c["datacentre"], "dataselect": c["dataselect"],
                 "fdsn_base": base(c["dataselect"]), "reference_stream": c["reference_stream"], "lat": c["lat"], "lon": c["lon"],
                 "selection_window": c["window"], "site_outage_days_in_selection_window": c["site_outage_days"],
                 "reference_good_day_share": c["reference_good_day_share"], "has_merged_pair": c["pair"],
                 "sites": [{"rank": k + 1, "dist_km": s["dist_km"], "members": s["members"]} for k, s in enumerate(c["sites"])],
                 "tune_start": TUNE, "eval_start": EV0, "eval_end": EV1,
                 "roles": {"MAKZ": c["reference_stream"], **{f"S{k + 1}_{j + 1}": m["stream"] for k, s in enumerate(c["sites"]) for j, m in enumerate(s["members"])}}}


nets = []
for c in pick:
    e = entry(c, None); e.pop("rule_order"); nets.append(e)   # networks.json keeps its pushed format byte-identical
out = {"amendment": "A1 (compute budget): uniform 6-month period, 10 networks; written before any data",
       "period": {"tune_start": TUNE, "eval_start": EV0, "eval_end_exclusive": EV1, "days": 182},
       "networks": nets,
       "eligible_not_run_compute_budget": sorted(n for n in elig if n not in [p["network"] for p in pick]),
       "eligible_period_not_covered": sorted(other),
       "regions": sorted({p["region"] for p in pick})}
json.dump(out, open(os.path.join(root, "results", "v2", "networks.json"), "w"), indent=1)
for p in nets:
    print(p["region"], "|", p["network"], p["datacentre"], p["reference_stream"], "| sites:",
          "; ".join(",".join(f"{m['stream']} {m['dist_km']}" for m in s["members"]) for s in p["sites"]), "| outage", p["site_outage_days_in_selection_window"])
print("regions", len(out["regions"]), "eligible not run", len(out["eligible_not_run_compute_budget"]), "W3 only", len(other))

# batch B run list (same format as networks.json, plus rule_order = position in the full rule order, 11 = first of batch B)
netsB = [entry(c, 11 + k) for k, c in enumerate(batchB)]
outB = {"amendment": "Batch B (PREREGISTRATION_V2_BATCHB_2026-11-08.md): every eligible network not in batch A, same rule v2, same period; "
                     "written after batch A started and before any batch-B data; compute order = rule_order",
        "period": out["period"],
        "networks": netsB,
        "batch_A": [p["network"] for p in pick],
        "eligible_period_not_covered": sorted(other),
        "regions": sorted({p["region"] for p in netsB})}
json.dump(outB, open(os.path.join(root, "results", "v2", "networks_batchB.json"), "w"), indent=1)
print("batch B", len(netsB), "networks in", len(outB["regions"]), "regions:", ", ".join(f'{p["rule_order"]}:{p["network"]}' for p in netsB))

# Extension ext12 (PREREGISTRATION_V2_EXT12_2026-11-08.md): the batch-A networks that passed tuning, evaluated over the six months
# following the batch-A period (2024-07-08 .. 2025-01-08), with the batch-A tuning week and the batch-A frozen thresholds (no
# re-tuning). Batch-A networks not run (tuning week without data) are excluded; the list is taken from results/v2/FLEET_DEVIATIONS.md
# (section "Not run"), written before any batch-A result was opened. networks.json and networks_batchB.json stay byte-identical.
EXT0, EXT1 = "2024-07-08", "2025-01-08"
NOT_RUN_A = ["AB", "AF", "AW"]   # FLEET_DEVIATIONS.md: tuning failed (NaN threshold, data centre answered no-data on all tuning days)
netsE = []
for k, c in enumerate(pick):
    if c["network"] in NOT_RUN_A: continue
    e = entry(c, k + 1)
    e["id"] = f'{c["network"]}_EXT12'
    e["batch_A_rule_order"] = e.pop("rule_order")
    e["eval_start"], e["eval_end"] = EXT0, EXT1
    e["tune_end"] = EV0
    e["thresholds"] = "frozen batch-A thresholds of this network (results/v2/runs/<NET>/status.json 'thresholds'); no re-tuning"
    e["output_dir"] = f'results/v2/runs_ext12/{c["network"]}/'
    e["period_covered_by_selection_metadata"] = c["window"] == "W2"
    netsE.append(e)
outE = {"amendment": "Extension ext12 (PREREGISTRATION_V2_EXT12_2026-11-08.md): batch-A networks that passed tuning, evaluation "
                     "2024-07-08 .. 2025-01-08 (six months after the batch-A period), batch-A tuning week 2024-01-01 .. 2024-01-08 and "
                     "batch-A frozen thresholds; written after batch A started and before any batch-A or batch-B result was opened; "
                     "queued after batch B",
        "period": {"tune_start": TUNE, "tune_end_exclusive": EV0, "eval_start": EXT0, "eval_end_exclusive": EXT1, "days": 184},
        "combined_period": {"eval_start": EV0, "eval_end_exclusive": EXT1, "days": 366},
        "networks": netsE,
        "batch_A_not_run_excluded": NOT_RUN_A,
        "regions": sorted({p["region"] for p in netsE})}
json.dump(outE, open(os.path.join(root, "results", "v2", "networks_ext12.json"), "w"), indent=1)
print("ext12", len(netsE), "networks:", ", ".join(p["id"] for p in netsE))
