"""Pre-specification timeline from GitHub's server-side push log (cannot be set by the author) against the start of
each processing run. Inputs: results/provenance/github_activity_raw.json (gh api repos/<repo>/activity, saved 07.11.2026)
and results/provenance/processing_start_times.json (VM file times, VM creation time, Kaggle version times, with sources).
Output: results/provenance/prespecification_timeline.json. Fails if any run started before its plan was pushed.
"""
import os, json
from datetime import datetime
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(root, "results", "provenance")
act = json.load(open(os.path.join(P, "github_activity_raw.json")))
push = {a["after"][:7]: a["timestamp"] for a in act if a["activity_type"] in ("push", "force_push")}
start = json.load(open(os.path.join(P, "processing_start_times.json")))
t = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
PAIRS = [("PREREGISTRATION (held-out)", "cc0b46f", ["heldout_kaggle_version_created"]),
         ("PREREGISTRATION_EXTENDED", "84e93ce", ["extended_MAKZ_vm_created", "extended_MAKZ_kaggle_2026h1_version_created"]),
         ("PREREGISTRATION_KURK_EXTENDED", "a53686d", ["kurk_extended_first_chunk"]),
         ("ANALYSIS_PLAN_NNC", "9ad4cc0", []),
         ("PREREGISTRATION_BLAST", "3f77906", ["blast_features"]),
         ("PREREGISTRATION_DETECTABILITY_2024", "3853469", ["y2024_MAKZ_first_chunk", "y2024_KURK_first_chunk"]),
         ("CG-D scorer 3e0f2f3 (D1-D4 computation)", "3e0f2f3", ["y2024_MAKZ_last_file", "y2024_KURK_last_file"]),
         ("CG-D scorer 133d6f1 (adds KZ scorer, NI_CG, ALLMISSING; D1-D4 unchanged)", "133d6f1", ["y2024_KURK_last_file"]),
         ("PREREGISTRATION_KZ_NETWORK", "f947bfa", ["kz_tuning_first_file"]),
         ("PREREGISTRATION_LEARNED_CRITERION", "d11004c", [])]
SCORERS = {"3e0f2f3", "133d6f1"}
rows, bad = [], []
for name, sha, keys in PAIRS:
    r = {"document": name, "commit": sha, "github_push_utc": push[sha], "runs": {}}
    for k in keys:
        s = int((t(start[k]) - t(push[sha])).total_seconds()); r["runs"][k] = {"time": start[k], "seconds_after_push": s}
        if s < 0 and sha not in SCORERS: bad.append((name, k, s))
    rows.append(r)
out = {"source": "GitHub repository activity API, server timestamps", "force_pushes": [(a["timestamp"], a["after"][:7]) for a in act if a["activity_type"] == "force_push"], "rows": rows, "plan_after_run": bad}
json.dump(out, open(os.path.join(P, "prespecification_timeline.json"), "w"), indent=1)
for r in rows: print(r["document"], r["github_push_utc"], {k: v["seconds_after_push"] for k, v in r["runs"].items()})
assert not bad, bad
print("OK: every plan was pushed before its run started")
