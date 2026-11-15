"""Owner-approved procedure and lifecycle contracts for the final editorial batch."""

import pytest
from ocf_tools.function_catalog import resources
from ocf_tools.locale import LocaleCatalog
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def functions():
    return {data["function_id"]: data for _, data in resources(REPO_ROOT)}


def _operations(command):
    return [step["operation"] for step in command.get("procedure_steps", [])]


@pytest.mark.parametrize(
    "identity",
    [
        "OCF-AUT-001",
        "OCF-BOD-001",
        "OCF-BOD-002",
        "OCF-BOD-003",
        "OCF-BOD-004",
        "OCF-BOD-005",
        "OCF-BOD-006",
        "OCF-BOD-007",
        "OCF-BOD-008",
        "OCF-BOD-009",
        "OCF-BOD-010",
        "OCF-BOD-011",
        "OCF-BOD-012",
        "OCF-BOD-013",
        "OCF-BOD-014",
        "OCF-BOD-015",
        "OCF-COG-001",
        "OCF-COG-002",
        "OCF-COG-003",
        "OCF-COG-004",
        "OCF-COG-005",
        "OCF-COG-006",
        "OCF-COG-007",
        "OCF-COM-001",
        "OCF-EMG-001",
        "OCF-EMG-002",
        "OCF-EMO-001",
        "OCF-EMO-002",
        "OCF-EMO-003",
        "OCF-EXP-001",
        "OCF-EXP-002",
        "OCF-EXP-003",
        "OCF-EXP-005",
        "OCF-EXP-006",
        "OCF-FND-001",
        "OCF-FND-002",
        "OCF-FND-003",
        "OCF-FND-004",
        "OCF-FND-005",
        "OCF-FND-006",
        "OCF-LIF-001",
        "OCF-PRF-001",
        "OCF-PRF-002",
        "OCF-PRF-003",
        "OCF-PRF-004",
        "OCF-PRF-005",
        "OCF-PRF-006",
        "OCF-SEN-001",
        "OCF-SEN-002",
        "OCF-SEN-003",
        "OCF-SEN-004",
        "OCF-SEN-005",
        "OCF-SLP-001",
        "OCF-SLP-002",
        "OCF-SLP-003",
        "OCF-SLP-004",
        "OCF-SLP-005",
        "OCF-SLP-006",
    ],
)
def test_all_58_narration_schedules_remain_one_four_one(functions, identity):
    assert [
        (row["role"], row["repetitions"]) for row in functions[identity]["narration"]["sequence"]
    ] == [
        ("opener", 1),
        ("function-body", 4),
        ("closer", 1),
    ]


def test_removed_selection_steps_and_explicit_outcome_selections(functions):
    for identity in ("OCF-PRF-002", "OCF-PRF-004", "OCF-FND-002", "OCF-FND-003", "OCF-SLP-006"):
        assert all(
            step["operation"] not in {"select-purpose", "select-activity"}
            for step in functions[identity]["activation"]["procedure_steps"]
        )
    assert (
        "today"
        in functions["OCF-PRF-005"]["activation"]["procedure_steps"][0]["instruction"][
            "text"
        ].lower()
    )
    assert (
        "completion time"
        in functions["OCF-EXP-001"]["activation"]["procedure_steps"][0]["instruction"][
            "text"
        ].lower()
    )
    assert (
        "unnecessary craving"
        in functions["OCF-BOD-005"]["activation"]["procedure_steps"][0]["instruction"][
            "text"
        ].lower()
    )
    assert (
        "one or more"
        in functions["OCF-FND-006"]["activation"]["procedure_steps"][0]["instruction"][
            "text"
        ].lower()
    )


def test_empathize_requires_a_being_but_is_breath_independent(functions):
    command = functions["OCF-EMO-003"]["activation"]
    assert _operations(command) == ["select-intention", "think-or-say-command"]
    assert command["control"]["procedure"]["before_steps"][0]["id"] == "select-being"
    assert not {"inhale", "hold-breath", "exhale"} & set(_operations(command))


