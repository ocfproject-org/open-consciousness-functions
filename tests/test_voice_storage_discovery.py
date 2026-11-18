"""Portable discovery of private voices across launch roots and worktrees."""

import json

import pytest
from ocf_tools import custom_voices, voice_packs
from ocf_tools.utils import OCFError

pytestmark = pytest.mark.unit


def write_config(home, profile_dir, asset_dir):
    path = home / ".config/ocf/voice-storage.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {"schema_version": 1, "profile_dir": str(profile_dir), "asset_dir": str(asset_dir)}
        )
    )
    path.chmod(0o600)
    return path


def test_private_storage_config_is_account_home_and_worktree_independent(monkeypatch, tmp_path):
    home = tmp_path / "account"
    profiles, assets = home / "voice-profiles", home / "voice-assets"
    config = write_config(home, profiles, assets)
    monkeypatch.setenv("OCF_VOICE_CONFIG", str(config))
    monkeypatch.setattr(custom_voices, "_account_home", lambda: home)
    monkeypatch.setenv("HOME", str(tmp_path / "launcher-home"))
    monkeypatch.delenv("OCF_VOICE_PROFILE_DIR", raising=False)
    monkeypatch.delenv("OCF_VOICE_ASSETS", raising=False)
    monkeypatch.chdir(tmp_path)

    assert custom_voices.profile_root() == profiles
    assert custom_voices.asset_root() == assets


def test_explicit_voice_roots_override_persistent_config(monkeypatch, tmp_path):
    home = tmp_path / "account"
    config = write_config(home, home / "configured-profiles", home / "configured-assets")
    monkeypatch.setenv("OCF_VOICE_CONFIG", str(config))
    monkeypatch.setattr(custom_voices, "_account_home", lambda: home)
    monkeypatch.setenv("OCF_VOICE_PROFILE_DIR", str(tmp_path / "override-profiles"))
    monkeypatch.setenv("OCF_VOICE_ASSETS", str(tmp_path / "override-assets"))

    assert custom_voices.profile_root() == (tmp_path / "override-profiles").resolve()
    assert custom_voices.asset_root() == (tmp_path / "override-assets").resolve()


def test_model_cache_and_runtime_use_persistent_config_and_environment_overrides(
    monkeypatch, tmp_path
):
    from ocf_tools import voice_packs

    home = tmp_path / "account"
    config = write_config(home, home / "profiles", home / "assets")
    monkeypatch.setenv("OCF_VOICE_CONFIG", str(config))
    settings = json.loads(config.read_text())
    settings.update(
        hf_hub_cache=str(home / "models/hub"),
        chatterbox_python=str(home / "runtime/bin/python"),
    )
    config.write_text(json.dumps(settings))
    config.chmod(0o600)
    monkeypatch.setattr(custom_voices, "_account_home", lambda: home)
    monkeypatch.delenv("OCF_CHATTERBOX_PYTHON", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)

    assert voice_packs.model_cache_root() == home / "models/hub"
    assert voice_packs.runtime_interpreter() == home / "runtime/bin/python"
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "override-hub"))
    monkeypatch.setenv("OCF_CHATTERBOX_PYTHON", str(tmp_path / "override-python"))
    assert voice_packs.model_cache_root() == tmp_path / "override-hub"
    assert voice_packs.runtime_interpreter() == tmp_path / "override-python"


def test_missing_private_config_keeps_repository_cache_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(custom_voices, "_account_home", lambda: tmp_path / "empty-home")
    monkeypatch.setenv("OCF_VOICE_CONFIG", str(tmp_path / "missing.json"))
    monkeypatch.setenv("OCF_VOICE_PROFILE_DIR", "")
    monkeypatch.setenv("OCF_VOICE_ASSETS", "")
    monkeypatch.setenv("OCF_WORK_DIR", str(tmp_path / "work"))

    assert custom_voices.profile_root() == tmp_path / "work/cache/voices/profiles"
    assert custom_voices.asset_root() == tmp_path / "work/cache/voices/models"


