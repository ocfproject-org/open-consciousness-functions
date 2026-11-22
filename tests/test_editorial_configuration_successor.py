"""Audio-default locks cover engineering inputs, not editable function text."""

import json

import pytest
from ocf_tools import audio_defaults
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration


def _engine_path(path: str) -> bool:
    return path.startswith(("audio/templates/", "audio/background/"))


def test_historical_026_lock_excludes_editorial_inputs_from_025():
    root = REPO_ROOT / "audio/defaults"
    predecessor = json.loads(
        (root / "OCF-AUDIO-DEFAULTS-HPLUS-025.json").read_text(encoding="utf-8")
    )
    lock = json.loads((root / "OCF-AUDIO-DEFAULTS-HPLUS-026.json").read_text(encoding="utf-8"))
    assert lock["profiles"] == predecessor["profiles"]
    expected_excluded = {path for path in predecessor["files"] if not _engine_path(path)}
    assert set(lock["excluded_predecessor_files"]) == expected_excluded
    assert set(predecessor["files"]) - expected_excluded <= set(lock["files"])
    assert all(_engine_path(path) for path in lock["files"])
    assert lock["human_listening_approval"] is None and lock["release_ready"] is False


def test_current_defaults_lock_is_independent_of_locale_and_editorial_yaml():
    path = REPO_ROOT / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-026.json"
    predecessor = json.loads(path.read_text(encoding="utf-8"))
    lock = audio_defaults.check_lock()

    assert lock["id"] == "OCF-AUDIO-DEFAULTS-HPLUS-027"
    assert audio_defaults.PREVIOUS_BASELINE_ID == predecessor["id"]
    assert lock["profiles"] == {
        **predecessor["profiles"],
        "template": {"id": "OCF-TPL-SESSION-HPLUS-LOCKED-008", "version": "8.0.0"},
    }
    assert lock["human_listening_approval"] is None and lock["release_ready"] is False
    assert lock["excluded_predecessor_files"] == []
    assert all(lock["files"][name] == sha for name, sha in predecessor["files"].items())
    assert all(_engine_path(path) for path in lock["files"])


def test_predecessor_audio_default_versions_remain_available():
    for number in range(1, 27):
        path = REPO_ROOT / "audio/defaults" / f"OCF-AUDIO-DEFAULTS-HPLUS-{number:03}.json"
        assert path.is_file(), path.name
        baseline = json.loads(path.read_text(encoding="utf-8"))
        assert baseline["human_listening_approval"] is None
        assert baseline["release_ready"] is False
