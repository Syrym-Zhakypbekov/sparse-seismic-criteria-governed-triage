"""Unit tests of the rule-v2 merge and the scorer helpers on SYNTHETIC votes (no data). Run: python -m pytest analysis/test_v2_networks.py"""
import os, sys, importlib.util
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("v2", os.path.join(here, "v2_networks.py")); v2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)


def test_merge_truth_table():
    a = np.array(["YES", "YES", "YES", "NO", "NO", "MISSING", "MISSING", "NO", "MISSING"], dtype=object)
    b = np.array(["YES", "NO", "MISSING", "YES", "NO", "YES", "NO", "MISSING", "MISSING"], dtype=object)
    site, = v2.merge_sites({"x": a, "y": b}, [["x", "y"]])
    assert list(site) == ["YES", "YES", "YES", "YES", "NO", "YES", "NO", "NO", "MISSING"]


def test_singleton_site_unchanged():
    a = np.array(["YES", "NO", "MISSING"], dtype=object)
    site, = v2.merge_sites({"x": a}, [["x"]])
    assert list(site) == list(a)


def test_greedy_grouping_50km():
    # seed at 0 deg lon; 0.3 deg (~33 km) joins; 0.6 deg (~67 km from seed) seeds a new site even though 33 km from the second
    roles = [("A", 100, (0.0, 0.0)), ("B", 110, (0.0, 0.3)), ("C", 120, (0.0, 0.6)), ("D", 400, (3.0, 0.0))]
    assert v2.group_by_distance(roles) == [["A", "B"], ["C"], ["D"]]


def test_merged_pair_counts_once():
    # two co-located NO votes: v1 (separate, 0.25 + 0.20) dismisses, v2 (one site 0.25) with a far YES does not
    n = 1; snr = np.array([3.0]); ok = np.array([True])
    near1 = np.array(["NO"], dtype=object); near2 = np.array(["NO"], dtype=object); far = np.array(["YES"], dtype=object)
    v1 = v2.policies([near1, near2, far], snr, ok)["CG"][0]
    S = v2.merge_sites({"a": near1, "b": near2, "c": far}, [["a", "b"], ["c"]])
    new = v2.policies(S, snr, ok)["CG"][0]
    # v1: num = 0.15*1 + 0.4*0.1 = 0.19, den = 0.25+0.20+0.15+0.40 = 1.0 -> D = 0.19 > 0.16 -> E ; v2: num = 0.20 + 0.04, den = 0.85 -> 0.28 -> E
    assert v1 == "E" and new == "E"
    S2 = v2.merge_sites({"a": near1, "b": near2}, [["a", "b"]])
    assert v2.policies(S2, snr, ok)["CG"][0] == "D"          # 0.04 / 0.65 = 0.06 <= 0.16


def test_p3_unchanged_by_merge():
    rng = np.random.default_rng(1); n = 500
    st = {k: rng.choice(["YES", "NO", "MISSING"], n).astype(object) for k in "abcd"}
    snr = rng.uniform(0, 20, n); ok = rng.random(n) > 0.1
    v1 = v2.policies([st["a"], st["b"], st["c"]], snr, ok)
    S = v2.merge_sites(st, [["a", "b"], ["c"], ["d"]])
    new = v2.policies(S, snr, ok)
    d4 = v2.policies([st["a"], st["b"], st["c"], st["d"]][:3], snr, ok)
    yes_any = (S[0] == "YES") | (S[1] == "YES") | (S[2] == "YES")
    assert ((new["P3"] == "A") == (yes_any & ok & (snr >= 7.5))).all()
    assert set(np.unique(new["CG"])) <= {"A", "D", "E"}


def test_holm_and_cluster_boot():
    h = v2.holm({"x": 0.01, "y": 0.04, "z": 0.03})
    assert h == {"x": 0.03, "z": 0.06, "y": 0.06}
    rng = np.random.default_rng(3); nets = {}
    for k in range(4):
        n = 300; days = np.array([f"2024-01-{1 + i % 20:02d}" for i in range(n)]); assoc = rng.random(n) < 0.3
        a = np.where(rng.random(n) < 0.05, "D", "E").astype(object); nets[f"N{k}"] = (days, assoc, {"CG": a, "P3": a.copy()})
    r = v2.cluster_boot(nets, "CG", "P3", n=200)
    assert r["pooled_diff_pp"] == 0.0 and r["pooled_noninferior"] and abs(r["ratio"] - 1.0) < 1e-9


if __name__ == "__main__":
    for f in [v for k, v in dict(globals()).items() if k.startswith("test_")]: f()
    print("all tests passed")
