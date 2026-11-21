"""Canonical function schemas and behavior are checked without frozen wording hashes."""

from copy import deepcopy

import pytest
from ocf_tools.function_catalog import resources, structural_contract
from ocf_tools.paths import REPO_ROOT
from ocf_tools.validators import _load_schema, validate_against_schema

pytestmark = pytest.mark.integration


def test_all_canonical_resources_have_valid_structure_and_four_pass_schedules():
    rows = resources(REPO_ROOT)
    assert len(rows) == 59
    identities = {data["function_id"] for _, data in rows}
    assert len(identities) == 59
    schema = _load_schema("localized-function.schema.json")
    for _, data in rows:
        assert not validate_against_schema(data, schema), data["function_id"]
        assert structural_contract(data)["function_id"] == data["function_id"]
        expected = [("opener", 1), ("function-body", 4), ("closer", 1)]
        sequence = data["narration"]["sequence"]
        if data["function_id"] == "OCF-EXP-007":
            expected[1:1] = [("guided-practice", 1), ("guided-practice", 1)]
            assert [row["key"].rsplit(".", 1)[-1] for row in sequence[1:3]] == [
                "guided-first",
                "guided-second",
            ]
        assert [(row["role"], row["repetitions"]) for row in sequence] == expected
        assert "contract_sha256" not in data.get("localization", {})


@pytest.mark.parametrize("field", ["command", "lifecycle", "cue"])
def test_behavioral_schema_rejects_invalid_structure_without_text_snapshots(field):
    _, source = next(row for row in resources(REPO_ROOT) if row[1]["function_id"] == "OCF-FND-002")
    changed = deepcopy(source)
    if field == "command":
        changed["activation"]["command_id"] = "not-a-command-id"
    elif field == "lifecycle":
        changed["lifecycle"]["persistence"] = "unrecognized"
    else:
        changed["activation"]["spoken_cue"]["text"] = ""
    assert validate_against_schema(changed, _load_schema("localized-function.schema.json"))
