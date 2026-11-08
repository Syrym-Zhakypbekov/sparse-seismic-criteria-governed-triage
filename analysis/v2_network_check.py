"""Per-network check of the rule-v2 fleet runs (descriptive, no hypothesis; written 08.11.2026 after the runs, before reading
any score). Reads results/v2/runs[_ext12]/<NET>/ (status.json, out_*/{episodes,availability,catalog,summary}) and, when present,
the scorer outputs v2_eval_batchA.json / v2_eval_batchB.json / v2_eval_ext12.json (inclusion flag, chance control).
Writes results/v2/network_check.json and the table part of results/v2/NETWORK_CHECK.md (between the AUTO markers).
    python analysis/v2_network_check.py
Columns: platform, state, period covered by availability, calendar days, episodes, associated, association rate, catalogue
regional / teleseismic events per day (catalogue rows the pipeline kept for this reference), outage days per site (site share =
largest member valid share < 0.10, as the scorer's V7), days with every site < 0.10, merged sites, chance-associated share
(scorer's shifted catalogue, mean chance-associated / associated), automatic flags."""
import os, json, glob
import numpy as np, pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(root, "results", "v2")


def lists():
    out = []
    for f, b in [("networks.json", "A"), ("networks_batchB.json", "B"), ("networks_ext12.json", "EXT12")]:
        for i, c in enumerate(json.load(open(os.path.join(V, f)))["networks"]):
            c = dict(c); c.setdefault("rule_order", c.get("batch_A_rule_order", i + 1)); out.append((b, c))
    return out


def evals():
    e = {}
    for b, f in [("A", "v2_eval_batchA.json"), ("B", "v2_eval_batchB.json"), ("EXT12", "v2_eval_ext12.json")]:
        p = os.path.join(V, f)
        e[b] = json.load(open(p))["networks"] if os.path.exists(p) else {}
    return e


def one(batch, cfg, ev):
    net = cfg["network"]; d = os.path.join(V, "runs_ext12" if batch == "EXT12" else "runs", net)
    st = json.load(open(os.path.join(d, "status.json"))) if os.path.exists(os.path.join(d, "status.json")) else {}
    row = {"batch": batch, "network": net, "rule_order": cfg.get("rule_order", cfg.get("batch_A_rule_order")),
           "region": cfg["region"], "datacentre": cfg["datacentre"], "lat": cfg["lat"], "lon": cfg["lon"],
           "reference": cfg["reference_stream"], "platform": st.get("platform"), "state": st.get("state", "no status.json"),
           "merged_sites": [[m["stream"] for m in s["members"]] for s in cfg["sites"] if len(s["members"]) > 1],
           "site_dist_km": [s["dist_km"] for s in cfg["sites"]]}
    dirs = sorted(glob.glob(os.path.join(d, "out_*")))
    ok = [x for x in dirs if os.path.exists(os.path.join(x, "summary.json")) and os.path.exists(os.path.join(x, "episodes.csv"))]
    row["chunks_planned"] = len(st.get("chunk_plan", [])) or None; row["chunks_done"] = len(ok)
    if not ok: return row
    ep = pd.concat([pd.read_csv(os.path.join(x, "episodes.csv")) for x in ok], ignore_index=True)
    av = pd.concat([pd.read_csv(os.path.join(x, "availability.csv")) for x in ok]).drop_duplicates("day").sort_values("day")
    cat = pd.concat([pd.read_csv(os.path.join(x, "catalog.csv")) for x in ok], ignore_index=True)
    summ = [json.load(open(os.path.join(x, "summary.json"))) for x in ok]
    nd = len(av); assoc = int((ep.assoc_event >= 0).sum())
    row.update({"period": [av.day.min(), av.day.max()], "calendar_days": nd, "episodes": len(ep), "associated": assoc,
                "association_rate": round(assoc / max(len(ep), 1), 4),
                "catalogue_regional_per_day": round(float((cat.kind == "regional").sum()) / max(nd, 1), 2),
                "catalogue_tele_per_day": round(float((cat.kind != "regional").sum()) / max(nd, 1), 2),
                "catalogue_failures": sorted({f for s in summ for f in s.get("catalog_failures", [])}),
                "fetch_failures": sum(len(s.get("fetch_failures", [])) for s in summ),
                "reference_valid_share_mean": round(float(av["MAKZ_valid_share"].mean()), 3),
                "reference_days_lt10": int((av["MAKZ_valid_share"] < 0.10).sum())})
    shares = []
    for i, s in enumerate(cfg["sites"]):
        roles = [f"S{i + 1}_{j + 1}" for j in range(len(s["members"]))]
        shares.append(av[[f"{r}_valid_share" for r in roles]].max(axis=1).to_numpy())
    row["site_outage_days_lt10"] = [int((x < 0.10).sum()) for x in shares]
    row["days_all_sites_lt10"] = int(np.all([x < 0.10 for x in shares], axis=0).sum())
    e = ev.get(batch, {}).get(net)
    if isinstance(e, dict) and "chance_control" in e:
        cc = e["chance_control"]; row["chance_associated_mean"] = cc["chance_associated_mean"]
        row["chance_share"] = round(cc["chance_associated_mean"] / max(assoc, 1), 3)
        row["chance_corrected_CG_minus_P3_pp"] = cc["chance_corrected_CG_minus_P3_pp"]
        row["included_in_pooled_by_scorer"] = e["included_in_pooled"]
    flags = []
    if row["catalogue_regional_per_day"] < 0.2: flags.append("near-zero regional catalogue (<0.2/day)")
    if assoc < 30: flags.append("fewer than 30 associated episodes (pre-registered exclusion)")
    if row["catalogue_failures"]: flags.append("catalogue failure in a chunk")
    for i, x in enumerate(shares):
        if (x < 0.10).mean() > 0.9: flags.append(f"site {i + 1} missing on >90% of days")
    if row["reference_days_lt10"] > 0.5 * nd: flags.append("reference <10% valid on most days")
    if row.get("chance_share", 0) > 0.5: flags.append("chance-associated share > 0.5")
    if row["chunks_planned"] and row["chunks_done"] < row["chunks_planned"]: flags.append("not every chunk finished")
    row["auto_flags"] = flags
    return row


