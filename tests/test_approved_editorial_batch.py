"""Exact owner-supplied editorial attachment conformance; not audio approval."""

import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml
from ocf_tools.locale import LocaleCatalog
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration
ATTACHMENT = Path(__file__).parent / "fixtures/approved-editorial-batch-20261114.txt"
ATTACHMENT_SHA256 = "d21984367701da8475e0dd741f3e047e380466339fc869113632afb2d071700b"


def _approved():
    source = ATTACHMENT.read_bytes()
    assert hashlib.sha256(source).hexdigest() == ATTACHMENT_SHA256
    text = source.decode("utf-8")
    sections = re.split(r"(?m)^### (OCF-[A-Z]{3}-\d{3}) — (.+)$", text)
    result = {}
    for index in range(1, len(sections), 3):
        identity, name, section = sections[index : index + 3]
        blocks = {}
        for role, label in (
            ("description", "Approved short description"),
            ("opener", "Approved opener"),
            ("function-body", "Approved body"),
            ("closer", "Approved closer"),
        ):
            match = re.search(
                rf"\*\*{re.escape(label)}(?: \(four scheduled passes\))?:\*\*\s*```text\n(.*?)\n```",
                section,
                re.S,
            )
            assert match, f"missing {label} for {identity}"
            blocks[role] = match.group(1)
        result[identity] = {"name": name, "texts": blocks}
    assert len(result) == 23
    return result


APPROVAL = _approved()


@pytest.mark.parametrize("identity", sorted(APPROVAL))
def test_exact_resolved_approved_narration_and_schedule(identity):
    approved = APPROVAL[identity]
    catalog = LocaleCatalog()
    data = catalog.require("en-US").localized_functions[identity]
    assert data["description"]["text"] == approved["texts"]["description"]
    assert [(row["role"], row["repetitions"]) for row in data["narration"]["sequence"]] == [
        ("opener", 1),
        ("function-body", 4),
        ("closer", 1),
    ]
    for role in ("opener", "function-body", "closer"):
        key = f"hplus.function.{identity.lower()}.{role}"
        actual = catalog.resource(key, "en-US", domain="narration", fallback=False)[0].text
        assert actual == approved["texts"][role]
        assert "{{" not in actual
        assert "candle" not in actual.lower()
        entry = data["entries"][key]
        visible_cues = re.findall(r'"(Plus [^"]+)"', approved["texts"][role])
        cue_refs = []
        for quoted_cue in visible_cues:
            cue = quoted_cue.rstrip(".,;:!?")
            if cue == data["activation"].get("spoken_cue", {}).get("text"):
                reference = "cue.primary"
            else:
                matching = [
                    command
                    for command in data["secondary_commands"]
                    if command.get("spoken_cue", {}).get("text") == cue
                ]
                assert len(matching) == 1, (identity, cue)
                reference = f"cue.id.{matching[0]['command_id']}"
            if reference not in cue_refs:
                cue_refs.append(reference)
            assert "{{ " + reference + " }}" in entry["text"]
            assert cue not in entry["text"]
        if cue_refs:
            assert entry["cue_template"]["function_id"] == identity
            assert entry["cue_template"]["allowed"] == cue_refs
        else:
            assert "cue_template" not in entry


