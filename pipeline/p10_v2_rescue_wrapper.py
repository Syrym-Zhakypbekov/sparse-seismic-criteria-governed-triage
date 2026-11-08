"""Rescue wrapper (PREREGISTRATION_V2_RESCUE_2026-11-08.md). Runs pipeline/p10_v2_datacentre_wrapper.py (which checks the frozen
pipeline sha256 and redirects only the waveform data centre) UNCHANGED. With P10_RATE_FIX=1 (network CZ only), before the
pipeline's Stream.merge, every trace whose sampling rate differs from the nominal rate of its channel (the most common rate in
that stream) by less than 0.01 % is resampled to the nominal rate (linear interpolation, rounded back to the channel's integer data type); each such trace is counted in
stderr ("rate_fix"). This removes only the data defect that made obspy refuse to merge (CZ.PRU: 100 vs 99.99998 Hz).
"""
import os, runpy
from collections import Counter
import numpy as np
from obspy.core.stream import Stream

HERE = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("P10_RATE_FIX") == "1":
    _merge = Stream.merge

    def merge(self, *a, **k):
        by = {}
        for tr in self.traces: by.setdefault(tr.id, []).append(tr)
        n = 0
        for _id, trs in by.items():
            nom = Counter(round(t.stats.sampling_rate, 6) for t in trs).most_common(1)[0][0]
            for t in trs:
                sr = t.stats.sampling_rate
                if sr != nom and abs(sr - nom) / nom < 1e-4:
                    dtype = t.data.dtype
                    t.interpolate(sampling_rate=nom, method="linear")
                    if dtype.kind in "iu": t.data = np.round(t.data).astype(dtype)   # keep the channel's data type for merge
                    n += 1
        if n: print(f"rate_fix: {n} trace(s) resampled to nominal", flush=True)
        return _merge(self, *a, **k)

    Stream.merge = merge

runpy.run_path(os.path.join(HERE, "p10_v2_datacentre_wrapper.py"), run_name="__main__")
