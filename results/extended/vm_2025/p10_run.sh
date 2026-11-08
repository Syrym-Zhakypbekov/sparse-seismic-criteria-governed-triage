#!/bin/bash
# extended run 2025, six two-month chunks in parallel, frozen detector thresholds (PREREGISTRATION_EXTENDED.md)
while [ ! -f /opt/p10/READY ]; do sleep 10; done
mkdir -p ~/p10 && cd ~/p10
export P10_NO_PIP=1 P10_FIXED_THR='{"MAKZ": 7.010977, "MK31": 7.384668, "KURK": 6.796058, "WUS": 3.490711}'
for span in "2025-01-01 2025-03-01" "2025-03-01 2025-05-01" "2025-05-01 2025-07-01" "2025-07-01 2025-09-01" "2025-09-01 2025-11-01" "2025-11-01 2026-01-01"; do
  set -- $span; d=out_$1; mkdir -p $d
  P10_T0=$1 P10_TUNE_END=$1 P10_EVAL_START=$1 P10_T1=$2 P10_OUT=$PWD/$d nohup /opt/p10/bin/python p10_stalta_criteria.py > $d/run.log 2>&1 &
done
wait; touch ALL_DONE