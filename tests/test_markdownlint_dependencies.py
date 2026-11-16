"""Actionable Markdownlint dependency setup diagnostics."""

import json

import pytest
from tools import check_markdownlint_dependencies as markdownlint

pytestmark = pytest.mark.unit


def test_missing_node_or_npm_has_setup_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr(markdownlint.shutil, "which", lambda _name: None)
    error = markdownlint.check(tmp_path)
    assert error is not None and "Node.js 22.20.0" in error and "npm ci" in error


def test_missing_or_wrong_cli_dependency_has_setup_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr(markdownlint.shutil, "which", lambda _name: "/usr/bin/tool")
    assert "Run npm ci" in markdownlint.check(tmp_path)

    package = tmp_path / "node_modules/markdownlint-cli2/package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"version": "0.13.0"}), encoding="utf-8")
    assert "expected pinned 0.14.0" in markdownlint.check(tmp_path)


def test_pinned_cli_dependency_is_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr(markdownlint.shutil, "which", lambda _name: "/usr/bin/tool")
    package = tmp_path / "node_modules/markdownlint-cli2/package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"version": "0.14.0"}), encoding="utf-8")
    assert markdownlint.check(tmp_path) is None
