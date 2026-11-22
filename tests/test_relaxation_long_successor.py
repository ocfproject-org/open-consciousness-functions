"""Current shared resources, real default bindings, pacing, and frozen-edition boundaries."""

import hashlib
import json
import re

import pytest
from ocf_tools import audio_defaults
from ocf_tools.complete_session import build_complete_session_plan
from ocf_tools.indexes import load_all_functions
from ocf_tools.locale import LocaleCatalog, iter_events, resolve_document
from ocf_tools.narration_pacing import plan_event_pacing, split_speech_units
from ocf_tools.paths import REPO_ROOT
from ocf_tools.session import compose, load_template
from ocf_tools.session_plans import source_plan
from ocf_tools.speech_cache import _synthesis_identity
from ocf_tools.transcript import resolve_timeline
from ocf_tools.utils import OCFError, yaml_safe_load

pytestmark = pytest.mark.integration
REVISION = "OCF-RELAXATION-LONG-002"
KEY_PARTS = [
    "begin",
    "support",
    "face",
    "jaw-neck",
    "shoulders",
    "hands",
    "chest-breathing",
    "abdomen-lower-back",
    "hips-thighs",
    "lower-legs-feet",
    "whole-body-awareness",
]
COUNTS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolved(plan):
    return list(iter_events(resolve_document(plan["template_plan"], "en-US")))


def relaxation(events):
    return [e for e in events if e["id"].startswith("relaxation.") and e.get("text")]


def test_current_relaxation_resource_order_and_anatomical_segmentation():
    catalog = LocaleCatalog().with_revision(REVISION, "en-US")
    keys = [f"hplus.shared.relaxation.{part}" for part in KEY_PARTS]
    entries = [catalog.resource(k, "en-US", domain="narration", fallback=False)[0] for k in keys]
    text = "\n\n".join(entry.text for entry in entries)
    assert (
        re.findall(r"^(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.$", text, re.M) == COUNTS
    )
    assert [entry.text.splitlines()[0] for entry in entries[1:]] == [f"{c}." for c in COUNTS]
    assert [len(e.text.split("\n\n")) for e in entries] == [2] + [1] * 9 + [2]
    for entry in entries:
        assert entry.status == "reviewed" and entry.version == "2.0.0"
        assert len(entry.timing["pacing_units"]) == len(split_speech_units(entry.text))
    assert text.strip()


@pytest.mark.parametrize("owner", ["OCF-FND-002", "OCF-SEN-001"])
def test_normal_function_default_consumes_long_successor(owner):
    # This checkpoint is now an explicit historical edition; v3 owns the
    # current default and deliberately changes other shared stages.
    plan = build_complete_session_plan(owner, template="OCF-TPL-SESSION-HPLUS-LOCKED-006")
    assert plan["template"]["id"] == "OCF-TPL-SESSION-HPLUS-LOCKED-006"
    assert plan["template_plan"]["narration_revision"] == REVISION
    events = resolved(plan)
    body = relaxation(events)
    assert [e["id"] for e in body] == [f"relaxation.{part}" for part in KEY_PARTS]
    assert "\n\n".join(e["text"] for e in body).strip()
    old = build_complete_session_plan(owner, template="OCF-TPL-SESSION-HPLUS-LOCKED-005")
    # All unrelated spoken text and event policy is identical; downstream absolute
    # timing is intentionally not frozen to the old speech duration.
    before = {e["id"]: e for e in resolved(old) if not e["id"].startswith("relaxation.")}
    after = {e["id"]: e for e in events if not e["id"].startswith("relaxation.")}
    assert before == after
    for field in (
        "state_directives",
        "effective_state_directives",
        "ignored_state_directives",
        "resolved_dsp_profile",
    ):
        assert plan[field] == old[field]
    assert sum(e.get("semantic") == "function.instruction" for e in events) == 4
    assert plan["resolved_pacing_profile"]["underlay"] == old["resolved_pacing_profile"]["underlay"]


def test_every_active_shared_consumer_has_explicit_successor_binding():
    records = load_all_functions()
    assert len(records) == 59
    for record in records:
        binding = record.data["content"]["bindings"]
        assert binding["default_session_template"] == audio_defaults.TEMPLATE_ID
        if record.id == "OCF-EXP-007":
            assert binding["session_templates"] == [
                audio_defaults.TEMPLATE_ID,
                "OCF-TPL-SESSION-HPLUS-LOCKED-007",
            ]
            continue
        assert {"OCF-TPL-SESSION-HPLUS-LOCKED-005", audio_defaults.TEMPLATE_ID} <= set(
            binding["session_templates"]
        )


