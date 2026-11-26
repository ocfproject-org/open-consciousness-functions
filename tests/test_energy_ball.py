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
        cue = command["spoken_cue"]["text"]
        assert command["usage"]["text"].startswith(f'Think or say in your mind, "{cue}."')
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


def test_energy_ball_two_guided_cycles_and_passive_reinforcement(energy):
    plan, doc = energy
    stages = [section["id"] for section in doc["sections"]]
    expected = [
        "function-opener",
        "body-comfort",
        "transmutation-box",
        "relaxation",
        "resonant-tuning",
        "guided-practice",
        "focus-ten",
        "open",
        "focus11-body",
        "close",
        "focus10-hold",
        "focus20-enter",
        "sleep20-body",
        "focus20-close",
        "return",
        "function-closer",
    ]
    assert [stage for stage in stages if stage in expected] == expected
    events = list(iter_events(doc))
    by_id = {event["id"]: event for event in events}
    practice = [event for event in events if event["id"].startswith("guided-practice.")]
    assert [e["id"].split(".", maxsplit=1)[1] for e in practice] == [
        "detailed",
        "healing-2",
        "healing-3",
        "healing-4",
        "healing-5",
        "healing-6",
        "healing-start",
        "withdrawal",
        "rehearsal",
        "protection-2",
        "protection-3",
        "protection-4",
        "protection-start",
        "continuation",
    ]
    cue_mentions = [
        event["id"]
        for event in events
        if any(cue in (event.get("text") or "") for cue in ("Plus Inflate", "Plus Deflate"))
    ]
    assert cue_mentions == [
        "focus11-body.pass-1",
        "focus11-body.pass-2",
        "sleep20-body.pass-1",
        "sleep20-body.pass-2",
    ]
    assert [event["id"] for event in events if "Plus Energize" in event.get("text", "")] == [
        "guided-practice.healing-start",
        "guided-practice.protection-2",
    ]
    for key in ("guided-practice.healing-start", "guided-practice.protection-2"):
        text = by_id[key]["text"]
        assert text.index("first choose the purpose or result") < text.index("Plus Energize")
        assert text.index("Plus Energize") < text.index("Hold your intended result")
    assert "invisible field" not in "\n".join(e["text"] for e in practice)
    assert (
        "If it is still around you, continue with the same ball."
        in by_id["guided-practice.rehearsal"]["text"]
    )
    assert by_id["guided-practice.detailed"]["after"] == "resonant-tuning.complete"
    assert by_id["focus-ten.begin"]["after"] == "guided-practice.continuation"
    assert "Your Energy Ball can remain around you as you close" in by_id["close.prepare"]["text"]
    assert by_id["open.prepare"]["after"] == "focus-ten.ready"
    bodies = [event for event in events if event.get("slot_ref") == "function_body"]
    assert [event["id"] for event in bodies] == [
        "focus11-body.pass-1",
        "focus11-body.pass-2",
        "sleep20-body.pass-1",
        "sleep20-body.pass-2",
    ]
    assert len({event["text"] for event in bodies}) == 1
    assert all(
        'think or say in your mind, "Plus Inflate."' in event["text"]
        and 'think or say in your mind, "Plus Deflate."' in event["text"]
        and "deliberately" not in event["text"].lower()
        and "renews the same ball at the size and with the qualities you have chosen"
        in event["text"]
        for event in bodies
    )
    assert next(s for s in doc["sections"] if s["id"] == "sleep20-body")["gain_db"] == -24
    assert sum(event.get("slot_ref") == "opener" for event in events) == 1
    assert sum(event.get("slot_ref") == "closer" for event in events) == 1
    closer = by_id["function-closer.block"]["text"]
    assert "Your Energy Ball can remain around you" in closer
    assert closer.count("remain available") == 1
    assert not any(cue in closer for cue in ("Plus Inflate", "Plus Deflate"))
    assert not any(event["id"].startswith("energy-ball.") for event in events)
    assert not plan["approval_state"]["release_ready"]


def test_energy_ball_realized_cadence_and_editability(energy):
    _, doc = energy
    durations = {e["id"]: 1.0 for e in iter_events(doc) if e.get("text")}
    practice = [e for e in iter_events(doc) if e["id"].startswith("guided-practice.")]
    waits = [5] * 6 + [60, 10] + [5] * 4 + [60, 5]
    assert [event["timing"]["pause_after"] for event in practice] == waits
    assert all(event["timing"]["trim_speech_padding"] for event in practice)
    for event in practice:
        pacing = plan_event_pacing(doc, event)
        assert pacing["rate_scale"] == 1
        units = pacing["units"]
        assert all("[" not in unit["text"] for unit in units)
        durations[event["id"]] = (
            sum(1.0 + u["pause_after_s"] for u in units if u["pause_inside_event"]) + 1.0
        )
    rows = {row["id"]: row for row in schedule_timeline(doc, durations)}
    for before, after, gap in (
        ("focus11-body.pass-1", "focus11-body.pass-2", 15),
        ("sleep20-body.pass-1", "sleep20-body.pass-2", 60),
    ):
        assert rows[after]["at"] - rows[before]["end"] == pytest.approx(gap)
    practice_ids = [event["id"] for event in practice]
    for before, after, wait in zip(
        practice_ids, [*practice_ids[1:], "focus-ten.begin"], waits, strict=True
    ):
        assert rows[after]["at"] - rows[before]["at"] - durations[before] == pytest.approx(wait)
    assert rows["resonant-tuning.complete"]["at"] - rows["resonant-tuning.begin"]["end"] == 120
    assert rows["resonant-tuning.practice"]["end"] - rows["resonant-tuning.practice"]["at"] == 120
    edited = deepcopy(practice[0])
    edited["text"] = edited["text"].replace("small sun", "steady light")
    assert any("steady light" in u["text"] for u in plan_event_pacing(doc, edited)["units"])


