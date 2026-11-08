#!/bin/bash
# AK-network replication (PREREGISTRATION_AK_NETWORK.md). Same pipeline as the KZ run (p10_stalta_criteria_kz.py,
# identical to pipeline/extended_stalta_criteria.py); stations via P10_STATIONS; thresholds from the tuning week only.
cd ~/p10
export P10_NO_PIP=1 P10_FETCH_PAUSE=2
export P10_STATIONS='{"MAKZ": ["AK","CUT","","BHZ",62.4058,-150.2625], "MK31": ["AK","L22K","","BHZ",62.5258,-150.7703], "KURK": ["AK","COLD","","BHZ",67.2278,-150.207], "WUS": ["AK","E22K","","BHZ",68.1343,-151.8132]}'
PY=/opt/p10/bin/python
mkdir -p outAK_tune
date -u +%Y-%m-%dT%H:%M:%SZ > outAK_tune/started_utc.txt
P10_T0=2024-01-01 P10_TUNE_END=2024-01-08 P10_EVAL_START=2024-01-08 P10_T1=2024-01-09 P10_OUT=$PWD/outAK_tune $PY p10_stalta_criteria_kz.py > outAK_tune/run.log 2>&1
THR=$($PY - <<'P'
import re, json, math
t = open("outAK_tune/run.log").read(); line = [l for l in t.splitlines() if l.startswith("thresholds")][0]
d = {k: float(v) for k, v in re.findall(r"'(\w+)': (?:np\.float64\()?([\d.]+)", line)}
assert len(d) == 4 and all(math.isfinite(x) for x in d.values()), line
print(json.dumps(d))
P
) || { echo "TUNING FAILED"; exit 1; }
echo "THR=$THR" | tee outAK_tune/thresholds.txt
export P10_FIXED_THR="$THR"
run() { set -- $1; d=outAK_$1; mkdir -p $d; P10_T0=$1 P10_TUNE_END=$1 P10_EVAL_START=$1 P10_T1=$2 P10_OUT=$PWD/$d $PY p10_stalta_criteria_kz.py > $d/run.log 2>&1; }
run "2024-01-08 2024-04-01" & sleep 60; run "2024-04-01 2024-07-01" & sleep 60; run "2024-07-01 2024-10-01" & sleep 60
run "2024-10-01 2025-01-01" & sleep 60; run "2025-01-01 2025-04-01" & sleep 60; run "2025-04-01 2025-07-01" & wait
touch ALL_DONE_AK
