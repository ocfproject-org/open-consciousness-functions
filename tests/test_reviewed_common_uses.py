"""Owner-reviewed discovery examples remain canonical data, not narration."""

import pytest
from ocf_tools.locale import LocaleCatalog
from ocf_tools.public_site_export import export_data

pytestmark = pytest.mark.integration


def test_reviewed_use_case_batch_is_complete_in_effective_catalog():
    catalog = LocaleCatalog()
    assert not catalog.problems
    resources = catalog.require("en-US").localized_functions
    reviewed = {
        identity: [
            row
            for row in resource["common_uses"]
            if (row.get("notes") or "").startswith("Use-case review;")
        ]
        for identity, resource in resources.items()
    }
    energy = reviewed["OCF-EXP-007"]
    assert {row["semantic_id"] for row in energy} == {
        "energy-ball-settle",
        "energy-ball-centering-pause",
        "energy-ball-chosen-quality",
    }
    original_review = {key: rows for key, rows in reviewed.items() if key != "OCF-EXP-007"}
    assert sum(map(len, original_review.values())) == 206
    assert sum(bool(rows) for rows in original_review.values()) == 57
    assert reviewed["OCF-EXP-005"] == []
    for identity, rows in reviewed.items():
        assert all(row["status"] == "reviewed" for row in rows), identity
        assert len({row["semantic_id"] for row in rows}) == len(rows), identity
        assert len({" ".join(row["text"].split()) for row in rows}) == len(rows), identity
    assert next(
        row["text"] for row in reviewed["OCF-FND-001"] if row["semantic_id"] == "energy-for-task"
    ) == (
        "Before a routine task that calls for enthusiasm, use Access to Energy "
        "as an intention for readiness."
    )


def test_public_export_preserves_all_use_text_and_editorial_status():
    resources = LocaleCatalog().require("en-US").localized_functions
    exported = export_data(source_commit="a" * 40)
    for function in exported["functions"]:
        uses = resources[function["function_id"]]["common_uses"]
        assert function["common_uses"] == [
            {"text": row["text"], "status": row["status"]} for row in uses
        ]
        assert all(set(row) == {"text", "status"} for row in function["common_uses"])
    # Export retains status labels; the downstream site gates display and search.
    assert any(
        row["status"] == "draft"
        for function in exported["functions"]
        for row in function["common_uses"]
    )
    assert exported["build_receipt"]["narration_text_included"] is False
