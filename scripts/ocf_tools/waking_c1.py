"""The owner-approved C1 stereo finishing layer for newly rendered waking sessions."""

from __future__ import annotations

import math
import os
import sys
import wave
from array import array
from pathlib import Path
from tempfile import NamedTemporaryFile

from .locale import iter_events
from .utils import OCFError

PROFILE_ID = "OCF-C1-WAKING-CLOSER-001"
FREQUENCIES_HZ = ((483, 608, 632), (467, 592, 568))  # Left, right.
RMS_DBFS = -34
FADE_IN_SECONDS = 4
FADE_OUT_SECONDS = 8
TAIL_SECONDS = 30
EOF_TAPER_SECONDS = 0.08
RETURN_COMPLETE = "session.return.complete"
FUNCTION_CLOSER = "function.closer"


def policy(document: dict, *, learning: bool = False) -> dict | None:
    """Select a semantic anchor without guessing wakefulness from a function name."""
    events = list(iter_events(document))
    returns = [event["id"] for event in events if event.get("semantic") == RETURN_COMPLETE]
    if not returns:
        return None
    if len(returns) != 1:
        raise OCFError("C1 waking ending requires a unique return completion")
    closers = [
        event["id"]
        for event in events
        if event.get("semantic") == FUNCTION_CLOSER
        and (event.get("narration_key") or str(event.get("text", "")).strip())
    ]
    if not learning and not closers:
        raise OCFError("C1 waking ending requires a spoken function closer")
    return {
        "id": PROFILE_ID,
        "version": "1.0.0",
        "return_event_id": returns[0],
        "closer_event_ids": closers if not learning else [],
        "frequencies_hz": [list(channel) for channel in FREQUENCIES_HZ],
        "combined_steady_rms_dbfs_per_channel": RMS_DBFS,
        "fade_in_seconds": FADE_IN_SECONDS,
        "fade_out_seconds": FADE_OUT_SECONDS,
        "tail_after_speech_seconds": TAIL_SECONDS,
    }


def measured_window(selection: dict, narration: dict) -> tuple[float, float, float]:
    """Return effect start, final speech end, effect end, all from the measured render."""
    rows = [row for row in narration["event_timing"] if row["id"] == selection["return_event_id"]]
    if len(rows) != 1:
        raise OCFError("C1 return completion is missing or ambiguous in measured timing")
    returned_at = float(rows[0]["at"])
    closer_ids = set(selection["closer_event_ids"])
    covered = set()
    start = math.inf if closer_ids else returned_at
    last = 0.0
    other_last = 0.0
    duration = float(narration["duration"])
    for cue in narration["cue_stats"]:
        sources = set(cue.get("source_ids", [cue["id"]]))
        if not str(cue.get("text", "")).strip():
            continue
        at = float(cue["at"])
        rendered_end = at + cue["samples"] / narration["sample_rate"]
        units = cue.get("spoken_units") or []
        end = max(float(unit["end_seconds"]) for unit in units) if units else rendered_end
        if not (math.isfinite(at) and 0 <= at < end <= rendered_end + 0.002 <= duration + 0.002):
            raise OCFError("C1 speech boundaries are outside the measured render")
        matched = sources & closer_ids
        if matched:
            if sources != matched:
                raise OCFError("C1 closer shares a measured utterance with another stage")
            covered |= matched
            start = min(start, at)
            last = max(last, end)
        else:
            other_last = max(other_last, end)
    if not closer_ids:
        last = other_last
    if not (
        covered == closer_ids
        and math.isfinite(returned_at)
        and 0 <= returned_at <= start + 0.002
        and 0 < last <= duration
        and (other_last <= start + 0.002)
        and (not closer_ids or start < last)
        and start < last + TAIL_SECONDS - FADE_OUT_SECONDS
    ):
        raise OCFError("C1 ending is not safely ordered after the measured waking return")
    return start, last, last + TAIL_SECONDS


def add_to_master(base: Path, output: Path, selection: dict, narration: dict) -> dict:
    """Stream PCM16, preserving unaffected frames and failing rather than clipping."""
    start, speech_end, end = measured_window(selection, narration)
    temporary = None
    try:
        with (
            wave.open(str(base), "rb") as reader,
            NamedTemporaryFile(dir=output.parent, prefix=".ocf-c1-", delete=False) as scratch,
        ):
            temporary = Path(scratch.name)
            rate, frames = reader.getframerate(), reader.getnframes()
            if reader.getnchannels() != 2 or reader.getsampwidth() != 2:
                raise OCFError("C1 finishing requires a stereo PCM16 master")
            first, spoken_stop, stop = (round(value * rate) for value in (start, speech_end, end))
            if spoken_stop > frames or not 0 <= first <= frames:
                raise OCFError("C1 ending is outside the mastered audio")
            total_frames = max(frames, stop)
            # If the tone outlasts the base, make its old EOF inaudible. Do not
            # taper speech, nor touch the base when its original tail is longer.
            taper_frames = (
                min(round(EOF_TAPER_SECONDS * rate), frames - spoken_stop) if stop > frames else 0
            )
            taper_from = frames - taper_frames
            omega = tuple(
                tuple(math.tau * frequency / rate for frequency in channel)
                for channel in FREQUENCIES_HZ
            )
            amplitude = 32768 * 10 ** (RMS_DBFS / 20) * math.sqrt(2 / 3)
            with wave.open(scratch, "wb") as writer:
                writer.setparams(reader.getparams())
                for offset in range(0, total_frames, 16384):
                    count = min(16384, total_frames - offset)
                    input_frames = max(0, min(count, frames - offset))
                    pcm = reader.readframes(input_frames)
                    if len(pcm) != input_frames * 4:
                        raise OCFError("C1 base master has truncated PCM")
                    if offset + count <= min(first, taper_from) or offset >= stop:
                        writer.writeframesraw(pcm)
                        continue
                    buffer = array("h")
                    buffer.frombytes(pcm + bytes((count - input_frames) * 4))
                    if sys.byteorder != "little":
                        buffer.byteswap()
                    for frame in range(
                        max(offset, min(first, taper_from)), min(offset + count, stop)
                    ):
                        phase = frame - first
                        env = min(
                            1.0,
                            max(0, phase) / (FADE_IN_SECONDS * rate),
                            (stop - 1 - frame) / (FADE_OUT_SECONDS * rate),
                        )
                        gain = amplitude * math.sin(math.pi * env / 2) ** 2
                        taper = 1.0
                        if taper_frames and taper_from <= frame < frames:
                            taper = (frames - 1 - frame) / max(1, taper_frames - 1)
                        for channel, angles in enumerate(omega):
                            index = (frame - offset) * 2 + channel
                            mixed = round(
                                buffer[index] * taper
                                + gain * sum(math.sin(angle * phase) for angle in angles)
                            )
                            if not -32768 < mixed < 32767:
                                raise OCFError("C1 overlay would clip; review base master headroom")
                            buffer[index] = mixed
                    if sys.byteorder != "little":
                        buffer.byteswap()
                    writer.writeframesraw(buffer.tobytes())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        **selection,
        "start_seconds": first / rate,
        "last_speech_end_seconds": spoken_stop / rate,
        "end_seconds": stop / rate,
        "base_master_seconds": frames / rate,
        "final_master_seconds": total_frames / rate,
        "extension_seconds": (total_frames - frames) / rate,
    }
