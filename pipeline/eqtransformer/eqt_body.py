"""P10 second alarm source: EQTransformer (SeisBench, pretrained 'original') on every MAKZ episode.
For each STA/LTA episode (development 1077 + held-out 317) a 3-component window [t_on-30 s, t_on+60 s] is fetched
from EarthScope FDSN (IU.MAKZ.00.BH?) and annotated. Output per episode: max detection probability and max P/S pick
probability within [t_on-5 s, t_on+30 s]. Question answered: are STA/LTA alarms without a catalogue event also
earthquake-like for a modern detector? Runs on Kaggle (GPU if enabled). Output: eqt_episodes.csv in the working dir.
"""
import subprocess, sys, os, gzip, base64, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "obspy==1.5.1", "seisbench"], check=True)
import numpy as np, pandas as pd, torch
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import seisbench.models as sbm

W = "/kaggle/working" if os.path.isdir("/kaggle/working") else "."
EP = gzip.decompress(base64.b64decode("__EPISODES_B64__")).decode().splitlines()
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = sbm.EQTransformer.from_pretrained("original")
model.to(dev)
print("seisbench model loaded on", dev, flush=True)
cl = Client("https://service.earthscope.org")
out = []
t0 = time.time()
for k, line in enumerate(EP):
    tag, ts = line.split(",")
    t = UTCDateTime(float(ts))
    rec = dict(set=tag, t_on=float(ts), det=np.nan, p=np.nan, s=np.nan, n_comp=0, error="")
    try:
        st = cl.get_waveforms("IU", "MAKZ", "00", "BH?", t - 30, t + 60)
        st.merge(fill_value=0)
        rec["n_comp"] = len(st)
        ann = model.annotate(st)
        for tr in ann:
            win = tr.slice(t - 5, t + 30)
            v = float(np.max(win.data)) if len(win.data) else np.nan
            ch = tr.stats.channel
            if ch.endswith("_Detection"):
                rec["det"] = v
            elif ch.endswith("_P"):
                rec["p"] = v
            elif ch.endswith("_S"):
                rec["s"] = v
    except Exception as e:
        rec["error"] = type(e).__name__ + ": " + str(e)[:120]
    out.append(rec)
    if k % 100 == 0:
        print(k, len(EP), round(time.time() - t0), "s", flush=True)
        pd.DataFrame(out).to_csv(os.path.join(W, "eqt_episodes.csv"), index=False)
df = pd.DataFrame(out)
df.to_csv(os.path.join(W, "eqt_episodes.csv"), index=False)
print("done", len(df), "errors", int((df.error != "").sum()), "device", dev, "seconds", round(time.time() - t0))
