"""Validate current canonical narration structure and symbolic cue resolution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ocf_tools.function_catalog import resources  # noqa: E402
from ocf_tools.indexes import load_all_functions  # noqa: E402
from ocf_tools.locale import LocaleCatalog  # noqa: E402
from ocf_tools.paths import REPO_ROOT  # noqa: E402


def narration_texts(root: Path = REPO_ROOT) -> dict[str, str]:
    """Resolve the current narration entries directly from locale resources."""
    catalog = LocaleCatalog(
        root / "locales", function_records=lambda: load_all_functions(root=root)
    )
    pack = catalog.require("en-US")
    return {
        key: catalog.resource(key, "en-US", domain=entry.domain, fallback=False)[0].text
        for key, entry in pack.entries.items()
        if entry.domain == "narration"
    }


def check(root: Path = REPO_ROOT) -> list[str]:
    """Validate schedule, entry ownership and strict cue resolution; wording is not frozen."""
    catalog = LocaleCatalog(
        root / "locales", function_records=lambda: load_all_functions(root=root)
    )
    problems = list(catalog.problems)
    try:
        pack = catalog.require("en-US")
    except Exception as exc:
        return problems + [str(exc)]
    function_files = resources(root)
    identities = {data["function_id"] for _, data in function_files}
    if len(identities) < 58 or len(identities) != len(function_files):
        problems.append(
            "canonical narration catalog must preserve at least 58 unique en-US functions"
        )
    if identities != set(pack.localized_functions):
        problems.append("canonical narration files and discovered en-US functions differ")
    for _path, data in function_files:
        function_id = data["function_id"]
        sequence = data.get("narration", {}).get("sequence", [])
        expected = [("opener", 1), ("function-body", 4), ("closer", 1)]
        if function_id == "OCF-EXP-007":
            # The Energy Ball lesson has two guided practices before its
            # four passive associations. Keep ordinary function checks strict.
            expected[1:1] = [("guided-practice", 1)] * 2
        actual = [(row.get("role"), row.get("repetitions")) for row in sequence]
        if actual != expected:
            problems.append(f"{function_id}: narration schedule must be {expected}")
        for row in sequence:
            key = row.get("key", "")
            if key not in pack.entries:
                problems.append(f"{function_id}: missing canonical narration entry {key}")
    try:
        narration_texts(root)
    except Exception as exc:
        problems.append(str(exc))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="kept for command compatibility")
    parser.parse_args(argv)
    problems = check()
    if problems:
        print("Current narration validation failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(
        f"Current canonical narration validates: {len(resources(REPO_ROOT))} functions, "
        "session-specific schedules and cue resolution PASS."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
