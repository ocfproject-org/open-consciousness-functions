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
    combined = deepcopy(data)
    combined["resources"] = extension["resources"]
    combined["added_locale_entries"] = extension.get("added_locale_entries", {})
    combined["hashes"] = deepcopy(data["hashes"])
    for kind, rows in extension["hashes"].items():
        combined["hashes"].setdefault(kind, {}).update(rows)
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
    combined["_hash_chain"] = [data, extension]
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
    return {key: _expected_hash(approved, kind, key, value) for key, value in previous.items()}


def expected_entry_pairs(previous, root=REPO_ROOT):
    """Advance a full raw/resolved map with one fresh receipt read."""
    approved = receipt(root)
    return {
        key: {
            "raw_sha256": _expected_hash(approved, "raw_entries", key, value["raw_sha256"]),
            "resolved_sha256": _expected_hash(
                approved, "resolved_entries", key, value["resolved_sha256"]
            ),
        }
        for key, value in previous.items()
    }
