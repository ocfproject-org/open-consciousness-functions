import hashlib
import io
import json
import wave

import pytest
from ocf_tools import speech_cache, speech_verify, voice
from ocf_tools.utils import OCFError

pytestmark = pytest.mark.unit
SPEC = {"name": "chatterbox-nano", "locale": "en-US"}
EXPECTED = "Go now."


def pcm(sample):
    result = io.BytesIO()
    with wave.open(result, "wb") as stream:
        stream.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        stream.writeframes(bytes((sample, 0)) * 128)
    return result.getvalue()


def sha(wav):
    return hashlib.sha256(wav).hexdigest()


class Verifier:
    identity = {"fixture": True}

    def __init__(self, *, clean=(), outages=()):
        self.clean = clean
        self.outages = outages

    def verify(self, data, text, locale):
        assert text == EXPECTED and locale == "en-US"
        if data in self.outages:
            raise OCFError("offline verifier unavailable")
        if data not in self.clean:
            raise speech_verify.SpeechMismatch(
                locale=locale,
                wav_sha256=sha(data),
                text_sha256=sha(text.encode()),
                first_difference=1,
                expected=2,
                heard=3,
            )
        return {"wav_sha256": sha(data)}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(speech_cache, "voice_identity", lambda spec: spec)
    work = tmp_path / "isolated-work"
    monkeypatch.setenv("OCF_WORK_DIR", str(work))
    _, key = speech_cache._synthesis_identity(SPEC, EXPECTED)
    return work / "cache" / "tts" / key


def test_real_cache_receives_only_eventual_whisper_pass(monkeypatch, store):
    rejected, accepted = pcm(1), pcm(2)
    takes = iter((rejected, accepted))
    verifier = Verifier(clean=(accepted,))

    def synthesize(*_):
        assert not store.exists(), "an unverified take reached the cache"
        return next(takes)

    monkeypatch.setattr(voice, "_render_cue_wav", synthesize)
    with speech_cache.policy(), speech_verify.verification_scope(verifier) as rows:
        assert voice.render_cue_wav(SPEC, EXPECTED) == accepted
        assert voice.render_cue_wav(SPEC, EXPECTED) == accepted  # cache hit rechecked
    proof = speech_verify.evidence(verifier, rows)
    assert [r["wav_sha256"] for r in proof["segments"]] == [sha(accepted)] * 2
    [row] = proof["rejected_attempts"]
    assert row["take"] == 1 and row["source"] == "fresh"
    assert row["wav_sha256"] == sha(rejected) and row["first_differing_word"] == 1
    assert str(EXPECTED) not in json.dumps(proof)
    assert store.joinpath("speech.wav").read_bytes() == accepted


def test_exhaustion_is_bounded_and_has_no_cache_candidate(monkeypatch, store):
    calls = []

    def synthesize(*_):
        calls.append(pcm(len(calls) + 1))
        return calls[-1]

    monkeypatch.setattr(voice, "_render_cue_wav", synthesize)
    with speech_cache.policy(), speech_verify.verification_scope(Verifier()) as rows:
        with pytest.raises(speech_verify.SpeechMismatch, match="Fresh takes rejected: 3") as exc:
            voice.render_cue_wav(SPEC, EXPECTED)
    assert len(calls) == 3 and not store.exists()
    assert [row["wav_sha256"] for row in rows] == [sha(wav) for wav in calls]
    assert all(sha(wav)[:12] in str(exc.value) for wav in calls)
    with pytest.raises(OCFError, match="verified no TTS segments"):
        speech_verify.evidence(Verifier(), rows)


def test_transcriber_outage_is_not_a_tts_mismatch_or_retry(monkeypatch, store):
    calls = []
    take = pcm(1)
    monkeypatch.setattr(voice, "_render_cue_wav", lambda *_: calls.append(True) or take)
    with speech_cache.policy(), speech_verify.verification_scope(Verifier(outages=(take,))) as rows:
        with pytest.raises(OCFError, match="offline verifier unavailable") as exc:
            voice.render_cue_wav(SPEC, EXPECTED)
    assert not isinstance(exc.value, speech_verify.SpeechMismatch)
    assert len(calls) == 1 and not store.exists() and not rows


def test_cached_mismatch_never_overwrites_original_or_generates(monkeypatch, store):
    original = pcm(1)
    identity, key = speech_cache._synthesis_identity(SPEC, EXPECTED)
    speech_cache._publish(store, key, original, identity=identity)
    monkeypatch.setattr(voice, "_render_cue_wav", lambda *_: pytest.fail("cache hit regenerated"))
    with speech_cache.policy(), speech_verify.verification_scope(Verifier()) as rows:
        with pytest.raises(speech_verify.SpeechMismatch, match="Cache hit withheld"):
            voice.render_cue_wav(SPEC, EXPECTED)
    assert store.joinpath("speech.wav").read_bytes() == original
    assert rows[0]["source"] == "cache" and rows[0]["take"] is None
