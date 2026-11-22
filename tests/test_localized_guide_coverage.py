"""L5 preparation: exact complete resources, fundamentals-first navigation."""

import pytest
from ocf_tools.indexes import load_all_functions
from ocf_tools.listening_guides import _guide_catalog, function_guide_markdown, portable_index_html
from ocf_tools.locale import LocaleCatalog

pytestmark = pytest.mark.integration


def test_all_function_resources_appear_with_preparation_closure_explicitly_excluded():
    catalog = LocaleCatalog()
    count = 0
    energy_ball_waking = set()
    for record in load_all_functions():
        metadata, _ = catalog.localized_function(record.id, "en-US", fallback=False)
        text = function_guide_markdown(record, catalog=catalog)
        for key in metadata["entries"]:
            entry, _ = catalog.resource(key, "en-US", domain="narration", fallback=False)
            if key.endswith(".access-close"):
                assert entry.text not in text
                continue
            assert key not in text and entry.text in text, (record.id, key)
            if key.startswith("hplus.function.ocf-exp-007.waking-"):
                energy_ball_waking.add(key.rsplit(".", 1)[-1])
            count += 1
        if record.id == "OCF-FND-001":
            assert "Access channel closure" not in text
            assert "plus, release, eleven, access" not in text
    assert energy_ball_waking == {
        "waking-descent",
        "waking-ten",
        "waking-count-to-one",
        "waking-alert",
        "waking-reorient",
    }
    assert count == 197


def test_foundation_navigation_precedes_other_categories_in_markdown_and_offline_html():
    records = load_all_functions()
    markdown = _guide_catalog(records)
    html = portable_index_html(records).decode("utf-8")
    assert markdown.index("## foundation") < markdown.index("## automation")
    assert html.index("<h2>foundation</h2>") < html.index("<h2>automation</h2>")
    assert len([line for line in markdown.splitlines() if line.startswith("- [")]) == 59
