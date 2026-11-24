"""Strict, nonrecursive cue interpolation; all locale lookup uses LocaleCatalog.

Only {{ documented.symbol }} is executable syntax. Backslash escapes a single
brace or backslash. Values are complete reviewed cues, never expressions.
"""

from __future__ import annotations

import hashlib
import re

from .commands import cue_presentation, is_active, localized_cue
from .utils import OCFError

ROLES = {
    "cue.mode.increase": "increase",
    "cue.mode.decrease": "decrease",
    "cue.release": "release",
    "cue.cancel": "cancel",
    "cue.close": "close",
    "cue.retrieval": "retrieval",
    "cue.access_close": "access-close",
}
SYMBOL = re.compile(
    r"(?:cue\.(?:primary|mode\.(?:increase|decrease)|release|cancel|close|retrieval|access_close|id\.OCF-CMD-[A-Z0-9-]+)(?:\.variant\.[a-z][a-z0-9_-]*)?|function\.title(?:\.OCF-[A-Z]{3}-[0-9]{3})?|state\.access\.(?:open|close))\Z"
)


class CueTemplateError(OCFError):
    """Semantic template errors must fail even in a labeled fallback audition."""


def scan(text):
    """Return literal/symbol spans with exact code-point offsets; no normalization."""
    result, cursor, literal = [], 0, []
    while cursor < len(text):
        if text[cursor] == "\\" and cursor + 1 < len(text) and text[cursor + 1] in "{}\\":
            literal.append(text[cursor + 1])
            cursor += 2
        elif text.startswith("{{", cursor):
            if literal:
                result.append({"text": "".join(literal)})
                literal = []
            end = text.find("}}", cursor + 2)
            if end < 0:
                raise CueTemplateError(f"unclosed cue reference at offset {cursor}")
            body = text[cursor + 2 : end].strip()
            if not SYMBOL.fullmatch(body):
                raise CueTemplateError(
                    f"unknown or malformed cue reference {body!r} at offset {cursor}"
                )
            result.append({"symbol": body, "start": cursor, "end": end + 2})
            cursor = end + 2
        elif text.startswith("}}", cursor):
            raise CueTemplateError(f"unexpected closing cue delimiter at offset {cursor}")
        elif text[cursor] in "{}":
            raise CueTemplateError(
                f"unescaped literal brace at offset {cursor}; use backslash escaping or a documented double-brace reference"
            )
        else:
            literal.append(text[cursor])
            cursor += 1
    if literal:
        result.append({"text": "".join(literal)})
    return result


def select_command(owner, symbol):
    base = symbol.split(".variant.", 1)[0]
    commands = [command for command in owner.command_records if is_active(command)]
    if base == "cue.primary":
        matches = [command for command in commands if command.designation == "primary"]
    elif base in ROLES:
        matches = [command for command in commands if command.role == ROLES[base]]
    elif base.startswith("cue.id."):
        matches = [command for command in commands if command.id == base.removeprefix("cue.id.")]
    else:
        raise CueTemplateError(f"unsupported cue selector: {base}")
    if len(matches) != 1:
        raise CueTemplateError(
            f"{owner.id}: {base} resolves {len(matches)} active commands; require a unique role or explicit stable ID"
        )
    if matches[0].function_id != owner.id:
        raise CueTemplateError(f"{owner.id}: selected command belongs to a different function")
    return matches[0]


def choices(owner):
    result = ["function.title"]
    for selector in ("cue.primary", *ROLES):
        try:
            select_command(owner, selector)
        except CueTemplateError:
            continue
        result.append(selector)
    result += ["cue.id." + command.id for command in owner.command_records if is_active(command)]
    for selector in list(result):
        if selector == "function.title":
            continue
        command = select_command(owner, selector)
        variants = set(command.data.get("spoken_variants", {})) | set(
            command.localization.get("spoken_variant_keys", {})
        )
        result.extend(selector + ".variant." + name for name in sorted(variants))
    return result


