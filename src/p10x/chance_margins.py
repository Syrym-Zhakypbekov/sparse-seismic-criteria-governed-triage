"""P10X-05 (registry v4-P10, 9063f88): chance-corrected non-inferiority at margins 1, 2, 3, 5 pp on the 33 reviewed networks.
Estimator A (shifted catalogue, primary) and B (per-episode Poisson). Network bootstrap 2000, seed 7 (as gap_reviewed G2).
Output: results/p10x/chance_margins.json, results/registry/P10X-05a/b/c.json."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

P = os.path.join(P10, "results", "posthoc")
POL = ["CG", "CG_c05", "CG-D"]; MARGINS = [1.0, 2.0, 3.0, 5.0]


def load_A():
    d = json.load(open(os.path.join(P, "chance_by_policy.json")))["sets"]["reviewed"]["per_network"]
    return {n: {"assoc": x["assoc"], "ca": x["chance_assoc"], "D": x["dismissed"], "C": x["chance_dismissed"]} for n, x in d.items()}


def load_B():
    d = json.load(open(os.path.join(P, "chance_per_episode_33net.json")))["per_network"]
    return {n: {"assoc": x["reviewed_associated"], "ca": x["sum_p_all_episodes"],
                "D": {k: x["rules"][k]["dismissed_assoc_raw"] for k in POL + ["P3"]},
                "C": {k: x["rules"][k]["expected_chance_among_dismissed"] for k in POL + ["P3"]}} for n, x in d.items()}


def analyse(d):
    names = sorted(d); rng = np.random.default_rng(SEED); draws = [rng.choice(names, len(names)) for _ in range(NB)]

    def diff(ks, k):
        num = den = 0.0
        for n in ks:
            x = d[n]; den += x["assoc"] - x["ca"]; num += (x["D"][k] - x["C"][k]) - (x["D"]["P3"] - x["C"]["P3"])
        return num / den * 100

    def ratio(ks, k):
        a = sum(d[n]["D"][k] - d[n]["C"][k] for n in ks); b = sum(d[n]["D"]["P3"] - d[n]["C"]["P3"] for n in ks)
        return a / b if b > 0 else np.nan

    out = {"networks": len(names)}
    for k in POL:
        v = np.array([diff(ks, k) for ks in draws]); r = np.array([ratio(ks, k) for ks in draws]); okr = np.isfinite(r)
        o = {"diff_pp": round(diff(names, k), 3), "ci95": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]}
        o["margins"] = {f"{m:g}": {"p_one_sided": float(((v >= m).sum() + 1) / (len(v) + 1)),
                                   "verdict": verdict([(o["diff_pp"], o["ci95"][1], m)])} for m in MARGINS}
        o["ratio"] = round(ratio(names, k), 3)
        o["ratio_ci95"] = [round(float(np.percentile(r[okr], 2.5)), 3), round(float(np.percentile(r[okr], 97.5)), 3)]
        o["ratio_undefined_resamples"] = int((~okr).sum()); o["ratio_le_1_5"] = bool(o["ratio_ci95"][1] <= 1.5)
        out[k] = o
    return out


res = {"A_shifted_catalogue_primary": analyse(load_A()), "B_per_episode": analyse(load_B()),
       "inputs_sha256": {"chance_by_policy.json": sha(os.path.join(P, "chance_by_policy.json")),
                         "chance_per_episode_33net.json": sha(os.path.join(P, "chance_per_episode_33net.json"))}}
g2 = json.load(open(os.path.join(P10, "results", "gap", "gap_reviewed.json")))["G2_chance_corrected"]
res["selfcheck_vs_G2"] = {k: [res["A_shifted_catalogue_primary"][k]["diff_pp"], res["A_shifted_catalogue_primary"][k]["ci95"], g2[k]["chance_corrected_diff_pp"], g2[k]["ci95_pp"]] for k in POL}
dump(os.path.join(OUT, "chance_margins.json"), res)
print(json.dumps(res["selfcheck_vs_G2"]))
for sub, k in (("a", "CG"), ("b", "CG_c05"), ("c", "CG-D")):
    A = res["A_shifted_catalogue_primary"][k]; B = res["B_per_episode"][k]
    dump(os.path.join(REG, f"P10X-05{sub}.json"), {
        "family": "F-P10X", "id": f"P10X-05{sub}", "chain": "B",
        "data": "33 reviewed-bulletin networks (P10 a97d376), chance_by_policy.json (A) and chance_per_episode_33net.json (B)",
        "metric": f"chance-corrected {k} - P3 dismissed share of reviewed-associated (pp), estimator A, network bootstrap 2000 seed 7",
        "est": A["diff_pp"], "ci": A["ci95"], "p": A["margins"]["3"]["p_one_sided"],
        "verdict_unadjusted": A["margins"]["3"]["verdict"], "verdict": None,
        "verdicts_by_margin_A": {m: A["margins"][m]["verdict"] for m in A["margins"]},
        "estimator_B": {"est": B["diff_pp"], "ci": B["ci95"], "verdicts_by_margin": {m: B["margins"][m]["verdict"] for m in B["margins"]}},
        "corrected_ratio_A": {"est": A["ratio"], "ci": A["ratio_ci95"], "undefined": A["ratio_undefined_resamples"], "le_1_5": A["ratio_le_1_5"]},
        "corrected_ratio_B": {"est": B["ratio"], "ci": B["ratio_ci95"], "undefined": B["ratio_undefined_resamples"], "le_1_5": B["ratio_le_1_5"]},
        "note": "Re-computation from existing chance outputs; the 3-pp verdict for estimator A was already published (gap_reviewed G2) and the other "
                "margins follow arithmetically from that interval; not independent confirmation. Final verdict after Holm (holm.py)."})
