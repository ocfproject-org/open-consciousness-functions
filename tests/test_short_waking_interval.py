"""The short waking interval counts completion pacing, not C1 tail time."""

import pytest
from ocf_tools.session import compose
from ocf_tools.timing import schedule_timeline
from ocf_tools.utils import OCFError
from ocf_tools.waking_c1 import policy

pytestmark = pytest.mark.integration


def _template():
    return {
        "schema_version": "1.0",
        "id": "OCF-TPL-SESSION-SHORT-WAKING-FIXTURE-001",
        "version": "1.0.0",
        "origin": "original-ocf",
        "slots": {"required": ["closer"]},
        "sections": [
            {"id": "return", "start": 0, "stage": "OCF-TPL-STAGE-HPLUS-ENERGY-BALL-WAKING-003"},
            {
                "id": "function-closer",
                "type": "outro",
                "slot": "closer",
                "semantic": "function.closer",
                "after": "$previous",
                "after_anchor": "event-end",
                "pace": "block",
                "trim_speech_padding": True,
            },
        ],
    }


def _pacing(complete):
    return {
        "id": "OCF-PACING-SHORT-WAKING-FIXTURE-001",
        "version": "1.0.0",
        "status": "approved_for_internal_composition",
        "pauses": {"waking_complete_s": complete},
    }


@pytest.mark.parametrize("complete", [0, 3, 9.5, 30])
def test_short_waking_total_survives_pacing_overrides(complete):
    doc = compose(
        _template(), {"closer": "Continue."}, title="Short return", pacing_profile=_pacing(complete)
    )
    events = {event["id"]: event for section in doc["sections"] for event in section["timeline"]}
    assert events["return.reorient"]["timing"]["pause_after"] == pytest.approx(30 - complete)
    assert events["return.complete"]["dsp"]["transition_s"] == complete
    assert "completion_total_s" not in events["return.complete"]
    assert events["function-closer.block"]["timing"]["trim_speech_padding"] is True
    durations = {"return.descent": 10, "return.ten": 0.5, "return.reorient": 2.33}
    times = {row["id"]: row for row in schedule_timeline(doc, durations)}
    assert times["function-closer.block"]["at"] == pytest.approx(
        times["return.reorient"]["at"] + durations["return.reorient"] + 30
    )
    assert policy(doc)["tail_after_speech_seconds"] == 30
    assert policy(doc)["closer_event_ids"] == ["function-closer.block"]


def test_short_waking_rejects_impossible_completion_and_unanchored_closer():
    with pytest.raises(OCFError, match="completion uses 31s, more than the 30s total"):
        compose(_template(), {"closer": "Continue."}, title="Short", pacing_profile=_pacing(31))
    template = _template()
    template["sections"][1]["after_anchor"] = "speech-end"
    with pytest.raises(OCFError, match="requires reorientation, one silent marker, and closer"):
        compose(template, {"closer": "Continue."}, title="Short", pacing_profile=_pacing(3))