def value(owner, symbol, locale, catalog, *, draft_review=False):
    if symbol == "function.title":
        key = owner.documentation.get("title_key")
        if not key:
            raise CueTemplateError(f"{owner.id}: missing localized title binding")
        entry, resolution = catalog.raw_resource(key, locale, domain="ui", fallback=False)
        if resolution.origin_locale != "en-US" and entry.status not in {"reviewed", "canonical"}:
            raise CueTemplateError(f"{owner.id}: localized title requires review")
        from .localized_authority import metadata as localized_metadata

        localized_owner = localized_metadata(owner, locale, catalog=catalog)
        if localized_owner is not None and entry.text != localized_owner["title"]["text"]:
            raise CueTemplateError(
                f"{owner.id}: title alias conflicts with authoritative localized function YAML"
            )
        if (
            localized_metadata(owner, locale, catalog=catalog) is None
            and resolution.origin_locale == "en-US"
            and entry.text != owner.canonical_name
        ):
            raise CueTemplateError(
                f"{owner.id}: en-US title conflicts with authoritative function YAML"
            )
        return entry.text, {"key": key, "locale": resolution.origin_locale, "function_id": owner.id}
    command = select_command(owner, symbol)
    if (
        draft_review
        and command.data.get("spoken_review") == "reviewed"
        and not command.data.get("spoken")
    ):
        raise CueTemplateError(
            f"{command.id}: reviewed candidate cue requires explicit source wording"
        )
    if draft_review and command.data.get("spoken_review") == "unresolved":
        return draft_cue(owner, command, locale, catalog)
    if ".variant." in symbol:
        variant = symbol.split(".variant.", 1)[1]
        key = command.localization.get("spoken_variant_keys", {}).get(variant)
        if locale == "en-US":
            row = command.data.get("spoken_variants", {}).get(variant, {})
            if row.get("status") != "reviewed" or not row.get("text"):
                raise CueTemplateError(f"{command.id}: unreviewed or missing variant {variant}")
            return row["text"], {"command_id": command.id, "variant": variant, "locale": "en-US"}
        if not key:
            raise CueTemplateError(f"{command.id}: no localized binding for variant {variant}")
        entry, resolution = catalog.raw_resource(key, locale, domain="narration", fallback=False)
        if entry.status not in {"reviewed", "canonical"}:
            raise CueTemplateError(f"{command.id}: localized variant needs review")
        return entry.text, {
            "command_id": command.id,
            "key": key,
            "locale": resolution.origin_locale,
            "variant": variant,
        }
    resolved = localized_cue(owner, command, locale, catalog=catalog, strict=True)
    from .localized_authority import metadata as localized_metadata

    if (
        localized_metadata(owner, locale, catalog=catalog) is None
        and resolved.get("spoken_locale") == "en-US"
        and (not command.data.get("spoken") or command.data.get("spoken_review") != "reviewed")
    ):
        raise CueTemplateError(
            f"{command.id}: symbolic English speech requires authoritative reviewed function-YAML wording"
        )
    if resolved["binding_status"] != "resolved" or not resolved["spoken_cue"]:
        raise CueTemplateError(f"{command.id}: no reviewed spoken cue for {locale}")
    return resolved["spoken_cue"], resolved


def draft_cue(owner, command, locale, catalog):
    """Inspect proposed vocabulary without authorizing production speech."""
    if owner.data.get("audio", {}).get("script_status") != "draft":
        raise CueTemplateError(f"{owner.id}: proposed cues require a draft function")
    key = command.localization.get("spoken_cue_key")
    if not key:
        raise CueTemplateError(f"{command.id}: missing proposed locale cue binding")
    entry, resolution = catalog.raw_resource(key, locale, domain="narration", fallback=False)
    if entry.cue_template is not None or "{" in entry.text or "}" in entry.text:
        raise CueTemplateError(f"{command.id}: proposed cue must be literal")
    if not entry.text.strip() or entry.status != "draft":
        raise CueTemplateError(f"{command.id}: proposed cue must have draft status and text")
    if resolution.origin_locale == "en-US" and entry.text != command.data.get("spoken"):
        raise CueTemplateError(f"{command.id}: proposed cue conflicts with function YAML")
    return entry.text, {
        "command_id": command.id,
        "key": key,
        "locale": resolution.origin_locale,
        "status": "draft",
        "production_authorized": False,
    }


