"""Waking C1 selection, sample-level mix invariants and receipt timing."""

import math
import sys
import wave
from array import array
from copy import deepcopy

import pytest
from ocf_tools import waking_c1
from ocf_tools.utils import OCFError


def document(*, sleep=False, learning=False):
    timeline = [] if sleep else [{"id": "wake", "semantic": waking_c1.RETURN_COMPLETE}]
    if not learning:
        timeline.append({"id": "closing", "semantic": waking_c1.FUNCTION_CLOSER, "text": "End."})
    return {"sections": [{"id": "outro", "timeline": timeline}]}


def measured(*, learning=False):
    return {
        "event_timing": [{"id": "wake", "at": 2.0}],
        "cue_stats": [
            {
                "id": "return-text",
                "at": 1.0,
                "samples": 8000,
                "text": "One.",
            },
            *(
                []
                if learning
                else [
                    {
                        "id": "closing",
                        "at": 3.0,
                        "samples": 16000,
                        "text": "End.",
                        "spoken_units": [{"end_seconds": 4.0}],
                    }
                ]
            ),
        ],
        "sample_rate": 8000,
        "duration": 6.0,
    }


def write_stereo(path, duration, value=1600):
    buf = array("h", [value, -value] * (8000 * duration))
    if sys.byteorder != "little":
        buf.byteswap()
    with wave.open(str(path), "wb") as out:
        out.setparams((2, 2, 8000, 0, "NONE", "not compressed"))
        out.writeframes(buf.tobytes())


