"""Exercise the real Make target's pinned Markdownlint dependency contract."""

import os
import shutil
import subprocess

import pytest
from conftest import REPO_ROOT
from tools.check_markdownlint_dependencies import check as markdownlint_dependency_error

pytestmark = [pytest.mark.integration, pytest.mark.external_tool]


@pytest.mark.skipif(os.name == "nt", reason="make is not part of the supported Windows dev setup")
def test_markdownlint_target_passes_or_reports_pinned_dependency_setup():
    make = shutil.which("make")
    if not make:
        pytest.skip("make is not installed")
    result = subprocess.run(
        [make, "lint-markdown"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    error = markdownlint_dependency_error()
    if error:
        assert result.returncode != 0
        assert "Markdownlint dependency error" in result.stderr
        assert error in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert "Summary:" in result.stdout
