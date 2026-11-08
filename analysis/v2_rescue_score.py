"""Scoring of PREREGISTRATION_V2_RESCUE_2026-11-08.md (post hoc extension; the 38-network primary results are unchanged).

Rescue networks: AB AF AW C CU EI FR KO O2 PQ S1 US (tuning failed in batch A/B), CZ (merge defect), SC (not completed).
Outputs of the rescue runs: results/v2/runs_rescue/<NET>/. Scored with the frozen scorer analysis/v2_networks.py (rules, margin,
bootstrap, seed, inclusion >= 30 associated episodes unchanged) and with the reviewed-bulletin labelling of
analysis/v2_reviewed_bulletin.py (same matching rule; labels of the rescue networks in results/v2_rescue/labels/).
Sets: RESCUE (rescued networks that pass inclusion) and ALL = the 38 primary networks + RESCUE (post hoc sensitivity).
  python analysis/v2_rescue_score.py download   # reviewed-bulletin labels of the rescued networks (after their runs)
  python analysis/v2_rescue_score.py score      # -> results/v2_rescue/v2_eval_rescue.json, v2_rescue_table.md
"""
import os, sys, json, glob, hashlib, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(here, fn)); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
rb = _load("rb", "v2_reviewed_bulletin.py"); v2 = rb.v2
V = os.path.join(root, "results", "v2"); OUT = os.path.join(root, "results", "v2_rescue"); LAB_R = os.path.join(OUT, "labels")
RESCUE = "AB AF AW C CU EI FR KO O2 PQ S1 US CZ SC".split()
PRIMARY = rb.NETS


def rescued():
    out = []
    for n in RESCUE:
        f = os.path.join(V, "runs_rescue", n, "status.json")
        if os.path.exists(f) and json.load(open(f)).get("state") == "done": out.append(n)
    return out


def ref_rescue(n):
    s = json.load(open(os.path.join(V, "runs_rescue", n, "status.json")))["stations"]["MAKZ"]; return s[4], s[5]


def download():
    os.makedirs(LAB_R, exist_ok=True); rb.LAB = LAB_R; jobs = []
    for n in rescued():
        la, lo = ref_rescue(n)
        for t0, t1 in rb.MONTHS: jobs += [("ISC", n, la, lo, t0, t1), ("USGS", n, la, lo, t0, t1)]
    jobs += [("TELE", "ALL", 0, 0, t0, t1) for t0, t1 in rb.MONTHS]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex: list(ex.map(rb.dl_one, [j for j in jobs if j[0] != "ISC"]))
    with ThreadPoolExecutor(2) as ex: list(ex.map(rb.dl_one, [j for j in jobs if j[0] == "ISC"]))
    with open(os.path.join(LAB_R, "SHA256.txt"), "w") as h:
        for f in sorted(glob.glob(os.path.join(LAB_R, "*.*"))):
            if not f.endswith("SHA256.txt"): h.write(hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + os.path.basename(f) + "\n")
    print("download done", len(jobs))


def cfgs():
    c = rb.cfgs(); return c


def eval_catalogue(n, cfg, rundir):
    v2.RUN_DIRS[:] = [rundir]
    try: return v2.evaluate_network(n, cfg)
    finally: v2.RUN_DIRS[:] = ["runs"]


def eval_reviewed(n, cfg, rundir, labdir, tele):
    isc = rb.arr([r for f in glob.glob(os.path.join(labdir, f"ISC_{n}_*.xml")) for r in rb.parse_isc(f)])
    usg = rb.arr([r for f in glob.glob(os.path.join(labdir, f"USGS_{n}_*.json")) for r in rb.parse_usgs(f)])
    orig = v2.load_network; info = {}

    def load(net, c):
        got = orig(net, c)
        if got is None or got == "incomplete": return got
        ep, av, cat, fails = got
        cat = cat.reset_index(drop=True); rev = np.zeros(len(cat), bool)
        m = (cat.source == "ISC").to_numpy(); r, _ = rb.label_rows(cat[m], isc, "ISC"); rev[m] = r
        mu = (cat.source == "USGS").to_numpy()
        for kind, b in (("regional", usg), ("tele", tele)):
            mm = mu & (cat.kind == kind).to_numpy(); r, _ = rb.label_rows(cat[mm], b, "USGS"); rev[mm] = r
        ra = v2.assoc_vec(cat.p_pred.to_numpy(float)[rev], ep.t_on.to_numpy(), ep.t_off.to_numpy())
        info.update({"rows_reviewed": int(rev.sum()), "catalogue_rows": int(len(cat)), "episodes_reviewed_associated": int(ra.sum())})
        ep = ep.copy(); ep["assoc_event"] = np.where(ra, 0, -1)
        return ep, av, cat[rev].reset_index(drop=True), fails

    v2.load_network = load; v2.RUN_DIRS[:] = [rundir]
    try: r = v2.evaluate_network(n, cfg)
    finally: v2.load_network = orig; v2.RUN_DIRS[:] = ["runs"]
    return r, info