def _data(identity):
    path = next((REPO_ROOT / "locales/en-US").glob(identity + "-*.yaml"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _ops(identity, command=None):
    data = _data(identity)
    row = command or data["activation"]
    return [step["operation"] for step in row["procedure_steps"]]


def test_description_parity_is_exact_for_all_23_functions():
    assert len(APPROVAL) == 23
    assert all(
        _data(identity)["description"]["text"] == item["texts"]["description"]
        for identity, item in APPROVAL.items()
    )


def test_source_only_integrity_record_binds_exact_attachment_without_claiming_authority():
    path = REPO_ROOT / "function-content/editorial/source-only-editorial-successor-23-20261114.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["kind"] == "source-only-editorial-integrity-successor"
    assert record["authority_attachment_sha256"] == ATTACHMENT_SHA256
    assert record["predecessor_commit"] == "828252bcc97e780c8b3dd0b3c15163496b7a86a7"
    assert len(record["resources"]) == 23
    assert not any("approved_text" in key or "approval_content" in key for key in record)
    assert len(record["added_locale_entries"]) == 8
    assert "command.scope.persistent" in record["added_locale_entries"]


def test_sleep_has_exact_close_hold_sequence_without_reusing_legacy_sleep_procedure():
    data = _data("OCF-SLP-002")
    assert data["activation"]["control"]["procedure"]["before_steps"] == []
    assert data["activation"]["control"]["procedure"]["ref"] == "OCF-PROC-SLEEP-HOLD"
    assert _ops("OCF-SLP-002") == [
        "close-eyes",
        "inhale",
        "hold-breath",
        "think-or-say-command",
        "exhale",
        "breathe-normally",
    ]
    assert all(
        s["operation"] not in {"select-purpose", "select-intention", "open-eyes"}
        for s in data["activation"]["procedure_steps"]
    )


def test_nutricia_has_no_default_or_per_meal_action_and_both_modes_persist():
    data = _data("OCF-BOD-010")
    assert data["lifecycle"]["persistence"] == "persistent"
    assert data["lifecycle"]["scopes"]["baseline"]["activation"] == "conditional"
    assert data["lifecycle"]["scopes"]["baseline"]["persistence"] == "persistent"
    assert data["lifecycle"]["scopes"]["application"]["persistence"] == "persistent"
    assert (
        "No mode is active by default"
        in data["metadata_entries"]["functions.ocf-bod-010.lifecycle.scopes.baseline.description"][
            "text"
        ]
    )
    assert (
        "until deliberately changed"
        in data["metadata_entries"]["functions.ocf-bod-010.lifecycle.scopes.baseline.description"][
            "text"
        ]
    )
    assert _ops("OCF-BOD-010") == ["inhale", "hold-breath", "think-or-say-command", "exhale"]
    secondary = next(command for command in data["secondary_commands"] if command["role"] == "mode")
    assert _ops("OCF-BOD-010", secondary) == _ops("OCF-BOD-010")
    assert secondary["control"]["effect_scope_ref"] == "lifecycle.scopes.baseline.persistence"
    assert (
        data["activation"]["control"]["effect_scope_ref"] == "lifecycle.scopes.baseline.persistence"
    )
    body = data["entries"]["hplus.function.ocf-bod-010.function-body"]
    assert "cue.primary" in body["cue_template"]["allowed"]
    assert "cue.id.OCF-CMD-BOD-010-FOOD-LESS" in body["cue_template"]["allowed"]
    approved_body = APPROVAL["OCF-BOD-010"]["texts"]["function-body"]
    assert "When you switch modes, your new selection replaces the previous one." in approved_body
    assert (
        "Whenever you wish to reinforce your current selection, you may use its command again."
        in approved_body
    )
    assert "There is no need to repeat the command before each meal." in approved_body


def test_required_and_optional_targets_remain_function_specific():
    assert "focus-target" not in _ops("OCF-BOD-001")
    assert _ops("OCF-BOD-003").index("focus-target") < _ops("OCF-BOD-003").index("inhale")
    assert _data("OCF-BOD-003")["activation"]["control"]["procedure"]["before_steps"] == []
    assert (
        _data("OCF-BOD-003")["activation"]["control"]["procedure"]["ref"]
        == "OCF-PROC-COMFORT-SELECTED-AREA"
    )
    assert _ops("OCF-SLP-001")[0] == "select-target-area"
    assert (
        "optionally"
        in _data("OCF-SLP-001")["activation"]["procedure_steps"][0]["instruction"]["text"]
    )
    assert _ops("OCF-BOD-013")[:2] == ["close-eyes", "select-target-area"]
    assert (
        "optionally"
        in _data("OCF-BOD-013")["activation"]["procedure_steps"][1]["instruction"]["text"]
    )
    metadata = _data("OCF-BOD-013")["metadata_entries"]
    assert (
        "whole body"
        in metadata["functions.ocf-bod-013.lifecycle.scopes.baseline.description"]["text"]
    )
    assert (
        "no selected area is required"
        in metadata["functions.ocf-bod-013.lifecycle.scopes.baseline.description"]["text"]
    )
    application = metadata["functions.ocf-bod-013.lifecycle.scopes.application.description"]["text"]
    assert "Optional" in application and "otherwise" in application
    assert _ops("OCF-BOD-014").index("focus-target") < _ops("OCF-BOD-014").index("inhale")
    assert (
        "specific part"
        in _data("OCF-BOD-014")["activation"]["procedure_steps"][1]["instruction"]["text"]
    )
    assert _ops("OCF-BOD-015").index("focus-target") < _ops("OCF-BOD-015").index("inhale")
    release = next(c for c in _data("OCF-BOD-015")["secondary_commands"] if c["role"] == "release")
    assert _ops("OCF-BOD-015", release)[:2] == ["close-eyes", "focus-target"]
    assert _ops("OCF-BOD-015", release)[2] == "inhale"
    assert release["control"]["procedure"]["ref"] == "OCF-PROC-CLOSE-FOCUS"


def test_information_access_and_energy_preserve_distinct_selection_contracts():
    assert _ops("OCF-COG-001") == ["select-question", "think-or-say-command"]
    assert _data("OCF-COG-001")["activation"]["control"]["procedure"]["ref"] == "OCF-PROC-QUESTION"
    energy = _data("OCF-FND-001")
    assert _ops("OCF-FND-001") == ["select-purpose", "think-or-say-command", "represent-result"]
    assert energy["activation"]["control"]["procedure"]["ref"] == "OCF-PROC-M-ENERGY"
    result_step = energy["activation"]["procedure_steps"][2]["instruction"]["text"]
    assert "hold your intended result in your awareness" in result_step
    assert "There is no need to picture it" in result_step
    assert not any(
        operation in _ops("OCF-FND-001") for operation in ("inhale", "hold-breath", "exhale")
    )
    special = next(c for c in energy["secondary_commands"] if c["role"] == "access-close")
    assert special["command_id"] == "OCF-CMD-FND-001-ACCESS-CLOSE"
    assert special["spoken_cue"]["text"] == "plus, release, eleven, access"
    assert (
        hashlib.sha256(
            json.dumps(special, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        == "bfde150941f2ab60eeb02111ccc2dc84dfc68941e5098cc983759c92aedd93e5"
    )


def test_adaptive_baselines_and_temporary_applications_remain_separate():
    for identity in (
        "OCF-BOD-007",
        "OCF-BOD-011",
        "OCF-BOD-013",
        "OCF-COG-001",
        "OCF-AUT-001",
    ):
        scopes = _data(identity)["lifecycle"]["scopes"]
        assert scopes["baseline"]["persistence"] == "permanent", identity
        assert scopes["baseline"]["activation"] == "automatic", identity
        assert scopes["application"]["persistence"] == "temporary", identity
        assert scopes["application"]["activation"] == "manual", identity
    for identity in ("OCF-SLP-001", "OCF-BOD-015"):
        scopes = _data(identity)["lifecycle"]["scopes"]
        assert scopes["capability"]["persistence"] == "permanent", identity
        assert scopes["application"]["persistence"] == "temporary", identity
    assert _data("OCF-SLP-001")["lifecycle"]["persistence"] == "temporary"
    assert _data("OCF-BOD-015")["lifecycle"]["persistence"] == "temporary"


def test_exact_eye_rules_are_not_normalized_across_functions():
    has_close = {identity for identity in APPROVAL if "close-eyes" in _ops(identity)}
    assert has_close == {
        "OCF-BOD-001",
        "OCF-BOD-002",
        "OCF-BOD-003",
        "OCF-BOD-004",
        "OCF-BOD-006",
        "OCF-BOD-007",
        "OCF-BOD-013",
        "OCF-BOD-014",
        "OCF-BOD-015",
        "OCF-SLP-001",
        "OCF-SLP-002",
    }
    has_open = {identity for identity in APPROVAL if "open-eyes" in _ops(identity)}
    assert has_open == {"OCF-BOD-001", "OCF-BOD-013", "OCF-BOD-014"}
    circulation_closer = APPROVAL["OCF-BOD-002"]["texts"]["closer"]
    assert "open your eyes" in circulation_closer.lower()
    assert "open-eyes" not in _ops("OCF-BOD-002")


def test_no_visualization_or_involuntary_behavior_gate_in_target_batch():
    for identity in APPROVAL:
        data = _data(identity)
        active = "\n".join(
            data["entries"][f"hplus.function.{identity.lower()}.{role}"]["text"]
            for role in ("opener", "function-body", "closer")
        ).lower()
        assert "as though gently blowing out a candle" not in active, identity
    for identity in ("OCF-AUT-001", "OCF-FND-001", "OCF-PRF-001"):
        assert "close-eyes" not in _ops(identity)
    for identity in ("OCF-BOD-001", "OCF-BOD-006", "OCF-BOD-002", "OCF-BOD-007"):
        assert not any(
            op in _ops(identity) for op in ("focus-target", "select-target-area", "select-purpose")
        )