def read_stereo(path):
    with wave.open(str(path), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (2, 2, 8000)
        pcm = array("h")
        pcm.frombytes(audio.readframes(audio.getnframes()))
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm


def test_sleep_ending_excluded_even_if_function_closer_remains():
    assert waking_c1.policy(document(sleep=True)) is None


def test_learning_starts_only_after_the_measured_return():
    choice = waking_c1.policy(document(learning=True), learning=True)
    assert waking_c1.measured_window(choice, measured(learning=True)) == (2.0, 2.0, 32.0)


def test_waking_uses_spoken_end_not_pause_or_pcm_extent():
    choice = waking_c1.policy(document())
    assert waking_c1.measured_window(choice, measured()) == (3.0, 4.0, 34.0)


@pytest.mark.parametrize(
    "error", ["no-return", "cross-stage", "invalid-samples", "early-closer", "later-speech"]
)
def test_fails_closed_when_the_ledger_is_not_safe(error):
    choice = waking_c1.policy(document())
    timing = deepcopy(measured())
    if error == "no-return":
        timing["event_timing"].clear()
    if error == "cross-stage":
        timing["cue_stats"][-1]["source_ids"] = ["closing", "elsewhere"]
    if error == "invalid-samples":
        timing["cue_stats"][-1]["samples"] = 0
    if error == "early-closer":
        timing["event_timing"][0]["at"] = 3.5
    if error == "later-speech":
        timing["cue_stats"].append({"id": "later", "at": 5.0, "samples": 1600, "text": "Later."})
    with pytest.raises(OCFError, match="C1"):
        waking_c1.measured_window(choice, timing)


def test_unknown_nonlearning_outro_and_duplicate_return_are_rejected():
    with pytest.raises(OCFError, match="spoken function closer"):
        waking_c1.policy(document(learning=True))
    doc = document()
    doc["sections"][0]["timeline"].append(
        {"id": "duplicate", "semantic": waking_c1.RETURN_COMPLETE}
    )
    with pytest.raises(OCFError, match="unique"):
        waking_c1.policy(doc)


def test_pcm_transitions_levels_and_left_right_orientation(tmp_path):
    base, wet = tmp_path / "base.wav", tmp_path / "wet.wav"
    write_stereo(base, 6)
    choice = waking_c1.policy(document())
    receipt = waking_c1.add_to_master(base, wet, choice, measured())
    rate = 8000
    original, result = read_stereo(base), read_stereo(wet)
    assert receipt["extension_seconds"] == 28
    assert receipt["end_seconds"] - receipt["last_speech_end_seconds"] == 30
    assert len(result) == 34 * rate * 2
    assert original[: 3 * rate * 2] == result[: 3 * rate * 2]
    assert result[-2:] == array("h", [0, 0])
    assert abs(result[6 * rate * 2] - result[6 * rate * 2 - 2]) < 1300
    assert max(abs(s) for s in result) < 32767
    for channel, frequencies in enumerate(waking_c1.FREQUENCIES_HZ):
        steady = result[10 * rate * 2 + channel : 11 * rate * 2 : 2]
        rms = math.sqrt(sum(x * x for x in steady) / rate) / 32768
        assert 20 * math.log10(rms) == pytest.approx(-34, abs=0.02)
        for tone in frequencies:
            magnitude = (
                abs(sum(x * math.sin(math.tau * tone * n / rate) for n, x in enumerate(steady)))
                * 2
                / rate
            )
            assert magnitude == pytest.approx(32768 * 10 ** (-34 / 20) * math.sqrt(2 / 3), abs=0.2)


def test_existing_longer_ending_is_not_cut_or_ducked(tmp_path):
    base, wet = tmp_path / "base.wav", tmp_path / "wet.wav"
    write_stereo(base, 36)
    receipt = waking_c1.add_to_master(base, wet, waking_c1.policy(document()), measured())
    assert receipt["extension_seconds"] == 0
    dry, output = read_stereo(base), read_stereo(wet)
    assert dry[34 * 8000 * 2 :] == output[34 * 8000 * 2 :]


def test_clipping_aborts_without_overwriting_target(tmp_path):
    base, wet = tmp_path / "base.wav", tmp_path / "wet.wav"
    write_stereo(base, 12, value=32700)
    wet.write_bytes(b"previous output")
    with pytest.raises(OCFError, match="would clip"):
        waking_c1.add_to_master(base, wet, waking_c1.policy(document()), measured())
    assert wet.read_bytes() == b"previous output"
    assert not list(tmp_path.glob(".ocf-c1-*"))


@pytest.mark.integration
def test_real_composed_comfort_and_learning_route_without_synthesis():
    from ocf_tools.complete_session import build_complete_session_plan
    from ocf_tools.learning_session import plan

    for overrides, wanted in [({}, True), ({"ending": "sleep"}, False)]:
        doc = build_complete_session_plan("OCF-BOD-003", overrides=overrides)["template_plan"]
        selected = waking_c1.policy(doc)
        assert bool(selected) is wanted
        if selected:
            assert selected["closer_event_ids"] == ["function-closer.block"]
    learning = waking_c1.policy(plan()["document"], learning=True)
    assert learning["return_event_id"] == "return.complete"
    assert learning["closer_event_ids"] == []


@pytest.mark.integration
def test_audio_builder_finishes_before_hashes_and_encoding(tmp_path, monkeypatch):
    from ocf_tools import audio_build
    from ocf_tools.utils import sha256_of_file

    monkeypatch.setenv("OCF_WORK_DIR", str(tmp_path / "workspace"))

    def fake_narration(_doc, path, **_kwargs):
        write_stereo(path, 6)
        return {
            **measured(),
            "backend": "synthetic",
            "channels": 2,
            "cues": 2,
            "overlap_mode": "reject-fixed-overlap",
        }

    monkeypatch.setattr(audio_build, "render_narration", fake_narration)
    seen = []

    def fake_encode(path, fmt, output, **_kwargs):
        with wave.open(str(path), "rb") as master:
            seen.append((fmt, master.getnframes(), master.getframerate()))
        output.write_bytes(b"fixture")
        return "synthetic"

    monkeypatch.setattr(audio_build, "_encode", fake_encode)
    doc = document()
    result = audio_build.build(
        "waking-fixture",
        manifest_override={"title": "C1 fixture", "background_audio": {"strategy": "none"}},
        document_override=doc,
        render_label="waking-fixture",
        out_root=tmp_path / "outputs",
        formats=["wav", "flac", "mp3"],
        sample_rate=8000,
        waking_c1=waking_c1.policy(doc),
    )
    master = tmp_path / "outputs" / result["master"]["file"]
    assert result["waking_c1"]["final_master_seconds"] == 34
    assert result["master"]["duration"] == 34
    assert result["master"]["checksum_sha256"] == sha256_of_file(master)
    assert seen == [("flac", 34 * 8000, 8000), ("mp3", 34 * 8000, 8000)]
