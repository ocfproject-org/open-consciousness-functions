"""Current source-plan generation reuses its catalog and returns current data."""

import pytest
from ocf_tools import audio_defaults, complete_session
from ocf_tools.session_plans import source_plan

pytestmark = pytest.mark.integration


def test_plan_reuses_completeness_catalog_and_tracks_current_function_source(monkeypatch):
    original = complete_session.LocaleCatalog
    created = []

    def counted():
        catalog = original()
        created.append(catalog)
        return catalog

    monkeypatch.setattr(complete_session, "LocaleCatalog", counted)
    plan, shared, _expanded = source_plan("OCF-FND-002")
    assert len(created) == 1
    assert plan["function_id"] == "OCF-FND-002"
    assert plan["approval"]["release_ready"] is False
    assert shared["defaults_lock"].endswith(f"{audio_defaults.BASELINE_ID}.json")
    assert shared["profiles"] == audio_defaults.check_lock()["profiles"]
    assert shared["timing"]["body_repetitions"] == {"programming": 2, "sleep": 2}
    assert any(
        resource["key"] == "hplus.function.ocf-fnd-002.function-body"
        for resource in plan["resources"]
    )
    assert all(
        path.startswith(("audio/templates/", "audio/background/"))
        for path in audio_defaults.check_lock()["files"]
    )
