"""Reuse preflight catalogs without changing complete-session declarations."""

import hashlib

import pytest
from ocf_tools import complete_session
from ocf_tools.session_plans import serialize, source_plan

pytestmark = pytest.mark.integration


def test_plan_reuses_completeness_catalog_and_retains_exact_baseline(monkeypatch):
    original = complete_session.LocaleCatalog
    created = []

    def counted():
        catalog = original()
        created.append(catalog)
        return catalog

    monkeypatch.setattr(complete_session, "LocaleCatalog", counted)
    plan, shared, expanded = source_plan("OCF-FND-002")
    assert len(created) == 1
    # Source-only successors advance defaults identity and fingerprints without
    # changing locked profiles or timing. Compare each immutable layer in order.
    text = serialize({"plan": plan, "shared": shared, "expanded": expanded})
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "849b810b7f1ac31c9b9f64d9b90ae0406f8d513156f22ef11bcceb8ad9682557"
    )
    successor_025_to_024 = {
        "OCF-AUDIO-DEFAULTS-HPLUS-025": "OCF-AUDIO-DEFAULTS-HPLUS-024",
        "7f8876ee26c1e7df04641c964b6ed1746a4e72a39e30bc9121cb52b37f5a7d6a": "b34e08681d5fa7849db0915e9804f04e24398d786852b9f8fba7314dd6d07ee7",
        "740fd864eb5920d24142162311996ab266be67b72880b36699dce58985f885a6": "0cc257a2fb2bfa71ff9364b15fa58cf9c77e0d925aa103e91937e6d5ac5d126f",
    }
    for current, previous in successor_025_to_024.items():
        assert text.count(current) == 1
        text = text.replace(current, previous)
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "310a2aed86ab71269c99a09549b0f92c6867e21b6176a2078842604707c4f715"
    )
    successor_024_to_023 = {
        "OCF-AUDIO-DEFAULTS-HPLUS-024": "OCF-AUDIO-DEFAULTS-HPLUS-023",
        "b34e08681d5fa7849db0915e9804f04e24398d786852b9f8fba7314dd6d07ee7": "82c814ad5edb1d5ea876f57d52d25819bea3f4e92431eb6659df0e8d12bbe8f8",
        "0cc257a2fb2bfa71ff9364b15fa58cf9c77e0d925aa103e91937e6d5ac5d126f": "0e15db0c0d7dc9a346099fcafdb1742d79db84fa03d43bfd57f88688e9209fb0",
    }
    for current, previous in successor_024_to_023.items():
        assert text.count(current) == 1
        text = text.replace(current, previous)
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "fe01823856fc3111ae1fe5641e2bca3458f64d97563eabaeffa466c8b2ef4eef"
    )
    successor_023_to_022 = {
        "OCF-AUDIO-DEFAULTS-HPLUS-023": "OCF-AUDIO-DEFAULTS-HPLUS-022",
        "82c814ad5edb1d5ea876f57d52d25819bea3f4e92431eb6659df0e8d12bbe8f8": "05fcb04b428949613122bd50b92c6f6175be5af3dda65a25d0062c26c99e11bf",
        "0e15db0c0d7dc9a346099fcafdb1742d79db84fa03d43bfd57f88688e9209fb0": "e114398498a94ffd57b6cf4b57401bc54c8cb8f8d8b212105a48f3aadc7e56fe",
    }
    for current, previous in successor_023_to_022.items():
        assert text.count(current) == 1
        text = text.replace(current, previous)
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "944c4178f96ba02b59f3fd584a8ec0b4c39c4ec4f1a6a65ca81c120152a642a6"
    )
    successor_022_to_020 = {
        "OCF-AUDIO-DEFAULTS-HPLUS-022": "OCF-AUDIO-DEFAULTS-HPLUS-020",
        "05fcb04b428949613122bd50b92c6f6175be5af3dda65a25d0062c26c99e11bf": "339ff152899937803c91808ac0d12e306d87930296c4c71790c0e5282e418ac2",
        "e114398498a94ffd57b6cf4b57401bc54c8cb8f8d8b212105a48f3aadc7e56fe": "4e93f381960d57172c6fe231cc6a55ce815da2ab88f97da25178e80ac744d50e",
    }
    for current, previous in successor_022_to_020.items():
        assert text.count(current) == 1
        text = text.replace(current, previous)
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "90d4fb98730c06452c65ed71f5a813fe6904710dd147941697b0bbd5ad85e53e"
    )
    successor_020_to_018 = {
        "OCF-AUDIO-DEFAULTS-HPLUS-020": "OCF-AUDIO-DEFAULTS-HPLUS-018",
        "339ff152899937803c91808ac0d12e306d87930296c4c71790c0e5282e418ac2": "e90b27d729273f913939cda8275ad5dd3533f35f613bc6a610f1122bde7e668e",
        "4e93f381960d57172c6fe231cc6a55ce815da2ab88f97da25178e80ac744d50e": "bcdc6389258d1b78e2ca626c73b5bf5e6bddc41c213e443df534bc6bbb68a28d",
    }
    for current, previous in successor_020_to_018.items():
        assert text.count(current) == 1
        text = text.replace(current, previous)
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "83cb7ec6d40d5cc9817012826a880f3b1d43bf3d9d54c256da263ef06c6a16d3"
    )