def main():
    ev = evals(); rows = [one(b, c, ev) for b, c in lists()]
    json.dump(rows, open(os.path.join(V, "network_check.json"), "w"), indent=1, default=str)
    H = ["batch", "#", "network", "region (label)", "lat, lon", "data centre", "platform", "state", "period", "days", "episodes",
         "assoc", "assoc rate", "cat reg/day", "cat tele/day", "site outage days <10%", "all sites <10% days", "merged sites",
         "chance share", "scorer included", "auto flags"]
    L = ["| " + " | ".join(H) + " |", "|" + "---|" * len(H)]
    for r in rows:
        L.append("| " + " | ".join(str(x) for x in [
            r["batch"], r["rule_order"], r["network"], r["region"], f"{r['lat']:.2f}, {r['lon']:.2f}", r["datacentre"],
            r.get("platform"), r["state"], " .. ".join(r["period"]) if r.get("period") else "-", r.get("calendar_days", "-"),
            r.get("episodes", "-"), r.get("associated", "-"), r.get("association_rate", "-"), r.get("catalogue_regional_per_day", "-"),
            r.get("catalogue_tele_per_day", "-"), r.get("site_outage_days_lt10", "-"), r.get("days_all_sites_lt10", "-"),
            "; ".join("+".join(m) for m in r["merged_sites"]) or "none", r.get("chance_share", "-"),
            r.get("included_in_pooled_by_scorer", "-"), "; ".join(r.get("auto_flags", [])) or "-"]) + " |")
    p = os.path.join(V, "NETWORK_CHECK.md"); txt = open(p, encoding="utf-8").read() if os.path.exists(p) else "<!-- AUTO -->\n<!-- /AUTO -->\n"
    a, b = txt.split("<!-- AUTO -->")[0], txt.split("<!-- /AUTO -->")[1]
    open(p, "w", encoding="utf-8").write(a + "<!-- AUTO -->\n" + "\n".join(L) + "\n<!-- /AUTO -->" + b)
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
