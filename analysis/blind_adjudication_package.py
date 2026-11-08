"""Blind waveform-adjudication package (planned, post hoc; internal review v32, point M2).

Cases: the reviewed-associated episodes of the 33 reviewed networks that CG c = 0.5 dismissed and P3 (7.5 dB) did not
(discordant), mixed with equal-sized controls drawn with seed 7 from reviewed-associated episodes dismissed by both and
alerted by both. Cases are shuffled and given neutral ids; no rule action, label or class is shown to the analyst. The key
(class, network, time, actions) is written to a separate file that the analyst must not open.

Output (adjudication/blind_v1/): cases.csv (case id, reference stream, neighbour streams, window start/end UTC),
plots/<case>.png (reference + neighbours, 1-8 Hz band-pass, common time axis, no labels), ANALYST_FORM.csv
(case, signal_on_reference [yes/no/unsure], signal_on_any_neighbour, notes), KEY_DO_NOT_OPEN.json.
Run: python analysis/blind_adjudication_package.py [--no-waveforms]
"""
import os, sys, json, glob, pickle, argparse
import numpy as np, pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
OUT = os.path.join(root, "adjudication", "blind_v1"); SEED = 7


def cfgs():
    c = {}
    for f in ("networks.json", "networks_batchB.json"):
        for n in json.load(open(os.path.join(root, "results", "v2", f)))["networks"]: c[n["network"]] = n
    return c


def episodes(net):
    dirs = sorted(glob.glob(os.path.join(root, "results", "v2", "runs", net, "out_*")))
    return pd.concat([pd.read_csv(os.path.join(d, "episodes.csv")) for d in dirs], ignore_index=True)


def select():
    R = pickle.load(open(os.path.join(root, "results", "posthoc", "_collect_reviewed.pkl"), "rb"))
    R = {k: v for k, v in sorted(R.items()) if v.get("included")}
    C = cfgs(); rows = {"discordant": [], "both_dismissed": [], "both_alerted": []}
    for net, v in R.items():
        ep = episodes(net)
        assert len(ep) == len(v["snr"]), net
        assert np.allclose(ep.snr_db.fillna(0).to_numpy(), v["snr"]), net  # alignment check
        a5, a3, assoc = v["act"]["CG_c05"], v["act"]["P3"], v["assoc"]
        for cls, m in (("discordant", (a5 == "D") & (a3 != "D") & assoc), ("both_dismissed", (a5 == "D") & (a3 == "D") & assoc),
                       ("both_alerted", (a5 == "A") & (a3 == "A") & assoc)):
            for i in np.flatnonzero(m):
                rows[cls].append({"network": net, "t_on_utc": ep.t_on_utc[i], "snr_db": float(ep.snr_db[i]) if pd.notna(ep.snr_db[i]) else None,
                                  "CG_c05": a5[i], "P3": a3[i], "reference": C[net]["reference_stream"],
                                  "neighbours": [m_["stream"] for s in C[net]["sites"] for m_ in s["members"]],
                                  "dataselect": C[net].get("dataselect") or C[net].get("fdsn_base")})
    rng = np.random.default_rng(SEED); n = len(rows["discordant"]); cases = list(rows["discordant"])
    for cls in ("both_dismissed", "both_alerted"):
        pick = rng.choice(len(rows[cls]), size=min(n, len(rows[cls])), replace=False)
        cases += [dict(rows[cls][j], cls=cls) for j in sorted(pick)]
    for c in cases[:n]: c["cls"] = "discordant"
    order = rng.permutation(len(cases)); out = []
    for k, j in enumerate(order): out.append(dict(cases[j], case=f"C{k + 1:03d}"))
    return out, {k: len(v) for k, v in rows.items()}


def fetch_plot(case, png):
    from obspy import UTCDateTime
    from obspy.clients.fdsn import Client
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    t0 = UTCDateTime(case["t_on_utc"]) - 60; t1 = t0 + 180
    base = case["dataselect"].split("/fdsnws")[0] if case["dataselect"] else "EARTHSCOPE"
    cl = Client(base); streams = [case["reference"]] + case["neighbours"]; tr_list = []
    for s in streams:
        net, sta, loc, cha = s.split(".")
        try:
            st = cl.get_waveforms(net, sta, loc or "", cha, t0 - 30, t1 + 30); st.merge(fill_value=0)
            st.detrend("demean"); st.filter("bandpass", freqmin=1, freqmax=8, corners=4, zerophase=True); st.trim(t0, t1)
            tr_list.append((s, st[0] if len(st) else None))
        except Exception:
            tr_list.append((s, None))
    fig, axes = plt.subplots(len(tr_list), 1, figsize=(10, 1.6 * len(tr_list)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (s, tr) in zip(axes, tr_list):
        if tr is None: ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center"); ax.set_yticks([])
        else:
            t = tr.times(reftime=t0); ax.plot(t, tr.data, lw=0.5, color="k"); ax.set_yticks([])
        ax.set_ylabel(s.split(".")[1], rotation=0, ha="right", fontsize=8)
    axes[-1].set_xlabel("seconds from window start (window = 180 s)"); fig.suptitle(case["case"], fontsize=9)
    fig.tight_layout(); fig.savefig(png, dpi=150); plt.close(fig)
    return sum(1 for _, tr in tr_list if tr is not None)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--no-waveforms", action="store_true"); a = ap.parse_args()
    os.makedirs(os.path.join(OUT, "plots"), exist_ok=True)
    cases, counts = select()
    key = {"counts_available": counts, "cases": [{k: c[k] for k in ("case", "cls", "network", "t_on_utc", "snr_db", "CG_c05", "P3")} for c in cases]}
    json.dump(key, open(os.path.join(OUT, "KEY_DO_NOT_OPEN.json"), "w"), indent=1)
    from obspy import UTCDateTime
    pd.DataFrame([{"case": c["case"], "reference": c["reference"], "neighbours": " ".join(c["neighbours"]),
                   "window_start_utc": str(UTCDateTime(c["t_on_utc"]) - 60), "window_end_utc": str(UTCDateTime(c["t_on_utc"]) + 120)}
                  for c in sorted(cases, key=lambda c: c["case"])]).to_csv(os.path.join(OUT, "cases.csv"), index=False)
    pd.DataFrame([{"case": c["case"], "signal_on_reference (yes/no/unsure)": "", "signal_on_any_neighbour (yes/no/unsure)": "",
                   "notes": ""} for c in sorted(cases, key=lambda c: c["case"])]).to_csv(os.path.join(OUT, "ANALYST_FORM.csv"), index=False)
    print("cases", len(cases), counts)
    if a.no_waveforms: return
    ok = 0
    for c in sorted(cases, key=lambda c: c["case"]):
        png = os.path.join(OUT, "plots", c["case"] + ".png")
        if os.path.exists(png): ok += 1; continue
        try: n = fetch_plot(c, png); ok += n > 0; print(c["case"], n, flush=True)
        except Exception as e: print(c["case"], "ERR", e, flush=True)
    print("plotted", ok, "of", len(cases))


if __name__ == "__main__":
    main()