def test_private_config_rejects_non_private_permissions(monkeypatch, tmp_path):
    home = tmp_path / "account"
    config = write_config(home, home / "profiles", home / "assets")
    config.chmod(0o644)
    monkeypatch.setenv("OCF_VOICE_CONFIG", str(config))
    monkeypatch.setattr(custom_voices, "_account_home", lambda: home)
    monkeypatch.delenv("OCF_VOICE_PROFILE_DIR", raising=False)

    with pytest.raises(OCFError, match="permissions must be private"):
        custom_voices.profile_root()


def test_production_preflight_requires_exact_private_voice_and_reports_checked_root(
    monkeypatch, tmp_path
):
    root = tmp_path / "profiles"
    monkeypatch.setattr(custom_voices, "profile_root", lambda: root)
    monkeypatch.setattr(custom_voices, "asset_root", lambda: tmp_path / "assets")
    monkeypatch.setattr(voice_packs, "load_voice_profiles", lambda: [])

    with pytest.raises(OCFError, match=r"OCF-VOICE-9100.*profiles"):
        voice_packs.production_preflight("OCF-VOICE-9100")


def test_production_preflight_rejects_conflicting_private_identities(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profile = {"id": "OCF-VOICE-9100", "backend": "chatterbox-nano"}
    monkeypatch.setattr(custom_voices, "profile_root", lambda: profiles)
    monkeypatch.setattr(voice_packs, "load_voice_profiles", lambda: [profile, dict(profile)])

    with pytest.raises(OCFError, match="exactly one.*OCF-VOICE-9100"):
        voice_packs.production_preflight("OCF-VOICE-9100")


def test_production_preflight_keeps_explicit_voice_backend(monkeypatch, tmp_path):
    profile = {
        "id": "OCF-VOICE-9100",
        "backend": "chatterbox-nano",
        "reference_audio": {
            "model_revision": "revision",
            "model_files": {"weights.bin": "b" * 64},
            "sha256": "a" * 64,
        },
    }
    runtime = tmp_path / "chatterbox-python"
    runtime.touch()
    monkeypatch.setattr(custom_voices, "profile_root", lambda: tmp_path / "profiles")
    monkeypatch.setattr(custom_voices, "asset_root", lambda: tmp_path / "assets")
    monkeypatch.setattr(voice_packs, "load_voice_profiles", lambda: [profile])
    monkeypatch.setattr(voice_packs, "runtime_interpreter", lambda: runtime)
    monkeypatch.setattr(voice_packs, "cached_model_revision", lambda: "revision")
    monkeypatch.setattr(
        voice_packs, "_cached_model_file_hashes", lambda _revision: {"weights.bin": "b" * 64}
    )
    monkeypatch.setattr(
        custom_voices,
        "validate_profile",
        lambda _profile: {"valid": True, "assets_checked": True, "inference_verified": True},
    )

    result = voice_packs.production_preflight("OCF-VOICE-9100")
    assert result["voice_id"] == "OCF-VOICE-9100"
    assert result["backend"] == "chatterbox-nano"
    assert result["inference_verified"] is True


def test_production_preflight_reports_missing_reference_root(monkeypatch, tmp_path):
    profile = {"id": "OCF-VOICE-9100", "backend": "chatterbox-nano"}
    profiles, assets = tmp_path / "profiles", tmp_path / "assets"
    monkeypatch.setattr(custom_voices, "profile_root", lambda: profiles)
    monkeypatch.setattr(custom_voices, "asset_root", lambda: assets)
    monkeypatch.setattr(voice_packs, "load_voice_profiles", lambda: [profile])
    monkeypatch.setattr(
        custom_voices,
        "validate_profile",
        lambda _profile: (_ for _ in ()).throw(OCFError("reference audio missing")),
    )

    with pytest.raises(OCFError, match="profiles:.*assets:.*reference audio missing"):
        voice_packs.production_preflight("OCF-VOICE-9100")