_OWNER_FIELDS = {"function_id", "shared_state", "shared_resource"}
_EXTRA_FIELDS = {"external_commands", "external_titles"}
_FUNCTION_ID = re.compile(r"OCF-[A-Z]{3}-[0-9]{3}\Z")
_COMMAND_ID = re.compile(r"OCF-CMD-[A-Z0-9-]+\Z")
_RESOURCE_ID = re.compile(r"[a-z][a-z0-9-]*(\.[a-z0-9-]+)+\Z")


def has_external_references(contract):
    return bool(contract and (contract.get("external_commands") or contract.get("external_titles")))


def validate_contract(contract):
    """Check the shape also for source readers that do not run JSON Schema."""
    if not isinstance(contract, dict):
        raise CueTemplateError("cue_template must be an object")
    fields = set(contract)
    owners = fields & _OWNER_FIELDS
    if (
        len(owners) != 1
        or "allowed" not in fields
        or fields - _OWNER_FIELDS - _EXTRA_FIELDS - {"allowed"}
    ):
        raise CueTemplateError("cue_template needs exactly one owner and an allowed-symbol list")
    owner_field = next(iter(owners))
    owner_id = contract[owner_field]
    patterns = {
        "function_id": _FUNCTION_ID,
        "shared_resource": _RESOURCE_ID,
        "shared_state": re.compile(r"OCF-SHARED-STATE-CUES-001\Z"),
    }
    if not isinstance(owner_id, str) or not patterns[owner_field].fullmatch(owner_id):
        raise CueTemplateError("cue_template has an invalid owner identifier")
    allowed = contract["allowed"]
    if not isinstance(allowed, list) or not all(isinstance(symbol, str) for symbol in allowed):
        raise CueTemplateError("cue_template requires an allowed-symbol list")
    commands = contract.get("external_commands", {})
    titles = contract.get("external_titles", [])
    if (
        not isinstance(commands, dict)
        or not all(
            isinstance(key, str)
            and _COMMAND_ID.fullmatch(key)
            and isinstance(value, str)
            and _FUNCTION_ID.fullmatch(value)
            for key, value in commands.items()
        )
        or not isinstance(titles, list)
        or not all(isinstance(value, str) and _FUNCTION_ID.fullmatch(value) for value in titles)
        or len(titles) != len(set(titles))
    ):
        raise CueTemplateError("invalid or duplicate external cue/title declarations")
    if owner_field == "shared_state" and fields & _EXTRA_FIELDS:
        raise CueTemplateError("shared-state contracts cannot declare function references")
    return owner_field, owner_id


def _owner(records, owner_id):
    owners = [record for record in records if record.id == owner_id]
    if len(owners) != 1:
        raise CueTemplateError(f"owner {owner_id!r} resolves {len(owners)} times")
    return owners[0]


def _external_command(records, owner_id, command_id):
    owner = _owner(records, owner_id)
    matches = [
        (holder.id, command)
        for holder in records
        for command in holder.command_records
        if command.id == command_id
    ]
    if len(matches) != 1 or not is_active(matches[0][1]):
        raise CueTemplateError(
            f"{command_id}: external command is unknown, inactive or ambiguous; require exactly one active command"
        )
    holder_id, command = matches[0]
    if holder_id != owner_id or command.function_id != owner_id:
        raise CueTemplateError(
            f"{command_id}: external command does not belong to declared owner {owner_id}"
        )
    return owner


