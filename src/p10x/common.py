"""Shared code for registry v4-P10 (plan/HYPOTHESIS_REGISTRY_V4_P10.md, commit 9063f88).

Reads the P10 repository read-only (C:/dev/p10-seismic-alarm-triage, HEAD a97d376). Rule constants are those of
analysis/v2_networks.py (frozen); nothing there is modified.
"""
import os, json, pickle, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
# In this archive the P10 data and the registry outputs live in the same repository (copied 15.11.2026 from
# criteria-governed-cross-domain/src/p10x, registry commit 9063f88); set P10_REPO to read another checkout.
P10 = os.environ.get("P10_REPO", REPO)
OUT = os.path.join(REPO, "results", "paper1", "p10x"); REG = os.path.join(REPO, "results", "registry")
W_RANK = [0.25, 0.20, 0.15]; W_SNR = 0.40; THETA_A, THETA_D, DELTA = 0.60, 0.16, 0.45
NB, SEED = 2000, 7
BATCH_A = {x["network"] for x in json.load(open(os.path.join(P10, "results/v2/networks.json")))["networks"]}
BATCH_B = {x["network"] for x in json.load(open(os.path.join(P10, "results/v2/networks_batchB.json")))["networks"]}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_reviewed():
    p = os.path.join(P10, "results/posthoc/_collect_reviewed.pkl")
    rows = pickle.load(open(p, "rb"))
    nets = sorted(k for k, v in rows.items() if v["included"])
    return rows, nets, sha(p)


def cg_score(S, snr, ok, c, delta=DELTA):
    """Score D and evidence mass den of rule v2 with constant discount c for a valid NO."""
    S = S[:3]; n = len(snr); num = np.zeros(n); den = np.zeros(n)
    for r, s in enumerate(S):
        q = np.isin(s, ["YES", "NO"]).astype(float); q = np.where(s == "NO", c, q)
        num += W_RANK[r] * (s == "YES") * q; den += W_RANK[r] * q
    num += W_SNR * np.clip(snr / 30, 0, 1) * ok; den += W_SNR * ok
    dd = den >= delta
    return np.where(dd, num / np.where(den > 0, den, 1), np.nan)


def act_from_D(D, td, ta):
    a = np.zeros(len(D), np.int8)                       # 0 escalate, 1 alert, -1 dismiss
    f = ~np.isnan(D); a[f & (D >= ta)] = 1; a[f & (D <= td)] = -1; return a


def anyyes(S):
    y = np.zeros(len(S[0]), bool)
    for s in S[:3]: y |= s == "YES"
    return y


def anymissing(S):
    m = np.zeros(len(S[0]), bool)
    for s in S[:3]: m |= s == "MISSING"
    return m


def p3_2t(yes, snr, ok, td, ta, miss=None):
    a = np.zeros(len(snr), np.int8); a[yes & ok & (snr >= ta)] = 1
    d = (~yes) & ok & (snr < td)
    if miss is not None: d &= ~miss                     # availability-aware: never dismiss with a missing site
    a[d] = -1; return a


def to_int(act):
    """frozen string actions -> int codes"""
    return np.where(act == "A", 1, np.where(act == "D", -1, 0)).astype(np.int8)


class DayTable:
    """Per network, per day-with-episodes counts for several action vectors (paired bootstrap on the same draws)."""

    def __init__(self, rows, nets, acts):
        # acts: {name: {net: int array}}
        self.nets = list(nets); self.names = list(acts)
        self.per = {}
        for k in self.nets:
            days = np.asarray(rows[k]["days"]); assoc = np.asarray(rows[k]["assoc"], bool)
            ud, inv = np.unique(days, return_inverse=True)
            m = {"assoc": np.bincount(inv, weights=assoc, minlength=len(ud))}
            for nm in self.names:
                a = acts[nm][k]
                m[nm + "|Da"] = np.bincount(inv, weights=(a == -1) & assoc, minlength=len(ud))
                m[nm + "|Au"] = np.bincount(inv, weights=(a == 1) & ~assoc, minlength=len(ud))
                m[nm + "|E"] = np.bincount(inv, weights=(a == 0), minlength=len(ud))
                m[nm + "|A"] = np.bincount(inv, weights=(a == 1), minlength=len(ud))
                m[nm + "|D"] = np.bincount(inv, weights=(a == -1), minlength=len(ud))
            self.per[k] = (len(ud), {kk: np.asarray(v, float) for kk, v in m.items()})

    def sums(self, draw):
        tot = {}; ndays = 0
        for k, idx in draw:
            nd, m = self.per[k]; ndays += len(idx)
            for kk, v in m.items(): tot[kk] = tot.get(kk, 0.0) + v[idx].sum()
        tot["days"] = ndays; return tot

    def full(self):
        return self.sums([(k, np.arange(self.per[k][0])) for k in self.nets])

    def boot(self, n=NB, seed=SEED):
        rng = np.random.default_rng(seed); out = []
        for _ in range(n):
            ks = rng.choice(self.nets, len(self.nets))
            out.append(self.sums([(k, rng.integers(0, self.per[k][0], self.per[k][0])) for k in ks]))
        return out


def contrast(full, boots, x, y, margin_pp=3.0, esc_ratio_max=1.10):
    def st(t):
        a = t["assoc"]; d = t["days"]
        return {"dism_pp": (t[x + "|Da"] - t[y + "|Da"]) / a * 100 if a else np.nan,
                "ua_per_nd": (t[x + "|Au"] - t[y + "|Au"]) / d,
                "esc_per_nd": (t[x + "|E"] - t[y + "|E"]) / d,
                "esc_ratio": t[x + "|E"] / t[y + "|E"] if t[y + "|E"] else np.nan,
                "dism_ratio": (t[x + "|Da"] + 0.5) / (t[y + "|Da"] + 0.5)}
    o = st(full); B = [st(b) for b in boots]
    res = {}
    for k in o:
        v = np.array([b[k] for b in B], float); v = v[np.isfinite(v)]
        res[k] = {"est": round(float(o[k]), 4), "ci": [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]}
    vd = np.array([b["dism_pp"] for b in B]); ve = np.array([b["esc_ratio"] for b in B])
    res["p_dism_ge_margin"] = float(((vd >= margin_pp).sum() + 1) / (len(vd) + 1))
    res["p_escratio_ge_max"] = float(((ve >= esc_ratio_max).sum() + 1) / (len(ve) + 1))
    res["levels"] = {p: {"dismissed_assoc": int(full[p + "|Da"]), "unassoc_alerts": int(full[p + "|Au"]),
                         "escalations": int(full[p + "|E"]), "alerts": int(full[p + "|A"]), "dismissals": int(full[p + "|D"]),
                         "assoc": int(full["assoc"]), "network_days_with_episodes": int(full["days"])} for p in (x, y)}
    return res


def verdict(components):
    """components: list of (est, upper, margin). HELD all upper<=margin; not held any est>margin; else inconclusive."""
    if all(u <= m for _, u, m in components): return "HELD"
    if any(e > m for e, _, m in components): return "not held"
    return "inconclusive"


def holm(p):
    ks = sorted(p, key=lambda k: p[k]); m = len(ks); out = {}; run = 0.0
    for i, k in enumerate(ks):
        run = max(run, min(1.0, (m - i) * p[k])); out[k] = round(run, 5)
    return out


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
