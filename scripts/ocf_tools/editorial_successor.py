"""Hash-only verification of the finite source-only November 14 editorial approval.

This module never supplies function content, restores predecessor wording, or
changes runtime resolution. Historical receipts remain immutable.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy

from .paths import REPO_ROOT
from .utils import OCFError

RECEIPT = "function-content/editorial/approved-editorial-20261114.json"
RECEIPT_SHA256 = "0610a99983a5121179c6d4f5e5450c89f01287d99619858d6f43f1b76d95010b"
SUCCESSOR_RECEIPT = "function-content/editorial/source-only-editorial-successor-23-20261114.json"
SUCCESSOR_RECEIPT_SHA256 = "b5d9189e312689e88ec86cb1079aa268a0a91f6663c4841176fc7e0381143eeb"
FINAL_SUCCESSOR_RECEIPT = (
    "function-content/editorial/source-only-editorial-successor-24-58-20261115.json"
)
FINAL_SUCCESSOR_RECEIPT_SHA256 = "7e9ca8a00ccf2904d4632f874f0ffee0ad416e4a2bed8d45bb912a0e0674da83"
SHARED_SESSION_PREDECESSOR_SHA256 = (
    "614947344808b446037addf290493dd6f26aefcfe2a17e81732ee166a7f53cc7"
)
DESCRIPTION_LEDGER_SHA256 = "dc139a5807b7abf11ad0e291fa8fd53edc736bbb36734d86526cc9648f30012b"
DESCRIPTION_MASTER_SHA256 = "aa5daaf619336b00d18237c0afa2e4feb3537bcd8992b927a198a9bff2dcbc79"
DESCRIPTION_PREDECESSOR_COMMIT = "0597df40bbffdc07012ef2fe7a318a084850342b"
APPROVAL_FIXTURE = "tests/fixtures/approved-editorial-batch-20261114.txt"
APPROVAL_SHA256 = "d21984367701da8475e0dd741f3e047e380466339fc869113632afb2d071700b"


def receipt(root=REPO_ROOT):
    raw = (root / RECEIPT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != RECEIPT_SHA256:
        raise OCFError("editorial successor receipt differs from approved scope")
    data = json.loads(raw)
    for path, expected in data["predecessors"].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise OCFError("editorial successor predecessor differs: " + path)
    extension_path = root / SUCCESSOR_RECEIPT
    extension_raw = extension_path.read_bytes()
    if hashlib.sha256(extension_raw).hexdigest() != SUCCESSOR_RECEIPT_SHA256:
        raise OCFError("source-only editorial integrity record differs from its pinned hash")
    extension = json.loads(extension_raw)
    approval = (root / APPROVAL_FIXTURE).read_bytes()
    if hashlib.sha256(approval).hexdigest() != APPROVAL_SHA256:
        raise OCFError("owner-supplied editorial attachment differs from its pinned hash")
    if extension.get("authority_attachment_sha256") != APPROVAL_SHA256:
        raise OCFError("source-only editorial integrity record authority hash differs")
    if extension.get("kind") != "source-only-editorial-integrity-successor":
        raise OCFError("unsupported source-only editorial integrity record")
    target_ids = set(re.findall(rb"(?m)^### (OCF-[A-Z]{3}-[0-9]{3}) ", approval))
    target_ids = {identity.decode("ascii") for identity in target_ids}
    if len(target_ids) != 23 or set(extension.get("resources", {})) != target_ids:
        raise OCFError("source-only editorial integrity identity set differs from attachment")
    defaults_path = root / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-021.json"
    if hashlib.sha256(defaults_path.read_bytes()).hexdigest() != extension.get(
        "predecessor_defaults_sha256"
    ):
        raise OCFError("source-only editorial predecessor audio baseline differs")
    for identity in target_ids & set(data["resources"]):
        if extension["resources"][identity]["before"] != data["resources"][identity]["after"]:
            raise OCFError("source-only editorial resource chain differs: " + identity)
    for kind, rows in extension.get("hashes", {}).items():
        for identity, row in rows.items():
            previous = data["hashes"].get(kind, {}).get(identity)
            if previous and row.get("before") != previous.get("after"):
                raise OCFError("source-only editorial hash chain differs: " + kind + "/" + identity)
    description_path = root / FINAL_SUCCESSOR_RECEIPT
    description_raw = description_path.read_bytes()
    if hashlib.sha256(description_raw).hexdigest() != FINAL_SUCCESSOR_RECEIPT_SHA256:
        raise OCFError("source-only 24-58 successor differs from its pinned hash")
    description_extension = json.loads(description_raw)
    if (
        description_extension.get("kind") != "source-only-editorial-successor-24-58"
        or description_extension.get("predecessor_commit") != DESCRIPTION_PREDECESSOR_COMMIT
        or description_extension.get("predecessor_successor_sha256") != SUCCESSOR_RECEIPT_SHA256
        or description_extension.get("authority_ledger_sha256") != DESCRIPTION_LEDGER_SHA256
        or description_extension.get("authority_master_prompt_sha256") != DESCRIPTION_MASTER_SHA256
    ):
        raise OCFError("source-only description successor authority chain differs")
    description_ids = set(description_extension.get("resource_ids", []))
    if (
        len(description_ids) != 33
        or description_ids & target_ids
        or set(description_extension.get("resources", {})) != description_ids
        or len(description_extension.get("description_sha256", {})) != 28
        or not set(description_extension.get("description_sha256", {})) <= description_ids
    ):
        raise OCFError("source-only description successor identity set differs")
    defaults_path = root / "audio/defaults/OCF-AUDIO-DEFAULTS-HPLUS-022.json"
    if hashlib.sha256(defaults_path.read_bytes()).hexdigest() != description_extension.get(
        "predecessor_defaults_sha256"
    ):
        raise OCFError("source-only description predecessor audio baseline differs")
    removed_entries = description_extension.get("removed_locale_entries", {})
    removed_entry_ids = {
        "commands.ocf-cmd-prf-006-release.display-cue",
        "commands.ocf-cmd-prf-006-release.explanation",
        "commands.ocf-cmd-prf-006-release.label",
        "commands.ocf-cmd-prf-006-release.spoken-cue",
        "commands.ocf-cmd-prf-006-release.usage",
    }
    predecessor_path = root / "function-content/editorial/shared-session-v3-001.json"
    predecessor_bytes = predecessor_path.read_bytes()
    if hashlib.sha256(predecessor_bytes).hexdigest() != SHARED_SESSION_PREDECESSOR_SHA256:
        raise OCFError("Strong-Quick historical command predecessor differs")
    predecessor_entries = json.loads(predecessor_bytes)["unchanged_canonical_entries"]
    if set(removed_entries) != removed_entry_ids or any(
        removed_entries[key] != predecessor_entries[key] for key in removed_entry_ids
    ):
        raise OCFError("Strong-Quick removed command history differs")
    frozen_events = json.loads(predecessor_bytes)["frozen_resolved_event_hashes"]
    shared_event_hashes = description_extension.get("shared_session_event_hashes", {})
    for owner, rows in shared_event_hashes.items():
        if owner not in frozen_events:
            raise OCFError("source-only shared-session owner differs: " + owner)
        for event_id, row in rows.items():
            if row.get("before") != frozen_events[owner].get(event_id) or not re.fullmatch(
                r"[0-9a-f]{64}", row.get("after", "")
            ):
                raise OCFError(
                    "source-only shared-session event hash differs: " + owner + "/" + event_id
                )
    combined = deepcopy(data)
    combined["resources"] = {**extension["resources"], **description_extension["resources"]}
    combined["added_locale_entries"] = {
        **extension.get("added_locale_entries", {}),
        **description_extension.get("added_locale_entries", {}),
    }
    combined["hashes"] = deepcopy(data["hashes"])
    for layer in (extension, description_extension):
        for kind, rows in layer["hashes"].items():
            combined["hashes"].setdefault(kind, {}).update(rows)
    combined["description_sha256"] = description_extension["description_sha256"]
    combined["shared_session_event_hashes"] = shared_event_hashes
    if combined["added_locale_entries"]:
        from .locale import LocaleCatalog

        catalog = LocaleCatalog(root / "locales")
        pack = catalog.require("en-US")
        for key, expected in combined["added_locale_entries"].items():
            entry = pack.entries.get(key)
            if entry is None:
                raise OCFError("source-only editorial locale entry is missing: " + key)
            raw_hash = hashlib.sha256(entry.text.encode("utf-8")).hexdigest()
            resolved_hash = hashlib.sha256(
                catalog.resource(key, "en-US", domain=entry.domain, fallback=False)[0].text.encode(
                    "utf-8"
                )
            ).hexdigest()
            if expected != {"raw_sha256": raw_hash, "resolved_sha256": resolved_hash}:
                raise OCFError("source-only editorial added locale entry differs: " + key)
    from .locale import LocaleCatalog

    current_entries = LocaleCatalog(root / "locales").require("en-US").entries
    if removed_entry_ids & set(current_entries):
        raise OCFError("Strong-Quick release remains an active localized command")
    combined["_removed_locale_entries"] = removed_entry_ids
    combined["_hash_chain"] = [data, extension, description_extension]
    return combined


def verify_resources(root=REPO_ROOT, snapshot=None):
    """Validate exact approved resources, including every untouched field."""
    from .function_catalog import resources

    approved = receipt(root)
    if snapshot is None:
        snapshot = {data["function_id"]: data for _, data in resources(root)}
    for identity, expected in approved["resources"].items():
        actual = hashlib.sha256(
            json.dumps(
                snapshot.get(identity), sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
        ).hexdigest()
        if actual != expected["after"]:
            raise OCFError("editorial successor canonical resource differs: " + identity)
    for identity, expected in approved.get("description_sha256", {}).items():
        text = snapshot[identity]["description"]["text"]
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            raise OCFError("source-only editorial description differs: " + identity)
    return approved


def expected_hash(kind, identity, previous, root=REPO_ROOT, *, approved=None):
    """Advance one exact historical hash; unrelated keys remain protected."""
    return _expected_hash(receipt(root) if approved is None else approved, kind, identity, previous)


def _expected_hash(approved, kind, identity, previous):
    chain = approved.get("_hash_chain", [approved])
    rows = [item.get("hashes", {}).get(kind, {}).get(identity) for item in chain]
    rows = [row for row in rows if row is not None]
    if not rows:
        return previous
    value = previous
    for index, row in enumerate(rows):
        if value == row["before"]:
            value = row["after"]
            continue
        later_values = {item["after"] for item in rows[index:]}
        if value in later_values:
            continue
        raise OCFError("editorial successor previous hash differs: " + kind + "/" + identity)
    return value


def expected_entries(previous, *, resolved=False, root=REPO_ROOT):
    kind = "resolved_entries" if resolved else "raw_entries"
    approved = receipt(root)
    removed = approved.get("_removed_locale_entries", set())
    return {
        key: _expected_hash(approved, kind, key, value)
        for key, value in previous.items()
        if key not in removed
    }


def expected_entry_pairs(previous, root=REPO_ROOT):
    """Advance a full raw/resolved map with one fresh receipt read."""
    approved = receipt(root)
    removed = approved.get("_removed_locale_entries", set())
    return {
        key: {
            "raw_sha256": _expected_hash(approved, "raw_entries", key, value["raw_sha256"]),
            "resolved_sha256": _expected_hash(
                approved, "resolved_entries", key, value["resolved_sha256"]
            ),
        }
        for key, value in previous.items()
        if key not in removed
    }
