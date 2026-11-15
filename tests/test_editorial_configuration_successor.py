"""Unmerged source configuration identity is not listening/release approval."""

import hashlib
import json

import pytest
from ocf_tools import audio_defaults
from ocf_tools.paths import REPO_ROOT
from ocf_tools.utils import OCFError

pytestmark = pytest.mark.integration


def test_source_only_successor_preserves_historical_lock_and_profiles():
    prior_path = REPO_ROOT / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-021.json"
    old_path = REPO_ROOT / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-020.json"
    prior = json.loads(prior_path.read_text())
    old = json.loads(old_path.read_text())
    assert (
        hashlib.sha256(old_path.read_bytes()).hexdigest()
        == "339ff152899937803c91808ac0d12e306d87930296c4c71790c0e5282e418ac2"
    )
    new = audio_defaults.check_lock()
    assert new["id"] == "OCF-AUDIO-DEFAULTS-HPLUS-022"
    assert audio_defaults.PREVIOUS_BASELINE_ID == prior["id"]
    assert new["profiles"] == prior["profiles"] == old["profiles"]
    assert set(new["files"]) == set(prior["files"])
    assert new["human_listening_approval"] is None
    assert new["release_ready"] is False
    changed = {p for p in prior["files"] if prior["files"][p] != new["files"][p]}
    expected = {
        "OCF-BOD-001",
        "OCF-BOD-002",
        "OCF-BOD-003",
        "OCF-BOD-004",
        "OCF-BOD-006",
        "OCF-BOD-007",
        "OCF-BOD-008",
        "OCF-BOD-009",
        "OCF-SLP-001",
        "OCF-SLP-002",
        "OCF-BOD-010",
        "OCF-BOD-011",
        "OCF-BOD-013",
        "OCF-BOD-014",
        "OCF-BOD-015",
        "OCF-COG-001",
        "OCF-COG-002",
        "OCF-COG-007",
        "OCF-COM-001",
        "OCF-PRF-003",
        "OCF-FND-001",
        "OCF-AUT-001",
        "OCF-PRF-001",
    }
    assert len(changed) == 23
    assert {p.split("/")[-1][:11] for p in changed if p.startswith("locales/en-US/")} == expected
    assert all(p.startswith("locales/en-US/") for p in changed)
    with pytest.raises(OCFError, match="stale"):
        audio_defaults.check_lock(old_path)


def test_all_untouched_plans_and_all_bindings_survive_shared_fingerprint_ripple():
    baseline = json.loads(
        (REPO_ROOT / "tests/fixtures/editorial-plan-baseline-20261114.json").read_text()
    )
    from test_approved_editorial_batch import APPROVAL

    changed = set(APPROVAL)
    assert len(baseline) == 58
    for identity, expected in baseline.items():
        data = json.loads(
            (REPO_ROOT / "audio/session-plans/en-US" / (identity + ".json")).read_text()
        )
        assert data["generation"]["binding_sha256"] == expected["binding_sha256"]
        assert data["approval"]["release_ready"] is False
        if identity not in changed:
            data["defaults"]["sha256"] = "shared-fingerprint"
            assert (
                hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                == expected["plan_without_shared_fingerprint"]
            ), identity