def _symbol_targets(contract, owner, records):
    """Bind only declared symbols; compare identities independently of translated variants."""
    commands = contract.get("external_commands", {})
    titles = set(contract.get("external_titles", []))
    used_commands, used_titles, targets = set(), set(), {}
    for symbol in contract["allowed"]:
        if symbol == "function.title" and owner is not None:
            targets[symbol] = (owner, symbol, ("title", owner.id), False)
        elif symbol.startswith("function.title."):
            target_id = symbol.removeprefix("function.title.")
            if target_id not in titles or (owner is not None and target_id == owner.id):
                raise CueTemplateError(
                    f"{symbol}: external title requires an explicit different owner declaration"
                )
            target = _owner(records, target_id)
            used_titles.add(target_id)
            targets[symbol] = (target, "function.title", ("title", target_id), True)
        else:
            base = symbol.split(".variant.", 1)[0]
            command_id = base.removeprefix("cue.id.") if base.startswith("cue.id.") else None
            if command_id in commands:
                target_id = commands[command_id]
                if owner is not None and target_id == owner.id:
                    raise CueTemplateError(
                        f"{symbol}: external command must belong to a different function"
                    )
                target = _external_command(records, target_id, command_id)
                used_commands.add(command_id)
                targets[symbol] = (target, symbol, ("command", target_id, command_id), True)
            elif owner is not None:
                command = select_command(owner, symbol)
                targets[symbol] = (owner, symbol, ("command", owner.id, command.id), False)
            else:
                raise CueTemplateError(
                    f"{symbol}: shared resource requires a declared explicit external ID"
                )
    if used_commands != set(commands) or used_titles != titles:
        raise CueTemplateError("extra or unused external cue/title declarations")
    return targets


