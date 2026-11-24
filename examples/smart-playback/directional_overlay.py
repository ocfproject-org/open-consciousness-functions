"""Audition-only dedicated texture overlay; callers must supply selected windows."""

import numpy as np
from directional_texture import render, texture


def overlay(baseline, rate, windows, *, gain_db=-36.0, seed=90210, envelope="reference"):
    if baseline.ndim != 2 or baseline.shape[1] != 2 or not np.isfinite(baseline).all():
        raise ValueError("Finite stereo baseline required")
    if not np.isfinite(gain_db) or gain_db > 0:
        raise ValueError("Nonpositive finite fixed gain required")
    candidate = baseline.copy()
    used_end = 0
    for index, window in enumerate(windows):
        start, arrival, end = (round(window[k] * rate) for k in ("start", "arrival", "end"))
        if not used_end <= start < arrival <= end <= len(baseline):
            raise ValueError("Overlapping or out-of-range FX window")
        used_end = end
        size = end - start
        rng = np.random.default_rng(seed + index)
        old, new = texture(rng, size, 6500, rate), texture(rng, size, 10000, rate)
        if window["direction"] < 0:
            old, new = new, old
        added = render(
            old,
            new,
            size / rate,
            window["direction"],
            rate=rate,
            lead=0,
            tail=(end - arrival) / rate,
            envelope=envelope,
        )
        candidate[start:end] += added * 10 ** (gain_db / 20)
    if np.max(np.abs(candidate)) >= 1:
        raise ValueError("Overlay clips; lower fixed FX gain, never normalize source")
    return candidate
