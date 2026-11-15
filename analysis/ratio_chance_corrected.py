"""Ratio criterion after chance correction (POST HOC, cold review v34, Fable finding 1).

The pre-specified reviewed-bulletin test (PLAN_REVIEWED_BULLETIN, criteria B2/B3) has two parts: the pooled
difference in dismissed reviewed-associated alarms (upper 95% bound <= 3 points) and the ratio of dismissals
rule / P3 (upper 95% bound <= 1.5). The chance-corrected DIFFERENCE was reported (results/gap/gap_reviewed.json G2);
this script computes the chance-corrected RATIO from the same existing outputs, without new data or new decisions:

  corrected ratio = sum_n (D_k,n - chance_k,n) / sum_n (D_P3,n - chance_P3,n)

with two chance estimators already on disk:
  A  shifted-catalogue control  results/posthoc/chance_by_policy.json  (sets.reviewed.per_network)
  B  per-episode Poisson        results/posthoc/chance_per_episode_33net.json (per_network.*.rules)
Uncertainty: the same network bootstrap as G2 (2000 resamples of the 33 networks, seed 7, analysis/v2_networks.py
NBOOT/SEED), percentile interval. Also reported: corrected dismissals, the 3-point margin in units of corrected
reviewed-associated alarms, and the share of resamples with a non-positive corrected P3 count (ratio undefined).

Usage: python analysis/ratio_chance_corrected.py  -> results/posthoc/ratio_chance_corrected.json
"""
import os, json
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
P = os.path.join(root, "results", "posthoc")
NB, SEED = 2000, 7          # analysis/v2_networks.py NBOOT, SEED
POL = ["CG", "CG-D", "CG_c05"]


def load_A():
    d = json.load(open(os.path.join(P, "chance_by_policy.json")))["sets"]["reviewed"]["per_network"]
    return {n: {"assoc": x["assoc"], "chance_assoc": x["chance_assoc"],
                "D": {k: x["dismissed"][k] for k in POL + ["P3"]},
                "C": {k: x["chance_dismissed"][k] for k in POL + ["P3"]}} for n, x in d.items()}


def load_B():
    d = json.load(open(os.path.join(P, "chance_per_episode_33net.json")))["per_network"]
    out = {}
    for n, x in d.items():
        r = x["rules"]
        out[n] = {"assoc": x["reviewed_associated"], "chance_assoc": x["sum_p_all_episodes"],
                  "D": {k: r[k]["dismissed_assoc_raw"] for k in POL + ["P3"]},
                  "C": {k: r[k]["expected_chance_among_dismissed"] for k in POL + ["P3"]}}
    return out


def analyse(d, label, source):
    names = sorted(d); rng = np.random.default_rng(SEED)
    draws = [rng.choice(names, len(names)) for _ in range(NB)]

    def sums(ks, k):
        return (sum(d[n]["D"][k] for n in ks), sum(d[n]["C"][k] for n in ks))

    def ratio(ks, k):
        dk, ck = sums(ks, k); dp, cp = sums(ks, "P3")
        den = dp - cp
        return (dk - ck) / den if den > 0 else np.nan

    tot_a = sum(d[n]["assoc"] for n in names); tot_ca = sum(d[n]["chance_assoc"] for n in names)
    corr_den = tot_a - tot_ca
    dp, cp = sums(names, "P3")
    o = {"source": source, "networks": len(names), "reviewed_associated": tot_a,
         "chance_associated_expected": round(tot_ca, 2), "corrected_reviewed_associated": round(corr_den, 2),
         "margin_3pp_in_corrected_alarms": round(0.03 * corr_den, 1),
         "P3": {"dismissed": dp, "chance_expected": round(cp, 2), "corrected_dismissed": round(dp - cp, 2),
                "negative_corrected_networks": [n for n in names if d[n]["D"]["P3"] - d[n]["C"]["P3"] < 0]}}
    for k in POL:
        dk, ck = sums(names, k)
        v = np.array([ratio(ks, k) for ks in draws]); ok = np.isfinite(v)
        lo, hi = (float(np.percentile(v[ok], 2.5)), float(np.percentile(v[ok], 97.5))) if ok.any() else (None, None)
        raw_ratio = dk / dp
        o[k] = {"dismissed": dk, "chance_expected": round(ck, 2), "corrected_dismissed": round(dk - ck, 2),
                "corrected_excess_over_P3": round((dk - ck) - (dp - cp), 2),
                "raw_ratio": round(raw_ratio, 3),
                "corrected_ratio": round(ratio(names, k), 3),
                "corrected_ratio_ci95": [round(lo, 3), round(hi, 3)] if lo is not None else None,
                "resamples_ratio_undefined": int((~ok).sum()),
                "ratio_criterion_upper_le_1_5": bool(hi is not None and hi <= 1.5)}
    return o


def main():
    res = {"status": "POST HOC (cold review v34_7f6b540, Fable finding 1); computed from existing outputs, no new "
                     "decisions; not a pre-specified test",
           "criterion": "pre-specified ratio criterion: upper 95% bound of dismissals rule/P3 <= 1.5 (B2/B3, V1r/R1r)",
           "bootstrap": {"resamples": NB, "seed": SEED, "unit": "network (33), percentile interval, as G2 in "
                         "results/gap/gap_reviewed.json"},
           "A_shifted_catalogue": analyse(load_A(), "A", "results/posthoc/chance_by_policy.json"),
           "B_per_episode": analyse(load_B(), "B", "results/posthoc/chance_per_episode_33net.json")}
    os.makedirs(P, exist_ok=True)
    json.dump(res, open(os.path.join(P, "ratio_chance_corrected.json"), "w"), indent=1)
    for e in ("A_shifted_catalogue", "B_per_episode"):
        r = res[e]; print(e, "P3 corrected", r["P3"]["corrected_dismissed"], "margin", r["margin_3pp_in_corrected_alarms"])
        for k in POL:
            print("  ", k, r[k]["corrected_ratio"], r[k]["corrected_ratio_ci95"], "undef", r[k]["resamples_ratio_undefined"],
                  "excess", r[k]["corrected_excess_over_P3"])


if __name__ == "__main__":
    main()
