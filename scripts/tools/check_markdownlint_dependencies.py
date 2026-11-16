"""Give actionable setup errors for the pinned local Markdownlint tool."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "0.14.0"


def check(root: Path = REPO_ROOT) -> str | None:
    """Return an actionable failure message, or None when dependencies are ready."""
    missing_tools = [name for name in ("node", "npm") if shutil.which(name) is None]
    if missing_tools:
        return (
            "Node.js/npm is unavailable. Install Node.js 22.20.0 from .nvmrc, "
            "then run npm ci (see docs/SETUP.md)."
        )
    package = root / "node_modules/markdownlint-cli2/package.json"
    try:
        version = json.loads(package.read_text(encoding="utf-8"))["version"]
    except (OSError, json.JSONDecodeError, KeyError):
        return "markdownlint-cli2 is not installed. Run npm ci from the repository root."
    if version != EXPECTED_VERSION:
        return (
            f"markdownlint-cli2 {version} is installed; expected pinned {EXPECTED_VERSION}. "
            "Run npm ci from the repository root."
        )
    return None


def main() -> int:
    failure = check()
    if failure:
        print(f"Markdownlint dependency error: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
