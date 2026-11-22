"""Local JSON-lines Whisper driver; also runs under external Python 3.9+."""

import base64
import io
import json
import os
import sys
from importlib.metadata import version
from pathlib import Path


def main():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    model = None
    for line in sys.stdin:
        try:
            if model is None:
                from faster_whisper import WhisperModel

                model = WhisperModel(
                    str(Path(sys.argv[1]).resolve(strict=True)),
                    device="cpu",
                    compute_type="int8",
                    local_files_only=True,
                )
                runtime = {name: version(name) for name in ("faster-whisper", "ctranslate2")}
            job = json.loads(line)
            segments, _ = model.transcribe(
                io.BytesIO(base64.b64decode(job["wav"], validate=True)),
                language=job["language"],
                initial_prompt=None,
                **job["settings"],
            )
            result = {"text": " ".join(segment.text for segment in segments), "runtime": runtime}
        except Exception as exc:
            result = {"error": type(exc).__name__ + ": " + str(exc)}
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
