"""Run list of PREREGISTRATION_V2_EXT12_B_2026-11-08.md: the 31 batch-B networks included in the batch-B pooled analysis, evaluated
over the six months after the batch-B period (2024-07-08 .. 2025-01-08, exclusive) with the batch-B tuning week and the batch-B
frozen thresholds (no re-tuning). Stations, roles and sites are copied unchanged from results/v2/networks_batchB.json.
Writes results/v2/networks_ext12B.json.   python analysis/v2_ext12B_networks.py
"""
import os, json
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); V = os.path.join(root, "results", "v2")
EXT0, EXT1 = "2024-07-08", "2025-01-08"
B = json.load(open(os.path.join(V, "networks_batchB.json")))
inc = {n for n, r in json.load(open(os.path.join(V, "v2_eval_batchB.json")))["networks"].items() if r.get("included_in_pooled")}
nets = []
for c in B["networks"]:
    if c["network"] not in inc: continue
    e = dict(c)
    e["id"] = f'{c["network"]}_EXT12B'
    e["batch_B_rule_order"] = e.pop("rule_order", None)
    e["eval_start"], e["eval_end"] = EXT0, EXT1
    e["tune_start"], e["tune_end"] = B["period"]["tune_start"], B["period"]["eval_start"]
    e["thresholds"] = "frozen batch-B thresholds of this network (results/v2/runs/<NET>/status.json 'thresholds'); no re-tuning"
    e["output_dir"] = f'results/v2/runs_ext12B/{c["network"]}/'
    nets.append(e)
out = {"amendment": "Extension ext12B (PREREGISTRATION_V2_EXT12_B_2026-11-08.md): the 31 batch-B networks included in the batch-B "
                    "pooled analysis, evaluation 2024-07-08 .. 2025-01-08, batch-B tuning week and frozen batch-B thresholds",
       "period": {"tune_start": B["period"]["tune_start"], "tune_end_exclusive": B["period"]["eval_start"],
                  "eval_start": EXT0, "eval_end_exclusive": EXT1, "days": 184},
       "combined_period": {"eval_start": B["period"]["eval_start"], "eval_end_exclusive": EXT1, "days": 366},
       "networks": nets, "regions": sorted({p["region"] for p in nets})}
json.dump(out, open(os.path.join(V, "networks_ext12B.json"), "w"), indent=1)
print("ext12B", len(nets), "networks:", " ".join(p["id"] for p in nets))
