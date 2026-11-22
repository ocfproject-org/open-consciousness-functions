"""Fail-closed offline recognition for release-path TTS bytes."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from queue import Empty, Queue

from .utils import OCFError, sha256_of_file

POLICY = "ocf-whisper-exact-words/1"
DECODE_TIMEOUT_S = 300
SETTINGS = {
    "beam_size": 5,
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "vad_filter": False,
}
# Tested and separately reviewed Focus Eleven closing cue only. This is not
# an alias: "axis" remains a mismatch, including for both witness decoders.
_ACCESS_CUE_SHA256 = "2623366803337ddc35f3a67e7718d6081d1b8b1daf492d8769bd388c9864a7e0"
_ACCESS_EXACT_WORDS = "851a7b8d5d3d7e54479fc2b02e4fa96c81483a2baf8eb093b868b0e35486a1e5"
_ACCESS_PRIMARY_WRONG_WORDS = "a36fa5f51363516e1bcb897b61dfa9019bb82e7bc352c8a78c32a4cc6a52d0b2"
_ACCESS_POLICY = "ocf-en-us-focus11-close-dual-witness/1"
_ACCESS_SNAPSHOTS = {
    "primary": "ae1b67ef9f88f5cec7f51cdf198a163419c5a7529ae85c7ecac18d5cebd98511",
    "medium": "42b4fc8318ad06a380dbfbcca75135c6b2f9db219f417cefc72a2d51f6c5ca89",
    "small": "40f0d23210624a91a050b5f38dc16e7957211c5f44439babd9cdcef5b1eff3bb",
}
_ACCESS_RUNTIME = {"faster-whisper": "1.2.1", "ctranslate2": "4.8.2"}
_ACCESS_SETTINGS = {
    "device": "cpu",
    "compute_type": "int8",
    "beam_size": 5,
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "vad_filter": False,
}
_ACCESS_ENV = ("OCF_WHISPER_ACCESS_MEDIUM_MODEL", "OCF_WHISPER_ACCESS_SMALL_MODEL")

_active: ContextVar = ContextVar("tts_whisper_verification", default=None)
_SMALL = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


class SpeechMismatch(OCFError):
    """A completed local ASR check that did not match the expected words."""

    def __init__(
        self,
        *,
        locale,
        wav_sha256,
        text_sha256,
        first_difference,
        expected,
        heard,
        recognized_sha256=None,
        normalized_recognized_sha256=None,
    ):
        self.diagnostic = {
            "locale": locale,
            "wav_sha256": wav_sha256,
            "text_sha256": text_sha256,
            "first_differing_word": first_difference,
            "expected_words": expected,
            "heard_words": heard,
            "recognized_sha256": recognized_sha256,
            "normalized_recognized_sha256": normalized_recognized_sha256,
        }
        super().__init__(
            f"Whisper review required ({locale}, PCM {wav_sha256[:12]}, "
            f"text {text_sha256[:12]}): first differing word {first_difference}, "
            f"expected {expected} words, heard {heard}. "
            "Review this clip locally before releasing it."
        )


def _json_sha256(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalized_words(text: str, language: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"(?<=\w)[’'](?=\w)", "", text)
    if language == "en":
        text = re.sub(r"\bc\s*(?:-\s*)?1\b", "c one", text)
        text = re.sub(r"(?<=\d)\.(?=\d)", " point ", text)
    result = []
    for word in re.findall(r"[^\W_]+", text):
        if language == "en" and re.fullmatch(r"0|[1-9][0-9]?", word):
            value = int(word)
            if value < 20:
                result.append(_SMALL[value])
            else:
                result.append(_TENS[value // 10])
                if value % 10:
                    result.append(_SMALL[value % 10])
        else:
            result.append(word)
    return tuple(result)


@lru_cache(maxsize=4)
def _fingerprint(entries):
    return {name: sha256_of_file(path) for name, path, *_ in entries}


class WhisperVerifier:
    """One offline process shared by a render batch; serializes model inference."""

    def __init__(self, model: Path, python: str | None = None):
        self.model = model.resolve()
        required = [self.model / name for name in ("model.bin", "config.json", "tokenizer.json")]
        if not all(path.is_file() for path in required):
            raise OCFError(
                "Offline Whisper requires a complete local CTranslate2 snapshot (model.bin, config.json, tokenizer.json)"
            )
        self.python = python or sys.executable
        self._worker = Path(__file__).with_name("speech_verify_worker.py")
        self._files = self._snapshot_files()
        try:
            runtime = json.loads(
                subprocess.check_output(
                    [
                        self.python,
                        "-c",
                        "from importlib.metadata import version; import json; print(json.dumps({n:version(n) for n in ('faster-whisper','ctranslate2')}))",
                    ],
                    timeout=20,
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise OCFError(
                "Offline Whisper interpreter is unavailable or lacks faster-whisper/CTranslate2"
            ) from exc
        self.identity = {
            "runtime": runtime,
            "policy": POLICY,
            "settings": {"device": "cpu", "compute_type": "int8", **SETTINGS},
            "model_sha256": _fingerprint(self._files),
            "worker_sha256": sha256_of_file(self._worker),
            "verifier_sha256": sha256_of_file(Path(__file__)),
        }
        self._process = None
        self._lock = threading.Lock()
        self._memo: dict = {}
        self._unavailable = False

    def _snapshot_files(self):
        entries = []
        for path in sorted(self.model.iterdir()):
            if path.is_file():
                stat = path.stat()
                entries.append(
                    (
                        path.name,
                        path,
                        stat.st_dev,
                        stat.st_ino,
                        stat.st_size,
                        stat.st_mtime_ns,
                        stat.st_ctime_ns,
                    )
                )
        return tuple(entries)

    def snapshot_current(self) -> bool:
        try:
            return self._snapshot_files() == self._files
        except OSError:
            return False

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("OCF_WHISPER_MODEL")
        if not raw:
            raise OCFError(
                "Offline Whisper verification is required: set OCF_WHISPER_MODEL to an "
                "installed local faster-whisper snapshot and optionally OCF_WHISPER_PYTHON "
                "to the interpreter with faster-whisper installed"
            )
        python = os.environ.get("OCF_WHISPER_PYTHON")
        medium, small = (os.environ.get(var) for var in _ACCESS_ENV)
        if bool(medium) != bool(small):
            raise OCFError("Focus Eleven close witness mode requires both local snapshots")
        primary = cls(Path(raw), python)
        if medium and small:
            return CloseCueWitnessVerifier(
                primary, cls(Path(medium), python), cls(Path(small), python)
            )
        return primary

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def close(self):
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            if self._process.stdin is not None:
                self._process.stdin.close()
            if self._process.stdout is not None:
                self._process.stdout.close()
            self._process = None

    @staticmethod
    def _exchange(request, stdin, stdout, responses):
        try:
            stdin.write(request + "\n")
            stdin.flush()
            line = stdout.readline()
            responses.put(line or OSError("Whisper worker exited"))
        except (OSError, ValueError) as exc:
            responses.put(exc)

    def _transcribe(self, wav: bytes, language: str) -> str:
        if self._unavailable:
            raise OCFError("Offline Whisper is unavailable for this render")
        try:
            if self._process is None:
                self._process = subprocess.Popen(
                    [
                        self.python,
                        "-I",
                        "-c",
                        "import runpy,sys; runpy.run_path(sys.argv.pop(1), run_name='__main__')",
                        str(self._worker),
                        str(self.model),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                )
            assert self._process.stdin is not None and self._process.stdout is not None
            request = {
                "wav": base64.b64encode(wav).decode("ascii"),
                "language": language,
                "settings": SETTINGS,
            }
            responses: Queue = Queue(maxsize=1)
            # A stalled worker can fill stdin's pipe before it reads the large
            # PCM request. Bound the write and response together.
            threading.Thread(
                target=self._exchange,
                args=(json.dumps(request), self._process.stdin, self._process.stdout, responses),
                daemon=True,
            ).start()
            try:
                line = responses.get(timeout=DECODE_TIMEOUT_S)
            except Empty as exc:
                raise OSError(
                    "Whisper worker timed out transmitting or transcribing a clip"
                ) from exc
            if isinstance(line, Exception):
                raise line
            response = json.loads(line)
            if response.get("error"):
                raise OSError(str(response["error"]))
            if not isinstance(response.get("text"), str):
                raise ValueError("Whisper worker returned no transcript")
            runtime = response.get("runtime")
            if self.identity["runtime"] != runtime:
                raise ValueError("Whisper runtime changed during verification")
            return response["text"]
        except (OSError, ValueError) as exc:
            self._unavailable = True
            self.close()
            raise OCFError(f"Offline Whisper failed; no audio approved: {exc}") from exc

    def verify(self, wav: bytes, expected: str, locale: str) -> dict:
        language = locale.casefold().split("-")[0] if locale else ""
        if not re.fullmatch("[a-z]{2,3}", language):
            raise OCFError("Offline Whisper requires an explicit supported narration locale")
        audio_hash = hashlib.sha256(wav).hexdigest()
        text_hash = hashlib.sha256(expected.encode("utf-8")).hexdigest()
        key = (audio_hash, text_hash, locale)
        with self._lock:
            if key not in self._memo:
                observed = self._transcribe(wav, language)
                if len(self._memo) >= 8192:
                    self._memo.clear()
                self._memo[key] = observed
            else:
                observed = self._memo[key]
        want = normalized_words(expected, language)
        got = normalized_words(observed, language)
        if not want or want != got:
            # Do not expose private speech in shared dashboards or logs.
            offset = next(
                (i for i, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got))
            )
            raise SpeechMismatch(
                locale=locale,
                wav_sha256=audio_hash,
                text_sha256=text_hash,
                first_difference=offset + 1,
                expected=len(want),
                heard=len(got),
                recognized_sha256=hashlib.sha256(observed.encode("utf-8")).hexdigest(),
                normalized_recognized_sha256=_json_sha256(got),
            )
        return {
            "wav_sha256": audio_hash,
            "text_sha256": text_hash,
            "locale": locale,
            "recognized_sha256": hashlib.sha256(observed.encode("utf-8")).hexdigest(),
        }


class CloseCueWitnessVerifier:
    """Two pinned exact offline witnesses, only for the observed en-US decode."""

    def __init__(self, primary, medium, small):
        self.decoders = {"primary": primary, "medium": medium, "small": small}
        self._check_decoders()
        # Binding the entire actual decoder identities protects batch resume
        # and keeps the configuration paths themselves out of receipts.
        self.identity = {
            "policy": _ACCESS_POLICY,
            "expected_text_sha256": _ACCESS_CUE_SHA256,
            "locale": "en-US",
            "expected_normalized_words_sha256": _ACCESS_EXACT_WORDS,
            "primary_mismatch_normalized_words_sha256": _ACCESS_PRIMARY_WRONG_WORDS,
            "decoders": {name: decoder.identity for name, decoder in self.decoders.items()},
        }

    def _check_decoders(self) -> None:
        for name, decoder in self.decoders.items():
            identity = decoder.identity
            if (
                not decoder.snapshot_current()
                or _json_sha256(identity.get("model_sha256")) != _ACCESS_SNAPSHOTS[name]
                or identity.get("runtime") != _ACCESS_RUNTIME
                or identity.get("settings") != _ACCESS_SETTINGS
            ):
                raise OCFError(
                    f"Focus Eleven close {name} decoder identity/decode settings do not match the pinned proof"
                )

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        for decoder in self.decoders.values():
            decoder.close()

    def verify(self, wav: bytes, expected: str, locale: str) -> dict:
        try:
            return self.decoders["primary"].verify(wav, expected, locale)
        except SpeechMismatch as primary:
            waveform = hashlib.sha256(wav).hexdigest()
            text = hashlib.sha256(expected.encode("utf-8")).hexdigest()
            prior = primary.diagnostic
            if (
                locale != "en-US"
                or text != _ACCESS_CUE_SHA256
                or _json_sha256(normalized_words(expected, "en")) != _ACCESS_EXACT_WORDS
                or prior["locale"] != locale
                or prior["wav_sha256"] != waveform
                or prior["text_sha256"] != text
                or (prior["first_differing_word"], prior["expected_words"], prior["heard_words"])
                != (10, 10, 10)
                or prior["normalized_recognized_sha256"] != _ACCESS_PRIMARY_WRONG_WORDS
                or not isinstance(prior["recognized_sha256"], str)
                or not re.fullmatch("[0-9a-f]{64}", prior["recognized_sha256"])
            ):
                raise
            self._check_decoders()
            witnesses = {}
            for name in ("medium", "small"):
                decoder = self.decoders[name]
                # A witness failure propagates; nothing is accepted on either
                # a partial quorum or a near-match. No text supplied to ASR.
                proof = decoder.verify(wav, expected, locale)
                if (
                    proof.get("wav_sha256") != waveform
                    or proof.get("text_sha256") != text
                    or proof.get("locale") != locale
                    or not isinstance(proof.get("recognized_sha256"), str)
                    or not re.fullmatch("[0-9a-f]{64}", proof["recognized_sha256"])
                ):
                    raise OCFError("Focus Eleven close witness returned invalid same-byte evidence")
                witnesses[name] = {
                    **proof,
                    "decoder_identity_sha256": _json_sha256(decoder.identity),
                }
            self._check_decoders()
            return {
                "wav_sha256": waveform,
                "text_sha256": text,
                "locale": locale,
                "recognized_sha256": witnesses["medium"]["recognized_sha256"],
                "exact_normalized_words_sha256": _ACCESS_EXACT_WORDS,
                "decoder_policy": _ACCESS_POLICY,
                "primary_disagreement": {
                    **prior,
                    "decoder_identity_sha256": _json_sha256(self.decoders["primary"].identity),
                },
                "witnesses": witnesses,
            }


@contextmanager
def verification_scope(verifier):
    rows: list[dict] = []
    token = _active.set((verifier, rows) if verifier is not None else None)
    try:
        yield rows
    finally:
        _active.reset(token)


def verify_tts(
    wav: bytes, text: str, locale: str, *, source: str = "unknown", take: int | None = None
) -> None:
    active = _active.get()
    if active is not None:
        verifier, rows = active
        try:
            rows.append(verifier.verify(wav, text, locale))
        except SpeechMismatch as exc:
            rows.append({**exc.diagnostic, "result": "mismatch", "source": source, "take": take})
            raise


def evidence(verifier, rows: list[dict]) -> dict:
    verified = [row for row in rows if row.get("result") != "mismatch"]
    rejected = [row for row in rows if row.get("result") == "mismatch"]
    if not verified:
        raise OCFError(
            "Offline Whisper verified no TTS segments; review recording-source inputs separately"
        )
    return {
        "verifier": verifier.identity,
        "segments": verified,
        "rejected_attempts": rejected,
    }
