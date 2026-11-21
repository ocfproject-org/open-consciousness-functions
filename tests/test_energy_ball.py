"""Reviewed Energy Ball, independent optional stage editions and measured hold structure."""

from copy import deepcopy

import pytest
from ocf_tools.complete_session import build_complete_session_plan
from ocf_tools.indexes import load_all_functions
from ocf_tools.learning_session import plan as learning_plan
from ocf_tools.locale import LocaleCatalog, iter_events, resolve_document
from ocf_tools.narration_pacing import plan_event_pacing
from ocf_tools.timing import schedule_timeline
from ocf_tools.utils import OCFError
from ocf_tools.validators import _load_schema, validate_against_schema

ID = "OCF-EXP-007"
PACING = "OCF-PACING-OPTIONAL-PREPARATION-001"
LEARNING_PACING = "OCF-PACING-OPTIONAL-PREPARATION-LEARNING-001"
pytestmark = pytest.mark.integration


def test_energy_ball_catalog_commands_and_scopes():
    records = load_all_functions()
    owner = next(record for record in records if record.id == ID)
    assert len(records) == 59 and all(record.id != "OCF-EXP-004" for record in records)
    pack = LocaleCatalog().require("en-US")
    data = pack.localized_functions[ID]
    assert pack.localized_function_files[ID] == "OCF-EXP-007-Energy-Ball.yaml"
    assert data["audio"]["script_status"] == "approved"
    assert data["audio"]["implementation_status"] == "not-started"
    scopes = data["lifecycle"]["scopes"]
    assert scopes["capability"]["persistence"] == "permanent"
    assert scopes["application"]["persistence"] == "temporary"
    inflate, deflate = [data["activation"], *data["secondary_commands"]]
    assert [cmd["spoken_cue"]["text"] for cmd in (inflate, deflate)] == [
        "Plus Inflate",
        "Plus Deflate",
    ]
    for command in (inflate, deflate):
        control = command["control"]
        assert control["effect_scope_ref"] == "lifecycle.scopes.application.persistence"
        assert [step["operation"] for step in control["procedure"]["override_steps"]] == [
            "think-or-say-command"
        ]
    assert deflate["role"] == "close"
    assert deflate["control"]["relationships"] == {"closes": [inflate["command_id"]]}
    assert {command.id for command in owner.command_records} == {
        "OCF-CMD-EXP-007-PRIMARY",
        "OCF-CMD-EXP-007-DEFLATE",
    }
    assert not data["lifecycle"]["release"]["required"]


@pytest.fixture(scope="module")
def energy():
    plan = build_complete_session_plan(ID, locale="en-US")
    doc = resolve_document(plan["template_plan"], "en-US", strict=True)
    return plan, doc


def test_energy_ball_four_passes_and_teaching_holds(energy):
    plan, doc = energy
    events = list(iter_events(doc))
    assert sum(event.get("slot_ref") == "opener" for event in events) == 1
    assert sum(event.get("slot_ref") == "closer" for event in events) == 1
    bodies = [event for event in events if event.get("slot_ref") == "function_body"]
    assert [event["id"] for event in bodies] == [
        "focus11-body.pass-1",
        "focus11-body.pass-2",
        "sleep20-body.pass-1",
        "sleep20-body.pass-2",
    ]
    assert len({event["text"] for event in bodies}) == 1
    assert all("[" not in event.get("text", "") for event in bodies)
    assert bodies[0]["text"].endswith("Plus Deflate.")
    assert "Let the ball remain deflated" in next(
        event["text"] for event in events if event.get("slot_ref") == "closer"
    )
    assert not any(event["id"].startswith("energy-ball.") for event in events)
    pacing = {event["id"]: plan_event_pacing(doc, event) for event in bodies}
    for value in pacing.values():
        units = value["units"]
        assert value["rate_scale"] == 1
        assert [u["pause_after_s"] for u in units if u["kind"] == "landing"] == [5] * 15
        practice = [u for u in units if u["kind"] == "independent-practice"]
        assert [u["text"] for u in practice] == ["Plus Inflate.", "Plus Deflate."]
        assert all(u["pause_after_s"] == 15 and u["pause_inside_event"] for u in practice)
        assert units[-1] == practice[-1]
    assert not plan["approval_state"]["release_ready"]


