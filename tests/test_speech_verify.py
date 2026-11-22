from contextlib import nullcontext

import pytest
from ocf_tools import bulk_render, speech_cache, speech_verify, voice
from ocf_tools.utils import OCFError


@pytest.mark.unit
def test_number_typography_without_hiding_cue_errors():
    words = speech_verify.normalized_words
    assert words("Focus 20, then C-1.", "en") == words("FOCUS TWENTY THEN C ONE", "en")
    assert words("Plus Inflate", "en") != words("Plus Deflate", "en")
    assert words("Don't.", "en") != words("Do.", "en")
    assert words("Go now.", "en") != words("Go, go now.", "en")
    assert words("1", "fr") != words("un", "fr")


@pytest.mark.unit
def test_real_batch_requires_local_model_and_dry_run_does_not(monkeypatch):
    monkeypatch.delenv("OCF_WHISPER_MODEL", raising=False)
    guarded = bulk_render._default_speech_verification(lambda **kwargs: kwargs)
    assert guarded(dry_run=True) == {"dry_run": True}
    with pytest.raises(OCFError, match="set OCF_WHISPER_MODEL"):
        guarded()


@pytest.mark.parametrize("cache_hit", [False, True])
@pytest.mark.unit
def test_hook_checks_returned_audio_for_fresh_and_cached_cues(monkeypatch, cache_hit):
    calls = []
    monkeypatch.setattr(voice, "_render_cue_wav", lambda *_: calls.append("generated") or b"fresh")
    monkeypatch.setattr(
        speech_cache, "cached_cue", lambda spec, text, render: b"cached" if cache_hit else render()
    )

    class Verifier:
        def verify(self, data, text, locale):
            calls.append((data, text, locale))
            raise OCFError("test review required")

    with speech_verify.verification_scope(Verifier()):
        with pytest.raises(OCFError, match="review required"):
            voice.render_cue_wav({"locale": "en-US"}, "Plus Inflate")
    assert calls[-1] == (b"cached" if cache_hit else b"fresh", "Plus Inflate", "en-US")
    assert ("generated" in calls) != cache_hit


@pytest.mark.unit
def test_gate_memo_is_keyed_to_pcm_and_text_and_exact_cues(monkeypatch, tmp_path):
    for file in ("config.json", "model.bin", "tokenizer.json"):
        (tmp_path / file).write_bytes(b"fixture")
    monkeypatch.setattr(speech_verify.subprocess, "check_output", lambda *_, **__: "{}")
    v = speech_verify.WhisperVerifier(tmp_path)
    jobs = []

    def transcribe(data, language):
        jobs.append((data, language))
        return "Plus Inflate" if data == b"clean" else "Plus Deflate"

    monkeypatch.setattr(v, "_transcribe", transcribe)
    with nullcontext(v), speech_verify.verification_scope(v) as rows:
        speech_verify.verify_tts(b"clean", "Plus Inflate", "en-US")
        speech_verify.verify_tts(b"clean", "Plus Inflate", "en-US")
        with pytest.raises(OCFError, match="first differing word 2"):
            speech_verify.verify_tts(b"garbled", "Plus Inflate", "en-US")
        with pytest.raises(OCFError, match="first differing word 2"):
            speech_verify.verify_tts(b"clean", "Plus Deflate", "en-US")
    assert jobs == [(b"clean", "en"), (b"garbled", "en"), (b"clean", "en")]
    assert rows[0] == rows[1]
    assert len(speech_verify.evidence(v, rows)["segments"]) == 2


@pytest.mark.integration
def test_external_worker_protocol_stays_running_and_fails_closed(monkeypatch, tmp_path):
    for file in ("config.json", "model.bin", "tokenizer.json"):
        (tmp_path / file).write_bytes(b"fixture")
    monkeypatch.setattr(
        speech_verify.subprocess, "check_output", lambda *_, **__: '{"fixture":"1"}'
    )
    v = speech_verify.WhisperVerifier(tmp_path)
    driver = tmp_path / "fixture.py"
    driver.write_text(
        "import base64,json,os,sys\n"
        "assert os.environ['HF_HUB_OFFLINE'] == '1'\n"
        "assert os.environ['TRANSFORMERS_OFFLINE'] == '1'\n"
        "for line in sys.stdin:\n"
        "    job = json.loads(line)\n"
        "    assert set(job) == {'wav','language','settings'}\n"
        "    assert job['language'] == 'en'\n"
        "    pcm = base64.b64decode(job['wav'])\n"
        "    result = {'error':'model unavailable'} if pcm == b'err' else "
        "{'text':'Go now','runtime':{'fixture':'1'}}\n"
        "    print(json.dumps(result),flush=True)\n"
    )
    v._worker = driver
    with v:
        v.verify(b"first", "Go now.", "en-US")
        process = v._process
        v.verify(b"second", "go now!", "en-US")
        assert v._process is process
        with pytest.raises(OCFError, match="model unavailable"):
            v.verify(b"err", "Go now", "en-US")
        with pytest.raises(OCFError, match="unavailable for this render"):
            v.verify(b"third", "Go now", "en-US")
    assert process.poll() is not None
