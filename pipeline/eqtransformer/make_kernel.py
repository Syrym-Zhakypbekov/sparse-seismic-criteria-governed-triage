"""Generate kaggle_eqt/p10_eqt.py with the episode list embedded (gzip + base64), plus kernel-metadata.json."""
import os, json, gzip, base64
import pandas as pd

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
rows = []
for tag, f in [("dev", "results/stage1_v3/episodes_policies.csv"), ("heldout", "results/heldout/episodes_policies.csv")]:
    for t in pd.read_csv(os.path.join(root, f)).t_on:
        rows.append(f"{tag},{t:.0f}")
blob = base64.b64encode(gzip.compress("\n".join(rows).encode())).decode()

body = open(os.path.join(here, "eqt_body.py"), encoding="utf-8").read()
code = body.replace("__EPISODES_B64__", blob)
open(os.path.join(here, "p10_eqt.py"), "w", encoding="utf-8").write(code)
m = json.load(open(os.path.join(root, "kaggle", "kernel-metadata.json")))
m.update(id="syrym95/p10-seismic-eqtransformer", title="p10-seismic-eqtransformer", code_file="p10_eqt.py", enable_gpu=True)
json.dump(m, open(os.path.join(here, "kernel-metadata.json"), "w"), indent=1)
print(len(rows), "episodes embedded")