def test_current_narration_and_audio_default_metadata_are_readable():
    catalog = LocaleCatalog()
    pack = catalog.require("en-US")
    assert pack.entries
    for owner in load_all_functions():
        for row in owner.data["narration"]["sequence"]:
            entry, _ = catalog.resource(row["key"], "en-US", domain="narration", fallback=False)
            assert entry.text.strip()
    for identity in (
        "OCF-AUDIO-DEFAULTS-HPLUS-015",
        "OCF-AUDIO-DEFAULTS-HPLUS-016",
        "OCF-AUDIO-DEFAULTS-HPLUS-017",
        "OCF-AUDIO-DEFAULTS-HPLUS-022",
        "OCF-AUDIO-DEFAULTS-HPLUS-025",
    ):
        path = REPO_ROOT / "audio/defaults" / f"{identity}.json"
        assert json.loads(path.read_text())["release_ready"] is False
    assert audio_defaults.check_lock()["id"] == audio_defaults.BASELINE_ID


def test_current_function_text_resolves_through_historical_templates_and_rc1_stays_frozen():
    slots = {
        slot: f"hplus.function.ocf-sen-001.{slot.replace('_', '-')}"
        for slot in ("opener", "function_body", "closer")
    }
    historical = json.loads(
        (REPO_ROOT / "function-content/editorial/shared-session-v3-001.json").read_text()
    )
    for identity in (
        "OCF-TPL-SESSION-HPLUS-LOCKED-001",
        "OCF-TPL-SESSION-HPLUS-LOCKED-002",
        "OCF-TPL-SESSION-HPLUS-LOCKED-003",
        "OCF-TPL-SESSION-HPLUS-LOCKED-004",
        "OCF-TPL-SESSION-HPLUS-LOCKED-005",
        "OCF-TPL-SESSION-HPLUS-LOCKED-006",
    ):
        doc = compose(
            load_template(identity),
            {},
            title="Baseline",
            function_id="OCF-SEN-001",
            slot_keys={} if identity.endswith("PREP-LEARN-001") else slots,
        )
        events = list(iter_events(resolve_document(doc, "en-US")))
        catalog = LocaleCatalog()
        for slot, key in slots.items():
            current = catalog.resource(key, "en-US", domain="narration", fallback=False)[0].text
            matches = [event for event in events if event.get("slot_ref") == slot]
            assert len(matches) == (4 if slot == "function_body" else 1), identity
            assert all(event.get("text") == current for event in matches), identity
    rc1 = resolve_document(
        compose(load_template("OCF-TPL-SESSION-PREP-LEARN-001"), {}, title="Frozen RC1"),
        "en-US",
    )
    assert {event["id"]: digest(event.get("text", "")) for event in iter_events(rc1)} == historical[
        "rc1_event_text_sha256"
    ]


def test_successor_section_and_pause_policy_are_strictly_scoped():
    old = load_template("OCF-TPL-SESSION-HPLUS-LOCKED-005")
    new = load_template("OCF-TPL-SESSION-HPLUS-LOCKED-006")
    assert [s for s in old["sections"] if s["id"] != "relaxation"] == [
        s for s in new["sections"] if s["id"] != "relaxation"
    ]
    plan = build_complete_session_plan("OCF-SEN-001", template="OCF-TPL-SESSION-HPLUS-LOCKED-006")
    previous = build_complete_session_plan("OCF-SEN-001", template=old["id"])
    for field in (
        "pauses",
        "transitions",
        "estimate",
        "voice_profile_id",
        "repetitions",
        "duration_preference",
    ):
        assert plan["resolved_pacing_profile"][field] == previous["resolved_pacing_profile"][field]
    events = resolved(plan)
    for event in relaxation(events):
        paced = plan_event_pacing(plan["template_plan"], event)
        assert paced and paced["rate_scale"] == 0.88
        assert " ".join(u["text"] for u in paced["units"]) == " ".join(event["text"].split())
        # The last unit uses only the existing event hold, not landing+hold.
        assert paced["units"][-1]["pause_inside_event"] is False
        assert paced["units"][-1]["pause_after_s"] == event["timing"]["pause_after"]
        assert "preferred_duration" not in event["timing"]
    hold = next(e for e in events if e["id"] == "relaxation.whole")
    assert hold["timing"]["pause_after"] == 30
    assert (
        next(e for e in events if e["id"] == "body-comfort.breathing-hold")["timing"]["pause_after"]
        == 20
    )
    assert (
        next(e for e in events if e["id"] == "transmutation-box.place")["timing"]["pause_after"]
        == 20
    )


@pytest.mark.parametrize("choice", [None, "none", "Gateway", "SyncCreation", "OCF", "custom"])
def test_relaxation_revision_preserves_existing_affirmation_choices_and_explicit_enable(choice):
    slots = {
        "opener": "Synthetic opener.",
        "function_body": "Synthetic body.",
        "closer": "Synthetic closer.",
    }
    if choice == "custom":
        slots["affirmation"] = "Synthetic explicit custom text."
    selections = []
    for identity in ("OCF-TPL-SESSION-HPLUS-LOCKED-005", "OCF-TPL-SESSION-HPLUS-LOCKED-006"):
        doc = compose(
            load_template(identity),
            slots,
            title="Fixture",
            enabled_stages=["affirmation"],
            affirmation=choice,
        )
        selections.append([e for e in iter_events(doc) if e["id"].startswith("affirmation.")])
        if choice is None:
            assert "affirmation_selection" not in doc
        else:
            assert doc["affirmation_selection"] == choice
    assert selections[0] == selections[1]
    assert len(selections[1]) == (0 if choice == "none" else 3)


