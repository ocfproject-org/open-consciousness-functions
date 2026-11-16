"""Acceptance: direct canonical YAML edits need no receipt or checksum refresh."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration


def _copy_checkout(destination: Path) -> None:
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
        .decode("utf-8")
        .split("\0")
    )
    excluded_roots = (
        "references/",
        "ReusablePrompts/",
        ".ocf-work/",
        "audio/renders/",
        "audio/voices/assets/",
        "audio/voices/datasets/",
    )
    binary_suffixes = {".wav", ".flac", ".mp3", ".ogg", ".png", ".jpg", ".jpeg", ".pdf"}
    for name in tracked:
        if not name or name.startswith(excluded_roots):
            continue
        source = REPO_ROOT / name
        if source.suffix.lower() in binary_suffixes or not source.is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # The new architecture baseline is part of the candidate checkout while
    # this test may run before Git staging during local development.
    active_lock = REPO_ROOT / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-026.json"
    if active_lock.is_file():
        target = destination / "audio/defaults" / active_lock.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active_lock, target)


def _run(checkout: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "OCF_WORK_DIR": str(checkout / ".ocf-work")}
    return subprocess.run(
        [sys.executable, "scripts/ocf.py", *args],
        cwd=checkout,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_narration_edit_regenerates_derived_data_without_touching_receipts(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    _copy_checkout(checkout)
    sentence = "Your mind and senses work together to recognize important details and understand what you are experiencing."
    replacement = "Your mind and senses work together to notice important details and understand what you are experiencing."
    description = "Strengthen concentration, sustain attention, and reduce distractions."
    revised_description = description[:-1] + " consistently."
    function = checkout / "locales/en-US/OCF-FND-002-Focus.yaml"
    original = function.read_text(encoding="utf-8")
    assert original.count(sentence) == 1
    assert original.count(description) == 1
    active_lock = checkout / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-026.json"
    lock_before = hashlib.sha256(active_lock.read_bytes()).hexdigest()
    plan_root = checkout / ".ocf-work" / "acceptance-plans"
    plan = plan_root / "en-US/OCF-FND-002.json"

    _run(checkout, "validate", "--all")
    _run(
        checkout,
        "audio",
        "plan",
        "OCF-FND-002",
        "--locale",
        "en-US",
        "--output",
        str(plan_root),
    )
    old_plan = plan.read_bytes()
    edited = original.replace(sentence, replacement).replace(description, revised_description)
    function.write_text(edited, encoding="utf-8")
    _run(checkout, "validate", "--all")
    _run(checkout, "build-index")
    _run(
        checkout,
        "audio",
        "plan",
        "OCF-FND-002",
        "--locale",
        "en-US",
        "--output",
        str(plan_root),
    )
    _run(checkout, "build-index", "--check")
    _run(
        checkout,
        "audio",
        "plan",
        "OCF-FND-002",
        "--locale",
        "en-US",
        "--output",
        str(plan_root),
        "--check",
    )
    _run(checkout, "validate", "--all")

    assert replacement in function.read_text(encoding="utf-8")
    assert hashlib.sha256(active_lock.read_bytes()).hexdigest() == lock_before
    assert plan.is_file()
    assert plan.read_bytes() != old_plan
    quick_reference = (checkout / "docs/COMMAND_QUICK_REFERENCE.md").read_text(encoding="utf-8")
    assert revised_description in quick_reference