def _external_provenance(owner, symbol, text, provenance, catalog):
    domain = "ui" if symbol == "function.title" else "narration"
    locale = provenance.get("spoken_locale", provenance.get("locale"))
    key = provenance.get("spoken_cue_key", provenance.get("key"))
    if key:
        source, _ = catalog.raw_resource(key, locale, domain=domain, fallback=False)
        if source.cue_template is not None or source.variables:
            raise CueTemplateError(f"{key}: external wording must be literal and nonrecursive")
        raw = source.text
        source_file = source.file
    else:
        # An explicit English variant can live solely in authoritative function YAML.
        key = f"commands.{provenance['command_id']}"
        key += (
            f".spoken_variants.{provenance['variant']}.text"
            if "variant" in provenance
            else ".spoken"
        )
        raw = text
        source_file = owner.path.name
    return provenance | {
        "function_id": owner.id,
        "external": True,
        "source_key": key,
        "source_locale": locale,
        "source_file": source_file,
        "source_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "resolved_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def expand(entry, locale, catalog, *, draft_review=False, external_locale=None):
    contract = entry.cue_template
    owner_field, owner_id = validate_contract(contract)
    if owner_field == "shared_state":
        from .shared_state_cues import expand as expand_shared

        return expand_shared(entry, locale, catalog)
    try:
        if draft_review and entry.status != "draft":
            raise CueTemplateError("draft review requires a draft narration resource")
        if entry.domain != "narration":
            raise CueTemplateError("cue templates are authorized only for narration resources")
        if entry.variables:
            raise CueTemplateError("symbolic resources cannot accept caller-supplied ICU variables")
        records = list(catalog.function_records())
        owner = _owner(records, owner_id) if owner_field == "function_id" else None

        def authorized_keys(record):
            return {row["key"] for row in (record.data.get("narration") or {}).get("sequence", [])}

        if owner is not None:
            if entry.key not in authorized_keys(owner):
                raise CueTemplateError(
                    "resource is not an authoritative function narration binding"
                )
        else:
            pack = catalog.get(entry.locale)
            if (
                owner_id != entry.key
                or pack is None
                or not any(
                    row.get("domain") == "narration" and row.get("file") == entry.file
                    for row in pack.manifest.get("resources", [])
                )
                or any(entry.key in authorized_keys(record) for record in records)
                or entry.status not in {"reviewed", "canonical"}
            ):
                raise CueTemplateError(
                    "resource is not its declared reviewed shared narration owner"
                )
        pieces = scan(entry.text)
        used = {piece["symbol"] for piece in pieces if "symbol" in piece}
        allowed = contract["allowed"]
        if len(allowed) != len(set(allowed)) or used != set(allowed):
            raise CueTemplateError(
                f"declared references differ from used references: used={sorted(used)}, declared={allowed}"
            )
        targets = _symbol_targets(contract, owner, records)
        canonical = catalog.canonical
        source = canonical.get(entry.key) if canonical else None
        if source is not None and source.locale != entry.locale:
            source_contract = source.cue_template
            if source_contract is None:
                if any(target[3] for target in targets.values()):
                    raise CueTemplateError(
                        "translation added external references without canonical authorization"
                    )
            else:
                if source_contract.get(owner_field) != owner_id:
                    raise CueTemplateError("translation changed the narration owner")
                source_targets = _symbol_targets(source_contract, owner, records)
                if {item[2] for item in source_targets.values()} != {
                    item[2] for item in targets.values()
                }:
                    raise CueTemplateError(
                        "translation changed the authorized cue identities; grammar variants must retain the same command"
                    )
        elif source is None and any(target[3] for target in targets.values()):
            raise CueTemplateError("external references require a canonical narration source")
        result, references = [], []
        for piece in pieces:
            if "text" in piece:
                result.append(piece["text"])
                continue
            target, selector, _, external = targets[piece["symbol"]]
            text, provenance = value(
                target,
                selector,
                (external_locale or locale) if external else locale,
                catalog,
                draft_review=draft_review and not external,
            )
            if not isinstance(text, str) or not text.strip() or "{" in text or "}" in text:
                raise CueTemplateError(
                    f"{piece['symbol']}: empty/circular/nested cue value is forbidden"
                )
            if external:
                provenance = _external_provenance(target, selector, text, provenance, catalog)
                if owner_field == "shared_resource":
                    provenance["shared_resource"] = owner_id
            result.append(text)
            references.append({**piece, "text": text, "provenance": provenance})
        resolved = "".join(result)
        reject_unexpanded(resolved)
        return resolved, references
    except OCFError as exc:
        raise CueTemplateError(f"{owner_id}/{locale}/{entry.key}: {exc}") from exc


def reject_unexpanded(text):
    if "{{" in text or "}}" in text:
        raise CueTemplateError(
            "unresolved symbolic delimiters in final narration; resolve the resource before synthesis/recording/export"
        )


def preview(function_id, locale="en-US", *, catalog=None, records=None):
    from .indexes import load_all_functions
    from .locale import LocaleCatalog

    records = records if records is not None else load_all_functions()
    catalog = catalog or LocaleCatalog(function_records=lambda: records)
    owner = next((record for record in records if record.id == function_id), None)
    if owner is None:
        raise CueTemplateError(f"unknown function {function_id}")
    resources = []
    for binding in (owner.data.get("narration") or {}).get("sequence", []):
        entry, resolution = catalog.resource(
            binding["key"], locale, domain="narration", fallback=False
        )
        raw = entry.raw_template if entry.raw_template is not None else entry.text
        resources.append(
            {
                **binding,
                "source_template": raw,
                "resolved_text": entry.text,
                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "resolved_sha256": hashlib.sha256(entry.text.encode()).hexdigest(),
                "locale": resolution.origin_locale,
                "references": list(entry.cue_provenance),
            }
        )
    title_key = owner.documentation.get("title_key")
    title_resolution = (
        catalog.lookup(title_key, locale, domain="ui", fallback=True) if title_key else None
    )
    return {
        "function_id": owner.id,
        "source_title": owner.canonical_name,
        "localized_title": catalog.text(title_key, locale) if title_key else owner.canonical_name,
        "title_locale": title_resolution.origin_locale if title_resolution else "canonical-record",
        "cue_presentation": cue_presentation(owner, locale, catalog=catalog),
        "requested_locale": locale,
        "resources": resources,
        "synthesis": False,
    }
