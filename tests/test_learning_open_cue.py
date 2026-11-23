"""Preparation Learning's first access cue must not change routine narration."""

import pytest
from ocf_tools.learning_session import TEMPLATE, plan
from ocf_tools.locale import LocaleCatalog, iter_events
from ocf_tools.narration_pacing import plan_event_pacing
from ocf_tools.session import load_template


@pytest.mark.parametrize("pacing", [None, "OCF-PACING-NANO-FARFIELD-LEARNING-001"])
def test_standalone_first_opening_preserves_cue_and_pacing(pacing):
    result = plan(locale="en-US", native_speed=True, pacing_profile=pacing)
    document = result["document"]
    events = {e["id"]: e for e in iter_events(document)}
    assert result["practice_seconds"] == 510
    assert [events[f"open-{i}.ready"]["timing"]["pause_after"] for i in range(1, 4)] == [90] * 3
    first = events["open-1.prepare"]
    assert first["narration_key"] == "preparation.learning.v3.open-1"
    assert 'Think or say in your mind: "Plus Eleven Access."' in first["text"]
    assert first["timing"]["narration_pacing_units"] == ["instruction"] * 4
    policy = document.get("narration_pacing", {}).get("entries", {})
    if "hplus.shared.focus11.open.prepare" in policy:
        assert policy[first["narration_key"]] == "guided-transition"
        units = plan_event_pacing(document, first)["units"]
        assert any(
            unit["text"] == 'Think or say in your mind: "Plus Eleven Access."' for unit in units
        )
    assert events["open-2.prepare"]["narration_key"] == "preparation.learning.v3.open-2"
    assert events["open-3.prepare"]["narration_key"] == "preparation.learning.v3.open-3"
    locked = next(
        section for section in load_template(TEMPLATE)["sections"] if section["id"] == "open-1"
    )
    assert locked["narration"]["prepare"]["narration_key"] == "hplus.shared.focus11.open.prepare"
    catalog = LocaleCatalog().with_revision("OCF-SHARED-SESSION-003", "en-US")
    shared, _ = catalog.raw_resource("hplus.shared.focus11.open.prepare", "en-US", fallback=False)
    assert 'Think or say in your mind, "{{ state.access.open }}."' in shared.text