def test_strict_revision_locale_and_duplicate_keys_are_not_bypassed():
    with pytest.raises(OCFError):
        LocaleCatalog().with_revision(REVISION, "es")
    with pytest.raises(Exception, match="duplicate"):
        yaml_safe_load("locale: en-US\nlocale: es\n")


def test_text_addressed_cache_cannot_reuse_old_relaxation(monkeypatch):
    monkeypatch.setattr("ocf_tools.speech_cache.voice_identity", lambda spec: {"fixture": True})
    old = LocaleCatalog()
    new = old.with_revision("OCF-RELAXATION-LONG-002", "en-US")
    for part in ("begin", "face", "shoulders", "hands"):
        key = f"hplus.shared.relaxation.{part}"
        a = old.resource(key, "en-US", domain="narration", fallback=False)[0]
        b = new.resource(key, "en-US", domain="narration", fallback=False)[0]
        assert a.text != b.text and a.version != b.version
        assert (
            _synthesis_identity({"locale": "en-US"}, a.text)[1]
            != _synthesis_identity({"locale": "en-US"}, b.text)[1]
        )


def test_predecessor_landing_pacing_remains_available_explicitly():
    plan = build_complete_session_plan("OCF-SLP-005", template="OCF-TPL-SESSION-HPLUS-LOCKED-005")
    torso = next(
        item
        for item in plan["narration_pacing_plan"]
        if item["narration_key"] == "hplus.shared.relaxation.torso"
    )
    landings = [unit for unit in torso["units"] if unit["text"] == "Sleep."]
    assert [unit["kind"] for unit in landings] == ["landing"] * 4
    assert [unit["pause_after_s"] for unit in landings] == [5.0, 5.0, 5.0, 6.0]


def test_generated_shared_plan_fingerprints_come_from_selected_yaml():
    _, shared, _ = source_plan("OCF-FND-002")
    resources = {row["key"]: row for row in shared["resources"]}
    catalog = LocaleCatalog().with_revision("OCF-SHARED-SESSION-003", "en-US")
    for key, resource in resources.items():
        entry = catalog.resource(key, "en-US", domain="narration", fallback=False)[0]
        assert resource["text_sha256"] == digest(entry.text)
        assert resource["version"] == entry.version


def test_pronunciation_preflight_retains_revision_with_a_base_catalog():
    from ocf_tools.voice import _pronunciation_hints

    plan = build_complete_session_plan("OCF-SEN-001")
    doc = resolve_document(plan["template_plan"], "en-US")
    # Renderer/cache callers may supply their general catalog; pronunciation
    # must consult the selected revision just like text and integrity do.
    assert isinstance(_pronunciation_hints(doc, "en-US", LocaleCatalog(), "piper"), dict)


def test_speech_relative_timeline_never_caps_new_long_speech():
    plan = build_complete_session_plan("OCF-SEN-001", template="OCF-TPL-SESSION-HPLUS-LOCKED-006")
    doc = resolve_document(plan["template_plan"], "en-US")
    events = list(iter_events(doc))
    # Synthetic long measurements deliberately exceed the old session target.
    # These are test inputs, not a new silence or delivery-rate policy.
    durations = {e["id"]: 300.0 if e.get("text") else 0.0 for e in events}
    timed, problems = resolve_timeline(doc, speech_durations=durations)
    assert not problems
    starts = {e.id: e.at for e in timed}
    by_id = {e["id"]: e for e in events}
    for event in events:
        if event["id"].startswith("relaxation.") and event.get("after"):
            previous = event["after"]
            assert starts[event["id"]] == pytest.approx(
                starts[previous]
                + durations[previous]
                + by_id[previous].get("timing", {}).get("pause_after", 0)
            )
    assert starts["focus-ten.learn"] > starts["relaxation.whole-body-awareness"] + 300
    assert starts["session-complete.signal"] > 2700


@pytest.mark.parametrize("owner", ["OCF-FND-002", "OCF-SEN-001"])
def test_cli_normal_complete_route_selects_long_form(owner, capsys, monkeypatch):
    from ocf_tools import cli, narration_first

    # Only optional backend discovery is isolated; selection/composition and the
    # CLI complete-session route run normally, without a template override.
    monkeypatch.setattr(
        narration_first,
        "_voice_profile",
        lambda query, locale, catalog: (
            {
                "id": "OCF-VOICE-0003",
                "slug": "fixture",
                "name": "Fixture",
                "backend": "piper",
                "piper_length_scale": 1.12,
            },
            {"name": "piper", "language": "en_US", "wpm": None},
        ),
    )
    assert cli.main(["audio", "render", owner, "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dry_run"] is True
    plan = report["session_plan"]
    assert plan["template"]["id"] == audio_defaults.TEMPLATE_ID
    assert "\n\n".join(e["text"] for e in relaxation(resolved(plan))).strip()