@pytest.mark.parametrize("tuning", [True, False])
def test_short_relaxation_is_independent_of_tuning(tuning, energy):
    plan, _ = energy
    assert any(
        item["key"] == "hplus.shared.settling.whole-body-awareness"
        for item in plan["narration_resources"]
    )
    short = build_complete_session_plan(
        ID,
        overrides={
            "relaxation": "short",
            "enabled_stages": ["resonant-tuning"] if tuning else [],
        },
    )
    doc = resolve_document(short["template_plan"], "en-US", strict=True)
    events = {e["id"]: e for e in iter_events(doc)}
    counts = [e for e in events.values() if e["semantic"] == "focus.ten.count"]
    assert [e["text"] for e in counts] == [
        word + "." for word in "One Two Three Four Five Six Seven Eight Nine Ten".split()
    ]
    assert all(e["timing"]["pause_after"] == 4 for e in counts)
    assert ("resonant-tuning.practice" in events) == tuning
    assert events["relaxation.begin"]["narration_key"] == "hplus.shared.settling.brief"
    relax = LocaleCatalog().require("en-US").localized_functions["OCF-FND-004"]
    cue = relax["activation"]["spoken_cue"]["text"]
    assert events["relaxation.begin"]["text"].count(cue) == 1
    assert [key for key in events if key.startswith("relaxation.")] == ["relaxation.begin"]
    assert events["guided-practice.detailed"]["after"] == (
        "resonant-tuning.complete" if tuning else "relaxation.begin"
    )


def test_no_routine_stage_or_changed_reinforcement_in_energy_ball_lesson():
    with pytest.raises(OCFError, match="optional stages unavailable.*energy-ball"):
        build_complete_session_plan(ID, overrides={"enabled_stages": ["energy-ball"]})
    with pytest.raises(OCFError, match=r"two\-plus\-two"):
        build_complete_session_plan(ID, overrides={"repetitions": {"sleep": 1}})


def test_old_profile_does_not_silently_drop_energy_ball_practice():
    with pytest.raises(OCFError, match="requires explicit pacing"):
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
    assert events["energy-ball.begin"]["text"] == (
        'To establish or renew your Energy Ball, think or say in your mind, "Plus Inflate."'
    )
    assert events["energy-ball.complete"]["text"] == (
        "Let it remain around you at the size and with the qualities you choose as we continue.\n\n"
        'Whenever you choose to draw the whole ball back within, think or say in your mind, "Plus Deflate."'
    )
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


def test_optional_short_wake_keeps_twenty_to_ten_and_shared_closing(energy):
    from ocf_tools.waking_c1 import policy

    _, full = energy
    short = resolve_document(
        build_complete_session_plan(ID, overrides={"waking_style": "short"})["template_plan"],
        "en-US",
        strict=True,
    )
    full_events = {event["id"]: event for event in iter_events(full)}
    short_events = {event["id"]: event for event in iter_events(short)}
    common = ["return.descent", "return.ten", "function-closer.block"]
    assert all(full_events[key] == short_events[key] for key in common)
    assert full_events["return.ten"]["text"] == "Ten."
    assert full_events["return.ten"]["semantic"] == "session.return.focus-ten-landed"
    descent = plan_event_pacing(full, full_events["return.descent"])["units"]
    assert "more awake and alert" in " ".join(unit["text"] for unit in descent[:2])
    assert [unit["text"] for unit in descent[2:]] == [
        word + "."
        for word in "Twenty Nineteen Eighteen Seventeen Sixteen Fifteen Fourteen Thirteen Twelve Eleven".split()
    ]
    ten = [unit["text"] for unit in plan_event_pacing(full, full_events["return.ten"])["units"]]
    nine_to_one = plan_event_pacing(full, full_events["return.count-to-one"])["units"]
    assert ten + [unit["text"] for unit in nine_to_one] == [
        word + "." for word in "Ten Nine Eight Seven Six Five Four Three Two One".split()
    ]
    assert full_events["return.count-to-one"]["after"] == "return.ten"
    assert short_events["return.reorient"]["after"] == "return.ten"
    assert set(full_events) - set(short_events) == {"return.count-to-one", "return.alert"}
    assert set(short_events) - set(full_events) == {"return.reorient"}
    short_text = short_events["return.reorient"]["text"]
    assert short_text == (
        "To return to C one, your normal waking consciousness, think of the number One."
    )
    assert "Plus One Awake" not in short_text
    duration = 2.0
    scheduled = {
        row["id"]: row
        for row in schedule_timeline(
            short, {event["id"]: duration for event in short_events.values() if event.get("text")}
        )
    }
    assert (
        scheduled["function-closer.block"]["at"] - scheduled["return.reorient"]["at"] - duration
    ) == pytest.approx(30.0)
    assert "renewed energy" in full_events["return.alert"]["text"]
    assert "Take a moment before you continue." in full_events["function-closer.block"]["text"]
    assert policy(full) == policy(short)
    assert policy(short)["tail_after_speech_seconds"] == 30
    assert policy(short)["closer_event_ids"] == ["function-closer.block"]


