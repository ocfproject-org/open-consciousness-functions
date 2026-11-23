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


def test_prebuilt_public_site_gets_inline_private_player_and_standalone_link(tmp_path, monkeypatch):
    batch, _ = valid(tmp_path, monkeypatch)
    pages = tmp_path / "pages"
    write(
        pages / "documentation-index.json",
        {"functions": [{"function_id": "OCF-EXP-007", "href": "functions/OCF-EXP-007/"}]},
    )
    markup = "<head></head><main>Production anchor</main>"
    pages.mkdir(exist_ok=True)
    (pages / "index.html").write_text(markup)
    page = pages / "functions/OCF-EXP-007/index.html"
    page.parent.mkdir(parents=True)
    page.write_text(markup)
    write(pages / "catalog.json", {"only": "existing-public-editions"})
    out = tmp_path / "review"
    review.build_review(batch, out, locale="en-US", edition_version="1.0.0", pages=pages)
    guide = out / "functions/OCF-EXP-007/index.html"
    content = guide.read_text()
    assert 'href="/_local-audition/OCF-EXP-007.html"' in content
    assert '<audio controls preload="none" src="/_local-audition/audio/OCF-EXP-007.mp3">' in content
    assert 'href="/_local-audition/audio/OCF-EXP-007.flac" download' in content
    assert (out / "_local-audition/OCF-EXP-007.html").exists()
    assert (out / "catalog.json").read_bytes() == (pages / "catalog.json").read_bytes()
    assert page.read_text() == markup


def test_pages_config_runs_real_cli_contract_and_rejects_wrong_pin(tmp_path, monkeypatch):
    from ocf_tools import public_site_export

    source_commit = "1" * 40
    audio_repo = tmp_path / "audio-repo"
    write(audio_repo / "site/source.json", {"source_commit": source_commit})
    write(audio_repo / "scripts/build_public_site.py", {})
    write(audio_repo / "scripts/validate_site.py", {})
    write(tmp_path / "catalog.json", {})
    media = tmp_path / "comfort.mp3"
    media.write_bytes(b"fixture only")
    (tmp_path / "transcripts").mkdir()
    cfg = write(
        tmp_path / "config.json",
        {
            "audio_repository": "audio-repo",
            "verified_catalog": "catalog.json",
            "smart_playback_media": "comfort.mp3",
            "published_transcript_mirror": "transcripts",
        },
    )
    calls = []

    def fake_git(argv, **kwargs):
        return source_commit if "rev-parse" in argv else ""

    def fake_pages(argv, **kwargs):
        assert kwargs["cwd"] == audio_repo and kwargs["check"]
        calls.append(argv)

    monkeypatch.setattr(review.subprocess, "check_output", fake_git)
    monkeypatch.setattr(review.subprocess, "run", fake_pages)
    monkeypatch.setattr(
        public_site_export,
        "write_export",
        lambda p, source_commit: write(p, {"source": source_commit}),
    )
    assert review.build_pages(cfg, tmp_path) == tmp_path / "pages-build"
    assert calls[0][1].endswith("/scripts/build_public_site.py")
    assert "--historical-reference" in calls[0] and "--smart-playback-media" in calls[0]
    assert calls[0][calls[0].index("--published-transcript-mirror") + 1] == str(
        tmp_path / "transcripts"
    )
    assert calls[1][1].endswith("/scripts/validate_site.py")
    write(audio_repo / "site/source.json", {"source_commit": "2" * 40})
    with pytest.raises(OCFError, match="same source revision"):
        review.build_pages(cfg, tmp_path)
    assert len(calls) == 2