def pooled(data, outage, nets, res):
    d = {k: v for k, v in data.items() if k in nets}
    if not d: return {"networks": 0}
    o = {"CG_minus_P3": v2.cluster_boot(d, "CG", "P3"), "CGD_minus_P3": v2.cluster_boot(d, "CG-D", "P3"),
         "CGc05_minus_P3": v2.cluster_boot(d, "CG_c05", "P3"), "CG_v2_minus_v1": v2.cluster_boot(d, "CG", "CG_v1"),
         "per_network_holm_CG_minus_P3": v2.holm({k: res[k]["H_noninferiority"]["CG-P3"]["p_one_sided_H0_ge_margin"] for k in d})}
    op = {"assoc": 0, "CG": 0, "P1": 0, "networks": 0}
    for k in nets:
        q = outage.get(k)
        if q and q["CG"]["assoc"]: op["networks"] += 1; op["assoc"] += q["CG"]["assoc"]; op["CG"] += q["CG"]["dismissed_assoc"]; op["P1"] += q["P1"]["dismissed_assoc"]
    ex = op["assoc"] >= 10 and op["networks"] >= 2
    o["outage"] = {**op, "exercised": ex, "holds": (op["CG"] < op["P1"]) if ex else None}
    return o


def score():
    C = cfgs(); os.makedirs(OUT, exist_ok=True)
    tele_p = rb.arr([r for f in glob.glob(os.path.join(rb.LAB, "TELE_ALL_*.json")) for r in rb.parse_usgs(f)])
    tele_r = rb.arr([r for f in glob.glob(os.path.join(LAB_R, "TELE_ALL_*.json")) for r in rb.parse_usgs(f)])
    out = {"plan": "PREREGISTRATION_V2_RESCUE_2026-11-08.md (post hoc extension)", "rescue_status": {}, "catalogue": {}, "reviewed": {}}
    for n in RESCUE:
        f = os.path.join(V, "runs_rescue", n, "status.json")
        s = json.load(open(f)) if os.path.exists(f) else {}
        out["rescue_status"][n] = {k: s.get(k) for k in ("state", "tune", "eval", "platform", "started_utc", "finished_utc", "rescue_window_try", "rate_fix")}
    resc = rescued()
    for mode in ("catalogue", "reviewed"):
        data, outage, res = {}, {}, {}
        for n in PRIMARY + resc:
            rundir = "runs" if n in PRIMARY else "runs_rescue"
            if mode == "catalogue":
                r = eval_catalogue(n, C[n], rundir); info = {}
            else:
                r, info = eval_reviewed(n, C[n], rundir, rb.LAB if n in PRIMARY else LAB_R, tele_p if n in PRIMARY else tele_r)
            if isinstance(r, dict): res[n] = {**r, **info}; continue
            rr, dd, oo = r; rr.update(info); res[n] = rr
            if rr["included_in_pooled"]: data[n] = dd
            outage[n] = rr["outage_nearest_site"]
        inc_r = [n for n in resc if n in data]
        out[mode] = {"rescued_networks_included": inc_r,
                     "RESCUE": pooled(data, outage, set(inc_r), res),
                     "ALL_primary_plus_rescue": pooled(data, outage, set(n for n in data), res),
                     "networks": {n: res[n] for n in resc}}
        print(mode, "rescued included", inc_r, flush=True)
    json.dump(out, open(os.path.join(OUT, "v2_eval_rescue.json"), "w"), indent=1, default=str)
    L = ["| network | state | tuning window | evaluation | episodes | assoc (catalogue) | reviewed-assoc | included (catalogue / reviewed) | CG−P3 pp catalogue | CG−P3 pp reviewed |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for n in RESCUE:
        st = out["rescue_status"][n]; rc = out["catalogue"]["networks"].get(n, {}); rv = out["reviewed"]["networks"].get(n, {})
        if st.get("state") != "done" and st.get("state") != "rescue_failed_thresholds": st = {**st, "tune": "-", "eval": "-"}
        f = lambda r: (f"{r['H_noninferiority']['CG-P3']['diff_pp']} {r['H_noninferiority']['CG-P3']['ci95_pp']}" if "H_noninferiority" in r else r.get("status", "-"))
        L.append(f"| {n} | {st.get('state')} | {st.get('tune')} | {st.get('eval')} | {rc.get('episodes', '-')} | {rc.get('associated', '-')} | "
                 f"{rv.get('episodes_reviewed_associated', '-')} | {rc.get('included_in_pooled', '-')} / {rv.get('included_in_pooled', '-')} | {f(rc) if rc else '-'} | {f(rv) if rv else '-'} |")
    open(os.path.join(OUT, "v2_rescue_table.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({m: {k: v for k, v in out[m].items() if k != "networks"} for m in ("catalogue", "reviewed")}, indent=1, default=str))


if __name__ == "__main__":
    {"download": download, "score": score}[sys.argv[1]]()