@pytest.mark.parametrize("style", ["full", "short"])
def test_split_wake_writes_measured_pacing_auditions(tmp_path, style):
    import wave

    from ocf_tools.pacing_auditions import write_timing_reports_and_auditions

    plan = build_complete_session_plan(ID, overrides={"waking_style": style})
    document = resolve_document(plan["template_plan"], "en-US", strict=True)
    events = list(iter_events(document))
    timings = schedule_timeline(
        document, {event["id"]: 2.0 for event in events if event.get("text")}
    )
    duration = max(row["end"] for row in timings)
    master = tmp_path / "master.wav"
    with wave.open(str(master), "wb") as wav:
        wav.setparams((2, 2, 200, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x00" * (4 * (int(duration * 200) + 1)))
    rows = {row["id"]: row for row in timings}
    _, excerpts, _ = write_timing_reports_and_auditions(
        stage=tmp_path,
        master_path=master,
        function_id=ID,
        title="Energy Ball",
        locale="en-US",
        voice={},
        session_pacing={},
        pacing_profile=plan["resolved_pacing_profile"],
        document=document,
        render={"event_timing": timings, "narration_timing": {"duration_seconds": 0}},
        session_duration=duration,
        sample_rate=200,
    )
    assert set(excerpts) == {
        "relaxation-1-to-10",
        "focus20-countdown-10-to-20",
        f"waking-return-{style}",
    }
    expected_span = rows["return.complete"]["end"] - rows["return.descent"]["at"]
    waking = excerpts[f"waking-return-{style}"]
    assert waking["duration_seconds"] == pytest.approx(expected_span, abs=0.011)
    assert ("think of One" in waking["label"]) == (style == "short")


def test_short_wake_requires_an_eligible_sleep_descent():
    with pytest.raises(OCFError, match="waking style is unavailable"):
        build_complete_session_plan("OCF-FND-002", overrides={"waking_style": "short"})
    with pytest.raises(OCFError, match="requires sleep descent and waking"):
        build_complete_session_plan(ID, overrides={"waking_style": "short", "ending": "sleep"})


def test_affirmation_follows_guided_ball_before_focus_ten():
    plan = build_complete_session_plan(ID, overrides={"affirmation": "Gateway"})
    stages = [stage["id"] for stage in plan["stages"]]
    assert stages[stages.index("transmutation-box") : stages.index("open")] == [
        "transmutation-box",
        "relaxation",
        "resonant-tuning",
        "guided-practice",
        "affirmation",
        "focus-ten",
    ]
    doc = resolve_document(plan["template_plan"], "en-US", strict=True)
    events = {e["id"]: e for e in iter_events(doc)}
    assert events["affirmation.begin"]["after"] == "guided-practice.continuation"
    assert events["focus-ten.begin"]["after"] == "affirmation.complete"
    assert events["open.prepare"]["after"] == "focus-ten.ready"


@pytest.mark.parametrize("relaxation", ["long", "short"])
def test_preparation_learning_orders_all_optional_stages_before_ten(relaxation):
    doc = learning_plan(
        enabled_stages=("energy-ball", "resonant-tuning"),
        affirmation="Gateway",
        relaxation=relaxation,
    )["document"]
    stages = [stage["id"] for stage in doc["sections"]]
    assert stages[stages.index("transmutation-box") : stages.index("learning-intro")] == [
        "transmutation-box",
        "relaxation",
        "resonant-tuning",
        "energy-ball",
        "affirmation",
        "focus-ten",
    ]
    assert len([e for e in iter_events(doc) if e["semantic"] == "focus.ten.count"]) == 10
    begin = next(e for e in iter_events(doc) if e["id"] == "relaxation.begin")
    assert ("Plus Relax" in begin["text"]) == (relaxation == "short")


def test_predecessor_template_remains_selectable_with_its_original_order():
    plan = build_complete_session_plan(ID, template="OCF-TPL-SESSION-HPLUS-LOCKED-007")
    stages = [stage["id"] for stage in plan["stages"]]
    assert stages[stages.index("transmutation-box") : stages.index("open")] == [
        "transmutation-box",
        "relaxation",
        "focus-ten",
        "resonant-tuning",
        "guided-practice",
    ]
