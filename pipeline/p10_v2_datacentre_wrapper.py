"""Run pipeline/extended_stalta_criteria.py UNCHANGED for a network archived outside EarthScope (PREREGISTRATION_V2_NETWORKS_2026-11-08.md).
The frozen pipeline requests waveforms from Client("EARTHSCOPE"). This wrapper only redirects that one name to the data centre
given in P10_FDSN_BASE (e.g. https://geofon.gfz.de); catalogue clients ("ISC", "USGS") are untouched. The detector, thresholds,
windows and association are the pipeline's own code, byte-identical (sha256 checked below before running).
Usage: P10_FDSN_BASE=https://geofon.gfz.de P10_STATIONS=... python pipeline/p10_v2_datacentre_wrapper.py
"""
import os, sys, hashlib, runpy
import obspy.clients.fdsn as fdsn

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.environ.get("P10_PIPELINE", os.path.join(HERE, "extended_stalta_criteria.py"))
FROZEN_SHA256 = "4c8c9a715bdfc94c7790ac0793f85360ae6a75489ca197acc2aad92483168284"   # LF-normalised, as committed at 9a8436c
got = hashlib.sha256(open(PIPE, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
if got != FROZEN_SHA256 and not os.environ.get("P10_SKIP_SHA"):
    sys.exit(f"pipeline sha256 {got} differs from the frozen {FROZEN_SHA256}")

_Base = fdsn.Client
BASE = os.environ.get("P10_FDSN_BASE", "").strip()


class Client(_Base):
    def __init__(self, base_url="EARTHSCOPE", *a, **k):
        if base_url == "EARTHSCOPE" and BASE:
            base_url = BASE
        super().__init__(base_url, *a, **k)


fdsn.Client = Client
runpy.run_path(PIPE, run_name="__main__")
