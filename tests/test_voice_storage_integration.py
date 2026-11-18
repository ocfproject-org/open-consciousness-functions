"""Fresh-process verification for persistent private voice discovery."""

import json
import os
import subprocess
import sys

import pytest
from ocf_tools import custom_voices

pytestmark = pytest.mark.integration


def test_fresh_noninteractive_process_loads_persisted_roots(tmp_path):
    home = tmp_path / "account"
    profiles, assets = home / "profiles", home / "assets"
    config = home / "voice-storage.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"schema_version": 1, "profile_dir": str(profiles), "asset_dir": str(assets)})
    )
    config.chmod(0o600)
    env = os.environ.copy()
    env.pop("OCF_VOICE_PROFILE_DIR", None)
    env.pop("OCF_VOICE_ASSETS", None)
    env["OCF_VOICE_CONFIG"] = str(config)
    env["HOME"] = str(tmp_path / "launcher-home")
    env["PYTHONPATH"] = str(custom_voices.REPO_ROOT / "scripts")
    code = (
        "import json; from ocf_tools.custom_voices import asset_root, profile_root; "
        "print(json.dumps([str(profile_root()), str(asset_root())]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [str(profiles), str(assets)]
