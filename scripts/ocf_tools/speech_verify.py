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
SETTINGS = {
    "beam_size": 5,
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "vad_filter": False,
}
_active: ContextVar = ContextVar("tts_whisper_verification", default=None)
_SMALL = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


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
        self._files = tuple(
            (p.name, p, p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(self.model.iterdir())
            if p.is_file()
        )
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
        self._responses: Queue = Queue()
        self._memo: dict = {}
        self._unavailable = False

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("OCF_WHISPER_MODEL")
        if not raw:
            raise OCFError(
                "Offline Whisper verification is required: set OCF_WHISPER_MODEL to an "
                "installed local faster-whisper snapshot and optionally OCF_WHISPER_PYTHON "
                "to the interpreter with faster-whisper installed"
            )
        return cls(Path(raw), os.environ.get("OCF_WHISPER_PYTHON"))

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

    def _reader(self, stream):
        for line in stream:
            self._responses.put(line)
        self._responses.put(None)

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
                assert self._process.stdout is not None
                threading.Thread(
                    target=self._reader, args=(self._process.stdout,), daemon=True
                ).start()
            assert self._process.stdin is not None
            request = {
                "wav": base64.b64encode(wav).decode("ascii"),
                "language": language,
                "settings": SETTINGS,
            }
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
            line = self._responses.get(timeout=300)
            if line is None:
                raise OSError("Whisper worker exited")
            response = json.loads(line)
            if response.get("error"):
                raise OSError(str(response["error"]))
            if not isinstance(response.get("text"), str):
                raise ValueError("Whisper worker returned no transcript")
            runtime = response.get("runtime")
            if self.identity["runtime"] != runtime:
                raise ValueError("Whisper runtime changed during verification")
            return response["text"]
        except (Empty, OSError, ValueError) as exc:
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
            raise OCFError(
                f"Whisper review required ({locale}, PCM {audio_hash[:12]}, text {text_hash[:12]}): "
                f"first differing word {offset + 1}, expected {len(want)} words, heard {len(got)}. "
                "Review this clip locally before releasing it."
            )
        return {
            "wav_sha256": audio_hash,
            "text_sha256": text_hash,
            "locale": locale,
            "recognized_sha256": hashlib.sha256(observed.encode("utf-8")).hexdigest(),
        }


@contextmanager
def verification_scope(verifier):
    rows: list[dict] = []
    token = _active.set((verifier, rows) if verifier is not None else None)
    try:
        yield rows
    finally:
        _active.reset(token)


def verify_tts(wav: bytes, text: str, locale: str) -> None:
    active = _active.get()
    if active is not None:
        verifier, rows = active
        rows.append(verifier.verify(wav, text, locale))


def evidence(verifier, rows: list[dict]) -> dict:
    if not rows:
        raise OCFError(
            "Offline Whisper verified no TTS segments; review recording-source inputs separately"
        )
    return {"verifier": verifier.identity, "segments": rows}