def test_selected_emotional_and_thought_patterns_are_specific_before_activation(functions):
    for identity, expected in (
        ("OCF-EMO-001", "unwanted emotion"),
        ("OCF-EMO-002", "unwanted thought, emotional response, or recurring pattern"),
    ):
        steps = functions[identity]["activation"]["procedure_steps"]
        selected = steps[0]
        assert selected["operation"] == "select-intention"
        assert expected in selected["instruction"]["text"].lower()
        assert functions[identity]["activation"]["control"]["procedure"]["before_steps"][0][
            "localization_key"
        ].startswith(f"functions.{identity.lower()}.procedure.")


def test_temporary_responses_keep_their_learned_capability_permanently_available(functions):
    for identity in (
        "OCF-COG-003",
        "OCF-COG-006",
        "OCF-EMO-001",
        "OCF-EMO-002",
        "OCF-FND-002",
        "OCF-FND-003",
        "OCF-FND-004",
        "OCF-FND-005",
        "OCF-FND-006",
        "OCF-PRF-006",
        "OCF-SLP-003",
        "OCF-SLP-006",
    ):
        lifecycle = functions[identity]["lifecycle"]
        assert lifecycle["persistence"] == "temporary"
        assert lifecycle["scopes"]["capability"]["persistence"] == "permanent"


def test_clear_zone_commands_are_breath_independent_and_modes_are_temporary(functions):
    function = functions["OCF-EXP-005"]
    commands = [function["activation"], *function["secondary_commands"]]
    assert len(commands) == 3
    for command in commands:
        assert _operations(command) == ["think-or-say-command"]
        assert not {"inhale", "hold-breath", "exhale"} & set(_operations(command))
    assert function["lifecycle"]["scopes"]["baseline"]["activation"] == "automatic"
    assert function["lifecycle"]["scopes"]["application"]["persistence"] == "conditional"
    assert any(
        "mutually exclusive" in row.lower() for row in function["lifecycle"]["trigger_conditions"]
    )
    assert any("sleep onset" in row.lower() for row in function["lifecycle"]["trigger_conditions"])


def test_strong_quick_has_no_active_release_and_ends_automatically(functions):
    function = functions["OCF-PRF-006"]
    assert all(
        row.get("control", {}).get("availability", "active") != "active"
        for row in function["secondary_commands"]
        if row["role"] == "release"
    )
    assert function["lifecycle"]["release"].get("command_id") is None
    assert any(
        "automatically" in row.lower() and "need passes" in row.lower()
        for row in function["lifecycle"]["trigger_conditions"]
    )
    assert "OCF-CMD-PRF-006-RELEASE" not in str(function["entries"])


def test_hearing_tinnitus_paragraph_and_touch_exhale_resolve_exactly():
    catalog = LocaleCatalog()
    resources_by_id = catalog.require("en-US").localized_functions
    hearing = catalog.resource(
        "hplus.function.ocf-sen-001.function-body", "en-US", domain="narration", fallback=False
    )[0].text
    expected = (
        "Unwanted sounds, whether coming from your surroundings or arising within your own hearing "
        "awareness, become less prominent.\n\n"
        "Your attention naturally shifts toward the sounds you wish to hear, while unnecessary ringing, "
        "buzzing, humming, and other distracting sounds fade into the background.\n\n"
        "You remain aware of important sounds around you and can change the adjustment whenever you choose."
    )
    assert " ".join(expected.split()) in " ".join(hearing.split())
    touch = catalog.resource(
        "hplus.function.ocf-sen-005.closer", "en-US", domain="narration", fallback=False
    )[0].text
    assert "Then slowly exhale through your mouth and open your eyes." in touch
    assert "candle" not in touch.lower()
    assert "OCF-SEN-001" in resources_by_id


def test_no_active_function_narration_retains_the_candle_analogy(functions):
    for function in functions.values():
        for entry in function["entries"].values():
            text = entry if isinstance(entry, str) else entry.get("text", "")
            assert "candle" not in text.lower(), function["function_id"]