def test_energy_ball_realized_cadence_and_editability(energy):
    _, doc = energy
    durations = {e["id"]: 1.0 for e in iter_events(doc) if e.get("text")}
    bodies = [e for e in iter_events(doc) if e.get("slot_ref") == "function_body"]
    for event in bodies:
        units = plan_event_pacing(doc, event)["units"]
        durations[event["id"]] = sum(1.0 + u["pause_after_s"] for u in units)
    rows = {row["id"]: row for row in schedule_timeline(doc, durations)}
    for before, after, gap in (
        ("focus11-body.pass-1", "focus11-body.pass-2", 15),
        ("sleep20-body.pass-1", "sleep20-body.pass-2", 60),
    ):
        assert rows[after]["at"] - rows[before]["end"] == pytest.approx(gap)
    assert rows["resonant-tuning.complete"]["at"] - rows["resonant-tuning.begin"]["end"] == 30
    assert rows["resonant-tuning.practice"]["end"] - rows["resonant-tuning.practice"]["at"] == 30
    edited = deepcopy(bodies[0])
    edited["text"] = edited["text"].replace("warm and bright", "steady and bright")
    assert any("steady and bright" in u["text"] for u in plan_event_pacing(doc, edited)["units"])


def test_tuning_optional_and_no_routine_before_energy_ball_teaching():
    without = build_complete_session_plan(ID, overrides={"enabled_stages": []})
    assert not any("resonant-tuning" == row["id"] for row in without["stages"])
    with pytest.raises(OCFError, match="optional stages unavailable.*energy-ball"):
        build_complete_session_plan(ID, overrides={"enabled_stages": ["energy-ball"]})


def test_old_profile_does_not_silently_drop_energy_ball_practice():
    with pytest.raises(OCFError, match="has no pause for unit kind"):
        build_complete_session_plan(ID, overrides={"pacing_profile": "OCF-PACING-HPLUS-LOCKED-007"})


def test_existing_defaults_and_independent_optional_stage_editions():
    owner = "OCF-FND-002"
    default = build_complete_session_plan(owner)
    assert not {"resonant-tuning", "energy-ball", "affirmation"} & {
        stage["id"] for stage in default["stages"]
    }
    routine = build_complete_session_plan(
        owner,
        overrides={"pacing_profile": PACING, "enabled_stages": ["energy-ball", "resonant-tuning"]},
    )
    doc = resolve_document(routine["template_plan"], "en-US", strict=True)
    events = {event["id"]: event for event in iter_events(doc)}
    assert events["energy-ball.begin"]["after"] == "resonant-tuning.complete"
    assert "let it remain around you" in events["energy-ball.complete"]["text"]
    assert events["energy-ball.practice"]["timing"]["pause_after"] == 15
    assert events["resonant-tuning.practice"]["timing"]["pause_after"] == 30
    learning = learning_plan(
        pacing_profile=LEARNING_PACING,
        enabled_stages=("resonant-tuning", "energy-ball", "affirmation"),
        affirmation="OCF",
    )
    events = {event["id"]: event for event in iter_events(learning["document"])}
    assert events["affirmation.practice"]["timing"]["pause_after"] == 15
    assert events["resonant-tuning.practice"]["timing"]["pause_after"] == 30
    assert events["energy-ball.practice"]["timing"]["pause_after"] == 15
    assert learning["practice_seconds"] == 510


def test_stage_pacing_schema_rejects_nonmatching_stage_family(energy):
    plan, _ = energy
    schema = _load_schema("session-pacing.schema.json")
    pacing = deepcopy(plan["resolved_pacing_profile"])
    assert not validate_against_schema(pacing, schema)
    pacing["optional_stage_variants"]["resonant-tuning"] = "OCF-TPL-STAGE-HPLUS-ENERGY-BALL-003"
    assert validate_against_schema(pacing, schema)
