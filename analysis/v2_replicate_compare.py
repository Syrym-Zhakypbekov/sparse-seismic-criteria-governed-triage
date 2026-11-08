"""Compare two runs of the same network (unplanned TX replicate, 08.11.2026: p10-fleet-3 = scored, laptop = replicate).
    python analysis/v2_replicate_compare.py TX results/v2/runs/TX results/v2/_replicate_TX_laptop/TX
Reports thresholds, per-chunk file hashes, episode/association counts, episode-level identity and actions per policy under rule v2
(policies of analysis/v2_networks.py, unchanged). Output: results/v2/replicate_<NET>.json (descriptive, no hypothesis)."""
import os, sys, json, glob, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_networks as S

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cfg_of(net):
    for f in ("networks.json", "networks_batchB.json"):
        for c in json.load(open(os.path.join(root, "results", "v2", f)))["networks"]:
            if c["network"] == net: return c


def load(d):
    dirs = sorted(glob.glob(os.path.join(d, "out_*")))
    ep = pd.concat([pd.read_csv(os.path.join(x, "episodes.csv")) for x in dirs], ignore_index=True)
    st = json.load(open(os.path.join(d, "status.json")))
    files = {}
    for x in dirs:
        for f in ("episodes.csv", "availability.csv", "catalog.csv"):
            raw = open(os.path.join(x, f), "rb").read()
            files[os.path.basename(x) + "/" + f] = (hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest())
    return ep, st, files


def actions(ep, cfg):
    sites = [[f"S{i + 1}_{j + 1}" for j in range(len(s["members"]))] for i, s in enumerate(cfg["sites"])]
    st = {r: ep[f"n_{r}"].astype(str).to_numpy() for s in sites for r in s}
    snr = ep.snr_db.fillna(0).to_numpy(); ok = ep.snr_db.notna().to_numpy()
    return S.policies(S.merge_sites(st, sites), snr, ok)


def main(net, a, b):
    cfg = cfg_of(net); (ea, sa, fa), (eb, sb, fb) = load(a), load(b)
    out = {"network": net, "run_a": {"dir": a, "platform": sa.get("platform"), "host": sa.get("host"), "state": sa.get("state")},
           "run_b": {"dir": b, "platform": sb.get("platform"), "host": sb.get("host"), "state": sb.get("state")},
           "thresholds_identical": sa.get("thresholds") == sb.get("thresholds"),
           "thresholds": {"a": sa.get("thresholds"), "b": sb.get("thresholds")},
           "files_byte_identical": {k: (fa.get(k) or [None])[0] == (fb.get(k) or [None])[0] for k in sorted(set(fa) | set(fb))},
           "files_identical_ignoring_line_endings": {k: (fa.get(k) or [None, None])[1] == (fb.get(k) or [None, None])[1] for k in sorted(set(fa) | set(fb))},
           "max_abs_threshold_diff": max(abs(sa["thresholds"][r] - sb["thresholds"][r]) for r in sa["thresholds"]) if sa.get("thresholds") and sb.get("thresholds") else None,
           "episodes": [len(ea), len(eb)], "associated": [int((ea.assoc_event >= 0).sum()), int((eb.assoc_event >= 0).sum())]}
    key = ["t_on", "t_off"]
    m = ea.merge(eb, on=key, how="outer", suffixes=("_a", "_b"), indicator=True)
    out["episodes_only_a"] = int((m._merge == "left_only").sum()); out["episodes_only_b"] = int((m._merge == "right_only").sum())
    both = m[m._merge == "both"]
    cols = [c[:-2] for c in m.columns if c.endswith("_a") and c[:-2] + "_b" in m.columns]
    diff = {}
    for c in cols:
        x, y = both[c + "_a"], both[c + "_b"]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            d = int((~np.isclose(x.fillna(-9e9), y.fillna(-9e9), rtol=0, atol=1e-9)).sum())
        else:
            d = int((x.astype(object).fillna("").astype(str).to_numpy() != y.astype(object).fillna("").astype(str).to_numpy()).sum())
        if d: diff[c] = d
    out["matched_episodes"] = int(len(both)); out["columns_differing_on_matched"] = diff
    aa, ab = actions(ea, cfg), actions(eb, cfg)
    asa, asb = (ea.assoc_event >= 0).to_numpy(), (eb.assoc_event >= 0).to_numpy()
    out["actions"] = {k: {"a": {x: int((aa[k] == x).sum()) for x in "ADE"}, "b": {x: int((ab[k] == x).sum()) for x in "ADE"},
                          "dismissed_assoc": [int(((aa[k] == "D") & asa).sum()), int(((ab[k] == "D") & asb).sum())]} for k in aa}
    out["max_abs_diff_numeric_on_matched"] = {c: float(np.nanmax(np.abs(both[c + "_a"].to_numpy(float) - both[c + "_b"].to_numpy(float))))
                                               for c in cols if pd.api.types.is_numeric_dtype(both[c + "_a"]) and len(both)}
    cat = {}
    for x in sorted(glob.glob(os.path.join(a, "out_*"))):
        ca = pd.read_csv(os.path.join(x, "catalog.csv")); cb = pd.read_csv(os.path.join(b, os.path.basename(x), "catalog.csv"))
        r = {"rows": [len(ca), len(cb)]}
        if len(ca) == len(cb) and list(ca.columns) == list(cb.columns):
            for c in ca.columns:
                if pd.api.types.is_float_dtype(ca[c]): r[c] = float(np.nanmax(np.abs(ca[c].to_numpy() - cb[c].to_numpy())) if len(ca) else 0.0)
                else: r[c] = int((ca[c].astype(object).fillna("").astype(str).to_numpy() != cb[c].astype(object).fillna("").astype(str).to_numpy()).sum())
        cat[os.path.basename(x)] = r
    out["catalog_max_abs_diff_or_mismatches"] = cat
    out["actions_identical"] =all(out["actions"][k]["a"] == out["actions"][k]["b"] for k in out["actions"])
    out["identical_all"] = bool(out["thresholds_identical"] and all(out["files_byte_identical"].values()))
    p = os.path.join(root, "results", "v2", f"replicate_{net}.json"); json.dump(out, open(p, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "actions"}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:4])
