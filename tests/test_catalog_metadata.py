"""Catalog-wide editorial status and immutable spoken-content boundaries."""

import pytest
from ocf_tools.locale import LocaleCatalog
from ocf_tools.paths import REPO_ROOT

pytestmark = pytest.mark.integration


def test_all_function_metadata_is_useful_draft_and_canonical_fields_are_single_source():
    catalog = LocaleCatalog()
    assert not catalog.problems
    pack = catalog.require("en-US")
    assert len(pack.localized_functions) == 58
    for identity, data in pack.localized_functions.items():
        assert 3 <= len(data["tags"]) <= 6
        assert 2 <= len(data["common_uses"]) <= 5
        assert all(
            value["status"] == "draft" and value["text"].strip()
            for field in ("tags", "common_uses")
            for value in data[field]
        )
        assert data["localization"]["status"] in {"complete", "partial"}
        assert "contract_sha256" not in data["localization"]
        approval = data.get("record_metadata", {}).get("editorial_approval", {})
        assert "resolved_text_sha256" not in approval
        assert "presented_snapshot_sha256" not in approval


def test_owner_approved_related_and_complementary_edges_remain_exact():
    from ocf_tools.guide_review import record, relationships, verify
    from ocf_tools.indexes import load_function_by_id

    pack = LocaleCatalog().require("en-US")
    ledger = record()
    assert verify() == []
    actual = []
    kinds = []
    for identity, data in pack.localized_functions.items():
        assert not data["relationships"].get("proposals", [])
        for kind in ("related_functions", "complementary_functions"):
            for edge in data["relationships"][kind]:
                actual.append((identity, edge["function_id"], edge["description"]["text"]))
                kinds.append(kind)
    expected = []
    for decision in ledger["decisions"]:
        owner = load_function_by_id(decision["source_id"])
        edge = next(
            row
            for row in relationships(owner)
            if row["relationship_id"] == decision["relationship_id"]
        )
        expected.append(
            (decision["source_id"], decision["related_id"], edge["approved_explanation"])
        )
    assert sorted(actual) == sorted(expected)
    assert len(actual) == 33
    assert kinds.count("related_functions") == 20
    assert kinds.count("complementary_functions") == 13


def test_current_locale_has_single_canonical_function_files_and_source_independent_lock():
    from ocf_tools.audio_defaults import check_lock
    from ocf_tools.function_catalog import resources

    pack = LocaleCatalog().require("en-US")
    declared = [r["file"] for r in pack.manifest["resources"]]
    assert len(declared) == len(set(declared))
    assert len(resources(REPO_ROOT)) == 58
    assert (
        len(pack.localized_function_files) == len(set(pack.localized_function_files.values())) == 58
    )
    # Authority is structural, not a blacklist of predecessor filenames.
    for path, data in resources(REPO_ROOT):
        assert path.name in declared
        assert data["domain"] == "function"
        assert pack.localized_function_files[data["function_id"]] == path.name
    for name in (
        "hplus-focus10.yaml",
        "hplus-focus11-open.yaml",
        "hplus-relaxation.yaml",
        "hplus-transmutation-box.yaml",
        "hplus-waking-return.yaml",
    ):
        assert name in declared and (pack.path / name).is_file()
    lock = check_lock()
    assert lock["id"] == "OCF-AUDIO-DEFAULTS-HPLUS-026"
    assert not any(path.startswith("locales/") for path in lock["files"])
