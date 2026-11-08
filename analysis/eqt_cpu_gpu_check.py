"""Compare EQTransformer detection scores from the Colab GPU run (all extended-test episodes) with the
Google Cloud CPU repeat (first 3000 episodes). Writes results/eqt_extended/cpu_vs_gpu_check.json.

Run from the repository root:  python analysis/eqt_cpu_gpu_check.py
Inputs: results/eqt_extended/eqt_extended_episodes.csv (GPU), results/eqt_vm_cpu/eqt_extended_vm_cpu.csv (CPU).
Episodes are matched on (set, t_on); rows with an error on either side are excluded.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

root = sys.argv[1] if len(sys.argv) > 1 else "."
gpu = pd.read_csv(os.path.join(root, "results", "eqt_extended", "eqt_extended_episodes.csv"))
cpu = pd.read_csv(os.path.join(root, "results", "eqt_vm_cpu", "eqt_extended_vm_cpu.csv"))

key = ["set", "t_on"]
m = cpu.merge(gpu, on=key, suffixes=("_cpu", "_gpu"), how="inner")
ok = m["error_cpu"].isna() & m["error_gpu"].isna() & m["det_cpu"].notna() & m["det_gpu"].notna()
m = m[ok]
assert len(m) == len(cpu), f"unmatched CPU rows: {len(cpu) - len(m)}"

d = (m["det_cpu"] - m["det_gpu"]).abs()
res = {
    "episodes_compared": int(len(m)),
    "max_abs_diff_det": float(d.max()),
    "mean_abs_diff_det": float(d.mean()),
    "same_decision_at_0.5": float(((m["det_cpu"] >= 0.5) == (m["det_gpu"] >= 0.5)).mean()),
    "pearson": float(np.corrcoef(m["det_cpu"], m["det_gpu"])[0, 1]),
}
out = os.path.join(root, "results", "eqt_extended", "cpu_vs_gpu_check.json")
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1))
