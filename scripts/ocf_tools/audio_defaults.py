"""Versioned shared defaults with a checked, content-addressed dependency lock."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .paths import REPO_ROOT
from .utils import OCFError, sha256_of_file, write_text_atomic

PREVIOUS_BASELINE_ID = "OCF-AUDIO-DEFAULTS-HPLUS-025"
BASELINE_ID = "OCF-AUDIO-DEFAULTS-HPLUS-026"
BASELINE_VERSIONS = {
    "OCF-AUDIO-DEFAULTS-HPLUS-001": "1.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-002": "2.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-003": "3.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-004": "4.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-005": "5.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-006": "6.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-007": "7.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-008": "8.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-009": "9.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-010": "10.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-011": "11.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-012": "12.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-013": "13.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-014": "14.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-015": "15.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-016": "16.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-017": "17.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-018": "18.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-019": "19.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-020": "20.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-021": "21.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-022": "22.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-023": "23.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-024": "24.0.0",
    "OCF-AUDIO-DEFAULTS-HPLUS-025": "25.0.0",
    BASELINE_ID: "26.0.0",
}
TEMPLATE_ID = "OCF-TPL-SESSION-HPLUS-LOCKED-007"
PACING_ID = "OCF-PACING-HPLUS-LOCKED-007"
DSP_ID = "OCF-DSP-HPLUS-LOCKED-004"
LOCK_PATH = REPO_ROOT / "audio" / "defaults" / f"{BASELINE_ID}.json"


def overlay(parent: dict, child: dict) -> dict:
    """Merge mappings recursively; arrays/scalars are explicit replacements."""
    result = deepcopy(parent)
    for key, value in child.items():
        result[key] = (
            overlay(result[key], value)
            if isinstance(value, dict) and isinstance(result.get(key), dict)
            else deepcopy(value)
        )
    return result


def _is_engine_dependency(name: str) -> bool:
    """Audio configuration is locked; editable locale/content YAML is not."""
    return name.startswith(("audio/templates/", "audio/background/"))


def configuration_lock(
    dependency_names: list[str] | None = None, *, baseline_id: str = BASELINE_ID
) -> dict:
    from .semantic_dsp import load_profile
    from .session import load_pacing_profile, load_template

    if baseline_id not in BASELINE_VERSIONS:
        raise OCFError(f"unknown audio defaults baseline: {baseline_id}")
    if baseline_id != BASELINE_ID:
        historical = json.loads(
            (REPO_ROOT / "audio/defaults" / f"{baseline_id}.json").read_text(encoding="utf-8")
        )
        ids = {name: value["id"] for name, value in historical["profiles"].items()}
    else:
        ids = {"template": TEMPLATE_ID, "pacing": PACING_ID, "dsp": DSP_ID}
    template = load_template(ids["template"])
    pacing = load_pacing_profile(ids["pacing"])
    dsp = load_profile(ids["dsp"])
    # Lock transitive stage, cue, preset and locale timing inputs too. Only
    # committed runtime inputs are inspected, never reference/source corpora.
    paths = set()
    for pattern in (
        "audio/templates/sessions/OCF-TPL-SESSION-HPLUS-*.yaml",
        "audio/templates/pacing/*.yaml",
        "audio/templates/stages/*.yaml",
        "audio/cues/*.yaml",
        "audio/background/manifests/OCF-BG-0012.yaml",
        "audio/background/manifests/OCF-BG-0006.yaml",
        "audio/background/presets/focus-10-v4-candidate.yaml",
        "audio/background/presets/farfield/focus-11-b.yaml",
        "audio/background/state-profiles/OCF-DSP-HPLUS-*.yaml",
    ):
        paths.update(REPO_ROOT.glob(pattern))
    if dependency_names is not None:
        paths = set()
        for name in dependency_names:
            path = (REPO_ROOT / name).resolve()
            if Path(name).is_absolute() or not path.is_relative_to(REPO_ROOT):
                raise OCFError("audio defaults dependency escapes repository")
            paths.add(path)
    predecessor_files = {}
    excluded_predecessor_files: list[str] = []
    if baseline_id == BASELINE_ID:
        predecessor_path = REPO_ROOT / "audio/defaults" / f"{PREVIOUS_BASELINE_ID}.json"
        predecessor_files = json.loads(predecessor_path.read_text(encoding="utf-8"))["files"]
        excluded_predecessor_files = sorted(
            name for name in predecessor_files if not _is_engine_dependency(name)
        )
        if dependency_names is None:
            paths.update(
                REPO_ROOT / name for name in predecessor_files if _is_engine_dependency(name)
            )

    def file_hash(path):
        if not path.is_file():
            previous = predecessor_files.get(path.relative_to(REPO_ROOT).as_posix())
            if previous:
                return previous
            raise OCFError("locked dependency is missing from the canonical checkout")
        return sha256_of_file(path)

    result = {
        "schema_version": "1.0",
        "id": baseline_id,
        "version": BASELINE_VERSIONS[baseline_id],
        "configuration_status": "locked-user-requested",
        "human_listening_approval": None,
        "release_ready": False,
        "compatibility": {
            "python": ">=3.11",
            "timing": "measured-speech-relative",
            "locale": "en-US",
        },
        "profiles": {
            name: {"id": data["id"], "version": data["version"]}
            for name, data in (("template", template), ("pacing", pacing), ("dsp", dsp))
        },
        "files": {
            path.relative_to(REPO_ROOT).as_posix(): file_hash(path) for path in sorted(paths)
        },
    }
    if baseline_id == BASELINE_ID:
        result["excluded_predecessor_files"] = excluded_predecessor_files
    return result


def check_lock(path: Path = LOCK_PATH) -> dict:
    recorded = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    baseline_id = recorded.get("id", BASELINE_ID)
    if path.name != f"{baseline_id}.json":
        raise OCFError("audio defaults lock identity/path mismatch")
    if baseline_id == BASELINE_ID:
        predecessor = json.loads(
            (REPO_ROOT / "audio/defaults" / f"{PREVIOUS_BASELINE_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        expected_excluded = {
            name for name in predecessor["files"] if not _is_engine_dependency(name)
        }
        excluded = set(recorded.get("excluded_predecessor_files", []))
        if excluded != expected_excluded:
            raise OCFError("successor audio defaults exclusions differ from predecessor scope")
        required = set(predecessor["files"]) - excluded
        if not required.issubset(recorded.get("files", {})):
            raise OCFError("successor audio defaults must retain all predecessor dependencies")
    # New unrelated functions/locales do not mutate an existing baseline.
    # A change to a locked input still fails exact content verification.
    expected = configuration_lock(list(recorded.get("files", {})), baseline_id=baseline_id)
    if recorded != expected:
        raise OCFError(
            "shared audio defaults lock is stale; create a new baseline version deliberately"
        )
    return expected


def create_lock(
    path: Path = LOCK_PATH,
    *,
    baseline_id: str = BASELINE_ID,
    dependency_names: list[str] | None = None,
) -> None:
    if path.exists():
        raise OCFError(f"immutable audio defaults lock already exists: {path.name}")
    if path.name != f"{baseline_id}.json":
        raise OCFError("audio defaults lock identity/path mismatch")
    write_text_atomic(
        path,
        json.dumps(
            configuration_lock(dependency_names, baseline_id=baseline_id),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        overwrite=False,
    )
