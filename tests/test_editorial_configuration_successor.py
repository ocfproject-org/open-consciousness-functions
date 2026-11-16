"""Audio-default locks cover engineering inputs, not editable function text."""

import json

import pytest
from ocf_tools import audio_defaults
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration


def _engine_path(path: str) -> bool:
    return path.startswith(("audio/templates/", "audio/background/"))


def test_current_defaults_lock_is_independent_of_locale_and_editorial_yaml():
    predecessor_path = REPO_ROOT / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-025.json"
    predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
    lock = audio_defaults.check_lock()

    assert lock["id"] == "OCF-AUDIO-DEFAULTS-HPLUS-026"
    assert audio_defaults.PREVIOUS_BASELINE_ID == predecessor["id"]
    assert lock["profiles"] == predecessor["profiles"]
    assert lock["human_listening_approval"] is None
    assert lock["release_ready"] is False

    expected_excluded = {path for path in predecessor["files"] if not _engine_path(path)}
    assert set(lock["excluded_predecessor_files"]) == expected_excluded
    assert set(predecessor["files"]) - expected_excluded <= set(lock["files"])
    assert all(_engine_path(path) for path in lock["files"])
    assert not any(path.startswith("locales/") for path in lock["files"])
    assert not any(path.startswith(("function-content/", "tests/")) for path in lock["files"])


def test_predecessor_audio_default_versions_remain_available():
    for number in range(1, 26):
        path = REPO_ROOT / "audio/defaults" / f"OCF-AUDIO-DEFAULTS-HPLUS-{number:03}.json"
        assert path.is_file(), path.name
        baseline = json.loads(path.read_text(encoding="utf-8"))
        assert baseline["human_listening_approval"] is None
        assert baseline["release_ready"] is False
