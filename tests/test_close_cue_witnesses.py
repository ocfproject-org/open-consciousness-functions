import hashlib
import threading
from copy import deepcopy

import pytest
from ocf_tools import speech_verify as sv
from ocf_tools.utils import OCFError

pytestmark = pytest.mark.unit

EXACT = 'Think or say in your mind, "Plus Release Eleven Access."'
AXIS = "Think or say in your mind, plus release 11-axis."
ACCESS = "Think or say in your mind, plus release 11 access."
PCM = b"one exact waveform"


class Stub:
    def __init__(self, role, heard):
        self.heard = heard
        self._memo = {}
        self._lock = threading.Lock()
        self.calls = []
        self.altered = False
        self.identity = {
            "runtime": deepcopy(sv._ACCESS_RUNTIME),
            "settings": deepcopy(sv._ACCESS_SETTINGS),
            "model_sha256": {"model.bin": hashlib.sha256(role.encode()).hexdigest()},
        }

    def snapshot_current(self):
        return not self.altered

    def _transcribe(self, wav, language):
        self.calls.append((wav, language))
        return self.heard

    def verify(self, wav, expected, locale):
        return sv.WhisperVerifier.verify(self, wav, expected, locale)

    def close(self):
        pass


@pytest.fixture
def roles(monkeypatch):
    decoders = (Stub("primary", AXIS), Stub("medium", ACCESS), Stub("small", ACCESS))
    fields = {
        name: sv._json_sha256(stub.identity["model_sha256"])
        for name, stub in zip(("primary", "medium", "small"), decoders, strict=True)
    }
    monkeypatch.setattr(sv, "_ACCESS_SNAPSHOTS", fields)
    return decoders


def test_same_pcm_receipts_require_both_independent_exact_decodes(roles):
    with sv.CloseCueWitnessVerifier(*roles) as verifier:
        proof = verifier.verify(PCM, EXACT, "en-US")
    assert [role.calls for role in roles] == [[(PCM, "en")]] * 3
    assert proof["primary_disagreement"]["first_differing_word"] == 10
    wav_sha = hashlib.sha256(PCM).hexdigest()
    assert proof["wav_sha256"] == proof["primary_disagreement"]["wav_sha256"] == wav_sha
    assert all(w["wav_sha256"] == wav_sha for w in proof["witnesses"].values())
    assert len({w["decoder_identity_sha256"] for w in proof["witnesses"].values()}) == 2
    assert proof["exact_normalized_words_sha256"] == sv._ACCESS_EXACT_WORDS
    assert proof["primary_disagreement"]["recognized_sha256"] != proof["recognized_sha256"]
    assert proof["primary_disagreement"]["normalized_recognized_sha256"] != sv._ACCESS_EXACT_WORDS


@pytest.mark.parametrize(
    ("expected", "heard", "locale"),
    [
        (EXACT, "Think or say in your mind, plus keep eleven axis.", "en-US"),
        (EXACT, "Think or say in your mind, plus release eleven ashes.", "en-US"),
        (EXACT, AXIS, "en-GB"),
        (EXACT.replace("Access", "Action"), AXIS, "en-US"),
        (EXACT.replace("Access", "Access "), AXIS, "en-US"),  # same words, wrong full SHA
    ],
)
def test_other_shapes_locales_and_expected_text_hashes_never_trigger_witnesses(
    roles, expected, heard, locale
):
    roles[0].heard = heard
    verifier = sv.CloseCueWitnessVerifier(*roles)
    with pytest.raises(sv.SpeechMismatch):
        verifier.verify(PCM, expected, locale)
    assert not roles[1].calls and not roles[2].calls


def test_primary_success_keeps_original_receipt_and_skips_secondary_decoders(roles):
    roles[0].heard = ACCESS
    verifier = sv.CloseCueWitnessVerifier(*roles)
    assert verifier.verify(PCM, EXACT, "en-US") == roles[0].verify(PCM, EXACT, "en-US")
    assert not roles[1].calls and not roles[2].calls


@pytest.mark.parametrize("witness", [1, 2])
def test_near_match_from_either_witness_fails_closed(roles, witness):
    roles[witness].heard = AXIS
    with pytest.raises(sv.SpeechMismatch):
        sv.CloseCueWitnessVerifier(*roles).verify(PCM, EXACT, "en-US")


def test_corrupt_or_changed_snapshot_and_decoder_runtime_fail_closed(roles):
    verifier = sv.CloseCueWitnessVerifier(*roles)
    roles[2].altered = True
    with pytest.raises(OCFError, match="small decoder identity"):
        verifier.verify(PCM, EXACT, "en-US")
    roles[2].altered = False
    roles[1].identity["runtime"]["ctranslate2"] = "999"
    with pytest.raises(OCFError, match="medium decoder identity"):
        sv.CloseCueWitnessVerifier(*roles)


def test_wrong_waveform_attestation_and_missing_witness_are_rejected(roles, monkeypatch):
    orig = roles[2].verify
    roles[2].verify = lambda *args: {**orig(*args), "wav_sha256": "f" * 64}
    with pytest.raises(OCFError, match="invalid same-byte"):
        sv.CloseCueWitnessVerifier(*roles).verify(PCM, EXACT, "en-US")
    monkeypatch.setenv("OCF_WHISPER_MODEL", "/local/model")
    monkeypatch.setenv("OCF_WHISPER_ACCESS_MEDIUM_MODEL", "/local/medium")
    monkeypatch.delenv("OCF_WHISPER_ACCESS_SMALL_MODEL", raising=False)
    with pytest.raises(OCFError, match="both local"):
        sv.WhisperVerifier.from_environment()


def test_unavailable_witness_does_not_approve_or_turn_into_speech_mismatch(roles):
    def offline(*_):
        raise OCFError("witness unavailable")

    roles[1].verify = offline
    with pytest.raises(OCFError, match="witness unavailable") as exc:
        sv.CloseCueWitnessVerifier(*roles).verify(PCM, EXACT, "en-US")
    assert not isinstance(exc.value, sv.SpeechMismatch)
    assert not roles[2].calls
