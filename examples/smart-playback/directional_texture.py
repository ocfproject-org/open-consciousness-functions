"""Reviewed port of the owner's directional-noise sketch; no source audio input.

Only a dedicated added texture is processed, never narration or a carrier bed.
No production dispatch/default is enabled by this experimental module.
"""

from __future__ import annotations

import numpy as np


def smooth(value):
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def texture(rng, size, cutoff, rate=48000):
    frequencies = np.fft.rfftfreq(size, 1.0 / rate)
    shape = 1.0 / np.sqrt(np.maximum(frequencies, 80.0))
    shape *= 1.0 - np.exp(-((frequencies / 85.0) ** 4))
    shape /= np.sqrt(1.0 + (frequencies / cutoff) ** 8)

    def noise():
        signal = np.fft.irfft(np.fft.rfft(rng.standard_normal(size)) * shape, n=size)
        return signal / np.sqrt(np.mean(signal * signal))

    center = noise()
    return np.column_stack([0.92 * center + 0.28 * noise() for _ in range(2)])


def comb(signal, delay, amount, rate):
    positions = np.arange(signal.size, dtype=np.float64)
    delayed = np.interp(positions - delay * rate, positions, signal, left=0.0, right=0.0)
    return (signal + amount * delayed) / np.sqrt(1.0 + amount * amount)


def smooth_sweep(times, duration, arrival, direction):
    """Effect-only raised-cosine ramps and full-width equal-power stereo travel."""
    rise = min(3.2, arrival * 0.47)
    fall = min(4.0, duration - arrival)
    if rise <= 0 or fall <= 0 or direction not in (-1, 1):
        raise ValueError("Smooth sweep requires measured count and a positive tail")

    def cosine(x):
        return (1 - np.cos(np.pi * np.clip(x, 0, 1))) / 2

    env = cosine(times / rise) * cosine((times[-1] - times) / fall)
    begin = rise * 0.7
    finish = arrival
    progress = cosine((times - begin) / (finish - begin))
    angle = progress * np.pi / 2
    gains = np.column_stack((np.cos(angle), np.sin(angle)))
    if direction < 0:
        gains = gains[:, ::-1]
    return env[:, None] * gains * np.sqrt(2)


def render(
    old,
    new,
    duration,
    direction,
    *,
    rate=48000,
    lead=2.0,
    tail=4.0,
    spatial=True,
    envelope="reference",
):
    """Continuous full-window synthesis. Slice afterwards; never restart per block.

    Default 30-second framing reproduces the accepted example. Production callers
    must resolve count/arrival/tail first and supply real lead/tail durations.
    This renderer does not decide semantic eligibility.
    """
    if direction not in (-1, 1) or not np.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid direction/duration")
    if rate < 8000 or old.shape != new.shape or old.shape != (round(duration * rate), 2):
        raise ValueError("Invalid stereo shape/sample rate")
    if not np.isfinite(old).all() or not np.isfinite(new).all():
        raise ValueError("Nonfinite texture")
    if min(lead, tail) < 0 or lead + tail >= duration:
        raise ValueError("Count must have positive measured duration")
    times = np.arange(old.shape[0]) / rate
    span = duration - lead - tail
    # Defaults are exactly the owner's formulas; short counts clamp only framing.
    ear_offset = min(1.0, span / 4)
    gate_start = min(1.0, lead / 2)
    gate_rise = min(1.2, span / 4)
    gate_end = min(0.4, tail / 10)
    gate_fall = min(3.6, max(1 / rate, tail - gate_end))
    travel_angle = np.pi * smooth((times - lead) / span) / 2.0
    effect_gate = smooth((times - gate_start) / gate_rise)
    effect_gate *= smooth((duration - gate_end - times) / gate_fall)
    output = np.zeros_like(old)
    for channel in range(2):
        side = 1.0 if channel == 0 else -1.0
        offset = direction * side * ear_offset if spatial else 0.0
        progress = smooth((times - lead + offset) / span)
        angle = np.pi * progress / 2.0
        signal = np.cos(angle) * old[:, channel] + np.sin(angle) * new[:, channel]
        if spatial:
            sweep = progress if direction > 0 else 1.0 - progress
            delay = 0.003 * (0.0006 / 0.003) ** sweep
            swept = comb(signal, delay, 0.62, rate)
            role = channel if direction > 0 else 1 - channel
            frequency = (0.08, 0.02)[role]
            phase = (0.8, 2.1)[role]
            cycle = (1.0 + np.cos(2 * np.pi * frequency * times + phase)) / 2.0
            swept = comb(swept, 0.000075 + 0.000365 * cycle, 0.28, rate)
            travel = np.cos(travel_angle) if role == 0 else np.sin(travel_angle)
            wet_gate = effect_gate * (0.35 + 0.65 * travel)
            signal += wet_gate * (swept - signal)
        output[:, channel] = signal
    if envelope == "gentle-full-width-v1":
        if not spatial:
            raise ValueError("Gentle full-width sweep requires stereo travel")
        return output * smooth_sweep(times, duration, duration - tail, direction)
    if envelope != "reference":
        raise ValueError("Unknown transition envelope")
    fade_in = min(0.35, duration / 4)
    fade_out = min(0.5, duration / 4)
    outer = smooth(times / fade_in) * smooth((duration - times - 1 / rate) / fade_out)
    return output * outer[:, None]


def reference(seed=90210):
    """Return the original 30s reference triplet, with its shared gain only."""
    rng = np.random.default_rng(seed)
    old, new = texture(rng, 30 * 48000, 6500), texture(rng, 30 * 48000, 10000)
    plain = render(old, new, 30, 1, spatial=False)
    up, down = render(old, new, 30, 1), render(new, old, 30, -1)
    gain = 10 ** (-6 / 20) / max(np.max(np.abs(x)) for x in (plain, up, down))
    return tuple(x * gain for x in (plain, up, down))
