import hashlib
import json

import pytest
from ocf_tools import local_batch_review as review
from ocf_tools.utils import OCFError


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def valid(tmp, monkeypatch):
    root = tmp / "recording"
    rel = "spoken.wav"
    root.mkdir()
    wav = root / rel
    wav.write_bytes(b"local fake audio")

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    report = write(
        root / "session-report.json",
        {
            "function_id": "OCF-EXP-007",
            "requested_locale": "en-US",
            "title": "<Not HTML>",
            "artifacts": {
                "wav": {"path": rel, "size_bytes": wav.stat().st_size, "sha256": sha(wav)}
            },
        },
    )
    speech = write(
        root / "speech-verification.json",
        {
            "verifier": {"test": True},
            "segments": [
                {
                    "locale": "en-US",
                    "text_sha256": "a" * 64,
                    "recognized_sha256": "b" * 64,
                    "wav_sha256": "c" * 64,
                }
            ],
        },
    )
    cache = tmp / "cache"
    key = "d" * 64
    write(
        cache / (key + ".json"),
        {
            "key": key,
            "output_directory": str(root),
            "manifest_sha256": sha(report),
            "speech_verification_sha256": sha(speech),
        },
    )
    batch = {
        "failed": 0,
        "blocked": 0,
        "dry_run": False,
        "results": [
            {
                "function_id": "OCF-EXP-007",
                "output_directory": str(root),
                "status": "skipped-verified",
            }
        ],
    }

    def export(source, *, output, **kwargs):
        assert source == root
        output.mkdir()
        artifacts = {}
        for ext in ("mp3", "flac"):
            file = output / ("fixture." + ext)
            file.write_bytes(ext.encode())
            artifacts[ext] = {"path": file.name, "sha256": sha(file)}
        write(output / "manifest.json", {"artifacts": artifacts})

    monkeypatch.setattr(
        review, "work_path", lambda area, *parts: cache if area == "cache" else tmp / "renders"
    )
    monkeypatch.setattr("ocf_tools.audition_exports.export_audition", export)
    return batch, sha


def test_stage_native_batch_without_publication(tmp_path, monkeypatch):
    batch, digest = valid(tmp_path, monkeypatch)
    out = tmp_path / "preview"
    result = review.build_review(batch, out, locale="en-US", edition_version="1.0.0")
    assert result["publication_approval"] is False
    assert result["recordings"] == 1
    landing = (out / "index.html").read_text()
    assert "noindex,nofollow" in landing and "&lt;Not HTML&gt;" in landing
    assert 'controls preload="none"' in (out / "OCF-EXP-007.html").read_text()
    result = json.loads((out / "local-review.json").read_text())
    assert result["routes"]["audio/OCF-EXP-007.mp3"] == digest(out / "audio/OCF-EXP-007.mp3")
    assert result["routes"]["audio/OCF-EXP-007.flac"] == digest(out / "audio/OCF-EXP-007.flac")


@pytest.mark.parametrize("bad", ["held", "different-wave", "different-proof"])
def test_do_not_stage_partial_or_tampered_batch(tmp_path, monkeypatch, bad):
    batch, _ = valid(tmp_path, monkeypatch)
    if bad == "held":
        batch["blocked"] = 1
    else:
        local = (
            tmp_path
            / "recording"
            / ("spoken.wav" if bad == "different-wave" else "speech-verification.json")
        )
        local.write_bytes(b"replacement")
    out = tmp_path / "preview"
    with pytest.raises(OCFError):
        review.build_review(batch, out, locale="en-US", edition_version="1.0.0")
    assert not out.exists()
