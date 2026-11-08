"""Reviewed-bulletin scoring of the ext12B extension (PREREGISTRATION_V2_EXT12_B_2026-11-08.md, section 6).
Wraps analysis/v2_reviewed_bulletin.py unchanged (labels, matching rule, decisions, hypotheses) with:
- networks: the 31 ext12B networks; run tree results/v2/runs_ext12B (EXT) or runs + runs_ext12B (BEXT, combined);
- labels: ISC/ComCat for 2024-07-01 .. 2024-11-01 in results/v2_reviewed_ext12B/labels (completeness rule: the ISC Reviewed
  Bulletin is complete to 2024-11-01, so episodes on or after 2024-11-01 are unusable for reviewed scoring in every network);
  BEXT also reads the batch-B labels of results/v2_reviewed/labels;
- sensitivity FULLCOMCAT: full ext period for networks whose catalogue rows come from ComCat only (labelled as such).
    python analysis/v2_reviewed_ext12B.py download | score EXT | score BEXT | score FULLCOMCAT
"""
import os, sys, glob as _glob, json, importlib.util
import pandas as pd
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
spec = importlib.util.spec_from_file_location("rb", os.path.join(here, "v2_reviewed_bulletin.py")); rb = importlib.util.module_from_spec(spec); spec.loader.exec_module(rb)
v2 = rb.v2
NETS = [c["network"] for c in json.load(open(os.path.join(root, "results", "v2", "networks_ext12B.json")))["networks"]]
CUT = "2024-11-01"; CUT_TS = pd.Timestamp(CUT, tz="UTC").timestamp()
EXT_LAB = os.path.join(root, "results", "v2_reviewed_ext12B", "labels"); B_LAB = os.path.join(root, "results", "v2_reviewed", "labels")
MONTHS_REV = [("2024-07-01", "2024-08-01"), ("2024-08-01", "2024-09-01"), ("2024-09-01", "2024-10-01"), ("2024-10-01", "2024-11-01")]
MONTHS_FULL = MONTHS_REV + [("2024-11-01", "2024-12-01"), ("2024-12-01", "2025-01-09")]


def setup(mode):
    rb.NETS = NETS; rb.BATCH_A = set(); rb.HIGH_CHANCE = set()
    rb.LAB = EXT_LAB; rb.OUT = os.path.join(root, "results", "v2_reviewed_ext12B", mode)
    v2.RUN_DIRS[:] = ["runs", "runs_ext12B"] if mode == "BEXT" else ["runs_ext12B"]
    if mode == "BEXT":   # labels of both periods
        class G:
            @staticmethod
            def glob(p):
                return _glob.glob(p) + _glob.glob(p.replace(EXT_LAB, B_LAB))
        rb.glob = G
    orig = v2.load_network

    def load(net, cfg):
        got = orig(net, cfg)
        if got is None or got == "incomplete" or mode == "FULLCOMCAT": return got
        ep, av, cat, fails = got
        keep = ep.t_on.to_numpy(float) < CUT_TS
        return ep[keep].reset_index(drop=True), av[av.day < CUT], cat, fails
    v2.load_network = load
    if mode == "FULLCOMCAT":   # only networks whose catalogue rows are ComCat-only
        sel = []
        for n in NETS:
            fs = _glob.glob(os.path.join(root, "results", "v2", "runs_ext12B", n, "out_*", "catalog.csv"))
            if fs and all(set(pd.read_csv(f).source.unique()) <= {"USGS"} for f in fs): sel.append(n)
        rb.NETS = sel; print("ComCat-only networks:", sel)


if __name__ == "__main__":
    if sys.argv[1] == "download":
        rb.NETS = NETS; rb.LAB = EXT_LAB; rb.MONTHS = MONTHS_FULL; rb.download()
    else:
        setup(sys.argv[2]); rb.score()
