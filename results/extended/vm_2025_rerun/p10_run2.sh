#!/bin/bash
# job A: rerun 2025-09/10 (ISC catalogue failed in the first run), frozen thresholds
# job B: second reference station KURK, tuned on 2026-07-01..07, evaluated 2026-07-08..10-01
while [ ! -f /opt/p10/READY ]; do sleep 10; done
cd ~/p10; export P10_NO_PIP=1
mkdir -p outA_2025-09-01 outB_ref_KURK
P10_FIXED_THR='{"MAKZ": 7.010977, "MK31": 7.384668, "KURK": 6.796058, "WUS": 3.490711}' P10_T0=2025-09-01 P10_TUNE_END=2025-09-01 P10_EVAL_START=2025-09-01 P10_T1=2025-11-01 P10_OUT=$PWD/outA_2025-09-01 nohup /opt/p10/bin/python p10_stalta_criteria.py > outA_2025-09-01/run.log 2>&1 &
sleep 120
P10_REF=KURK P10_T0=2026-07-01 P10_TUNE_END=2026-07-08 P10_EVAL_START=2026-07-08 P10_T1=2026-10-01 P10_OUT=$PWD/outB_ref_KURK nohup /opt/p10/bin/python p10_stalta_criteria.py > outB_ref_KURK/run.log 2>&1 &
wait; touch ALL_DONE_2