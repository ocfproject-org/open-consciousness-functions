"""Strict scoped symbols, locale authority, zero-drift and downstream boundaries."""

from copy import deepcopy

import pytest
from ocf_tools.cue_templates import CueTemplateError, choices, expand, preview, scan
from ocf_tools.locale import LocaleCatalog, LocalePack, NarrationResource, resolve_document
from ocf_tools.models import FunctionRecord


def fixture(
    tmp_path, *, locale="en-US", speech="Plus Example", symbol="cue.primary", role="activation"
):
    command = {
        "id": "OCF-CMD-COG-999-PRIMARY",
        "function_id": "OCF-COG-999",
        "phrase_ref": {"source": "canonical-primary"},
        "role": role,
        "designation": "primary",
        "spoken": "Plus Example",
        "spoken_review": "reviewed",
        "localization": {"spoken_cue_key": "cue.example", "display_cue_key": "cue.display"},
    }
    owner = FunctionRecord(
        "OCF-COG-999",
        "example",
        tmp_path / "function.yaml",
        {
            "canonical": {"name": "Example", "command": {"primary": "PLUS-EXAMPLE", "modes": []}},
            "commands": [command],
            "documentation": {"title_key": "function.example"},
            "narration": {
                "sequence": [{"key": "fixture.body", "role": "function-body", "repetitions": 4}]
            },
        },
    )
    entry = NarrationResource(
        "fixture.body",
        locale,
        "narration",
        "Don't change  whitespace.\nThink {{ " + symbol + " }}.\n",
        status="reviewed",
        version="1.0.0",
        cue_template={"function_id": owner.id, "allowed": [symbol]},
    )
    values = {
        entry.key: entry,
        "cue.example": NarrationResource(
            "cue.example", locale, "narration", speech, status="reviewed", version="1.0.0"
        ),
        "cue.display": NarrationResource(
            "cue.display", locale, "ui", "PLUS-EXAMPLE", status="reviewed"
        ),
        "function.example": NarrationResource(
            "function.example", locale, "ui", "Example", status="reviewed"
        ),
    }
    catalog = LocaleCatalog.from_packs(
        [
            (
                locale,
                LocalePack(
                    {"locale": locale, "status": "canonical" if locale == "en-US" else "reviewed"},
                    values,
                ),
            )
        ]
    )
    catalog._function_records = lambda: [owner]
    return owner, entry, catalog


@pytest.mark.unit
@pytest.mark.parametrize(
    "symbol,role",
    [
        ("cue.primary", "activation"),
        ("cue.mode.increase", "increase"),
        ("cue.mode.decrease", "decrease"),
        ("cue.release", "release"),
        ("cue.cancel", "cancel"),
        ("cue.close", "close"),
        ("cue.retrieval", "retrieval"),
        ("cue.access_close", "access-close"),
        ("cue.id.OCF-CMD-COG-999-PRIMARY", "activation"),
    ],
)
def test_roles_and_ids_insert_complete_cue_without_prose_or_whitespace_drift(
    tmp_path, symbol, role
):
    owner, raw, catalog = fixture(tmp_path, symbol=symbol, role=role)
    entry, resolution = catalog.resource(raw.key, "en-US", domain="narration", fallback=False)
    assert entry.text == "Don't change  whitespace.\nThink Plus Example.\n"
    assert entry.render() == entry.text
    assert entry.raw_template == raw.text
    assert entry.cue_provenance[0]["provenance"]["command_id"] == owner.command_records[0].id
    assert raw.text.endswith("}}.\n")
    assert symbol in choices(owner)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "{{ cue.unknown }}",
        "{{ cue.primary",
        "{{ cue.primary() }}",
        "{{ cue.primary }} }}",
        "{{ env.SECRET }}",
        "{{ cue.primary.__class__ }}",
        "{{ {{ cue.primary }} }}",
        "{{ cue.mode }}",
        "{cue.primary}",
        "{{ cue.primary }} {unapproved}",
    ],
)
def test_unknown_malformed_or_expression_syntax_is_rejected(text):
    with pytest.raises(CueTemplateError):
        scan(text)


@pytest.mark.unit
def test_documented_literal_brace_and_backslash_escapes_are_exact(tmp_path):
    owner, raw, catalog = fixture(tmp_path)
    raw = deepcopy(raw)
    from dataclasses import replace

    raw = replace(raw, text=r"Literal \{brace\}, slash \\, then {{ cue.primary }}.")
    text, _ = expand(raw, "en-US", catalog)
    assert text == r"Literal {brace}, slash \, then Plus Example."
    with pytest.raises(Exception, match="LocaleCatalog first"):
        raw.render()
    with pytest.raises(CueTemplateError, match="caller-supplied ICU"):
        expand(replace(raw, variables=("command",)), "en-US", catalog)


@pytest.mark.unit
def test_locale_cue_pronunciation_and_required_tokens_follow_expansion(tmp_path):
    from dataclasses import replace

    owner, entry, catalog = fixture(tmp_path)
    cue = catalog.canonical.entries["cue.example"]
    catalog.canonical.entries[cue.key] = replace(
        cue, pronunciation={"Example": {"piper": "Example"}}, required_pronunciation=("Example",)
    )
    resolved, _ = catalog.resource(entry.key, "en-US", domain="narration", fallback=False)
    assert resolved.pronunciation == {"Example": {"piper": "Example"}}
    assert resolved.required_pronunciation == ("Example",)
    assert resolved.text == "Don't change  whitespace.\nThink Plus Example.\n"
    catalog.canonical.entries[entry.key] = replace(
        entry, pronunciation={"Example": {"piper": "Conflicting"}}
    )
    with pytest.raises(CueTemplateError, match="conflicting pronunciation"):
        catalog.resource(entry.key, "en-US", domain="narration", fallback=False)


@pytest.mark.unit
def test_newline_and_icu_quote_characters_are_not_reformatted(tmp_path):
    from dataclasses import replace

    owner, entry, catalog = fixture(tmp_path)
    raw = "'Keep doubled apostrophes: '' exactly'\r\n\r\n{{ cue.primary }}.\r\n"
    entry = replace(entry, text=raw)
    catalog.canonical.entries[entry.key] = entry
    resolved, _ = catalog.resource(entry.key, "en-US", domain="narration", fallback=False)
    assert resolved.render().encode() == raw.replace("{{ cue.primary }}", "Plus Example").encode()


@pytest.mark.unit
@pytest.mark.parametrize(
    "change",
    [
        "missing-role",
        "ambiguous",
        "inactive",
        "cross-owner",
        "unauthorized",
        "undeclared",
        "extra-declaration",
        "unknown-owner",
        "missing-cue",
        "unreviewed",
        "conflicting-english",
        "nested",
    ],
)
def test_invalid_identity_authority_and_contracts_fail_closed(tmp_path, change):
    from dataclasses import replace

    owner, entry, catalog = fixture(tmp_path)
    if change == "missing-role":
        entry = replace(
            entry,
            text="{{ cue.release }}",
            cue_template={"function_id": owner.id, "allowed": ["cue.release"]},
        )
    elif change == "ambiguous":
        owner.data["commands"].append(deepcopy(owner.data["commands"][0]))
    elif change == "inactive":
        owner.data["commands"][0]["availability"] = "historical-lookup"
    elif change == "cross-owner":
        entry = replace(
            entry,
            text="{{ cue.id.OCF-CMD-FND-001-PRIMARY }}",
            cue_template={"function_id": owner.id, "allowed": ["cue.id.OCF-CMD-FND-001-PRIMARY"]},
        )
    elif change == "unauthorized":
        owner.data["narration"]["sequence"] = []
    elif change == "undeclared":
        entry = replace(entry, cue_template={"function_id": owner.id, "allowed": []})
    elif change == "extra-declaration":
        entry = replace(
            entry, cue_template={"function_id": owner.id, "allowed": ["cue.primary", "cue.close"]}
        )
    elif change == "unknown-owner":
        catalog._function_records = lambda: []
    elif change == "missing-cue":
        owner.data["commands"][0]["localization"] = {}
        owner.data["commands"][0]["spoken"] = None
    else:
        old = catalog.canonical.entries["cue.example"]
        if change == "unreviewed":
            catalog.canonical.entries[old.key] = replace(old, status="draft")
        elif change == "conflicting-english":
            catalog.canonical.entries[old.key] = replace(old, text="Plus Wrong")
        else:
            owner.data["commands"][0]["spoken"] = "{{ cue.primary }}"
            catalog.canonical.entries[old.key] = replace(old, text="{{ cue.primary }}")
    with pytest.raises(CueTemplateError, match="OCF-COG-999/en-US/fixture.body"):
        expand(entry, "en-US", catalog)


@pytest.mark.unit
@pytest.mark.parametrize("missing", [True, False])
def test_reviewed_locale_copy_cannot_authorize_missing_or_unresolved_english(tmp_path, missing):
    owner, entry, catalog = fixture(tmp_path)
    if missing:
        owner.data["commands"][0].pop("spoken")
        owner.data["commands"][0].pop("spoken_review")
    else:
        owner.data["commands"][0].update(spoken=None, spoken_review="unresolved")
    with pytest.raises(CueTemplateError, match="authoritative|conflicts"):
        expand(entry, "en-US", catalog)


@pytest.mark.unit
def test_display_and_ui_templates_cannot_form_a_recursive_resolution_cycle(tmp_path):
    from dataclasses import replace

    owner, entry, catalog = fixture(tmp_path)
    display = catalog.canonical.entries["cue.display"]
    catalog.canonical.entries[display.key] = replace(
        display, text="{{ cue.primary }}", cue_template=entry.cue_template
    )
    with pytest.raises(CueTemplateError, match="display cue must be literal"):
        expand(entry, "en-US", catalog)
    with pytest.raises(CueTemplateError, match="only for narration"):
        expand(replace(entry, domain="ui"), "en-US", catalog)


@pytest.mark.unit
@pytest.mark.parametrize(
    "locale,speech", [("ja", "見る"), ("ar", "تركيز"), ("es", "Enfocar"), ("zh-Hant", "專注")]
)
def test_locale_complete_realizations_preserve_unicode_and_translator_word_order(
    tmp_path, locale, speech
):
    owner, entry, catalog = fixture(tmp_path, locale=locale, speech=speech)
    from dataclasses import replace

    entry = replace(entry, text="{{ cue.primary }} — Surrounding grammar.")
    assert expand(entry, locale, catalog)[0] == speech + " — Surrounding grammar."


@pytest.mark.unit
def test_variants_require_review_and_same_stable_identity(tmp_path):
    from dataclasses import replace

    owner, entry, catalog = fixture(tmp_path, symbol="cue.primary.variant.object")
    owner.data["commands"][0]["spoken_variants"] = {
        "object": {"text": "the complete cue", "status": "reviewed"}
    }
    assert "cue.primary.variant.object" in choices(owner)
    assert expand(entry, "en-US", catalog)[0].endswith("Think the complete cue.\n")
    owner.data["commands"][0]["spoken_variants"]["object"]["status"] = "unresolved"
    with pytest.raises(CueTemplateError, match="unreviewed"):
        expand(entry, "en-US", catalog)
    owner, entry, catalog = fixture(
        tmp_path, locale="es", speech="Elegir", symbol="cue.primary.variant.object"
    )
    with pytest.raises(CueTemplateError, match="no localized binding"):
        expand(entry, "es", catalog)
    owner.data["commands"][0]["localization"]["spoken_variant_keys"] = {"object": "cue.example"}
    assert "Elegir" in expand(entry, "es", catalog)[0]
    catalog.packs["es"].entries["cue.example"] = replace(
        catalog.packs["es"].entries["cue.example"], status="draft"
    )
    with pytest.raises(CueTemplateError, match="needs review"):
        expand(entry, "es", catalog)


@pytest.mark.unit
def test_title_is_presentation_not_an_activation_and_regional_fallback_is_labeled(tmp_path):
    owner, entry, catalog = fixture(tmp_path, symbol="function.title")
    text, refs = expand(entry, "en-GB", catalog)
    assert text.endswith("Think Example.\n") and refs[0]["provenance"]["locale"] == "en-US"
    from dataclasses import replace

    catalog.canonical.entries["function.example"] = replace(
        catalog.canonical.entries["function.example"], text="Conflicting title"
    )
    with pytest.raises(CueTemplateError, match="title conflicts"):
        expand(entry, "en-US", catalog)
    del owner.data["documentation"]["title_key"]
    with pytest.raises(CueTemplateError, match="missing localized title"):
        expand(entry, "en-US", catalog)


@pytest.mark.unit
def test_translation_keeps_authorized_command_identity_but_may_use_reviewed_variant(tmp_path):
    from dataclasses import replace

    owner, source, catalog = fixture(tmp_path)
    translated = replace(
        source,
        locale="es",
        text="{{ cue.primary.variant.object }} ahora.",
        cue_template={"function_id": owner.id, "allowed": ["cue.primary.variant.object"]},
    )
    owner.data["commands"][0]["localization"]["spoken_variant_keys"] = {"object": "cue.object"}
    catalog.packs["es"] = LocalePack(
        {"locale": "es", "status": "reviewed"},
        {
            translated.key: translated,
            "cue.object": NarrationResource(
                "cue.object", "es", "narration", "Elegir", status="reviewed"
            ),
        },
    )
    assert expand(translated, "es", catalog)[0] == "Elegir ahora."
    cancel = deepcopy(owner.data["commands"][0])
    cancel.update(id="OCF-CMD-COG-999-CANCEL", role="cancel", designation="secondary")
    owner.data["commands"].append(cancel)
    translated = replace(
        translated,
        text="{{ cue.cancel }} ahora.",
        cue_template={"function_id": owner.id, "allowed": ["cue.cancel"]},
    )
    with pytest.raises(CueTemplateError, match="changed the authorized cue identities"):
        expand(translated, "es", catalog)


@pytest.mark.unit
def test_document_expansion_precedes_recording_fingerprints_and_release(tmp_path):
    from ocf_tools.narration_sources import SourceResolver
    from ocf_tools.release import transcript_from_render

    owner, entry, catalog = fixture(tmp_path)
    doc = {"locale": "en-US", "timeline": [{"id": "body", "at": 0, "narration_key": entry.key}]}
    resolved = resolve_document(doc, "en-US", catalog=catalog)
    text = resolved["timeline"][0]["text"]
    assert text.endswith("Think Plus Example.\n")
    assert "raw_template_sha256" in resolved["narration"]["resolved"][0]
    assert transcript_from_render({"narration_timing": {"cues": [{"spoken_text": text}]}}) == text
    for final in ("{{ cue.primary }}", "unfinished }}"):
        with pytest.raises(CueTemplateError):
            SourceResolver({"timeline": [{"id": "bad", "text": final}]}, {})
        with pytest.raises(CueTemplateError):
            transcript_from_render({"narration_timing": {"cues": [{"spoken_text": final}]}})
    from ocf_tools.voice import render_cue_wav

    with pytest.raises(CueTemplateError):
        render_cue_wav({}, "{{ cue.primary }}")


@pytest.mark.integration
def test_all_canonical_resolved_bytes_and_four_passes_match_function_resources():
    from ocf_tools.indexes import load_all_functions
    from ocf_tools.locale import LocaleCatalog
    from ocf_tools.narration_first import plan_narration

    catalog = LocaleCatalog()
    for record in load_all_functions():
        owner = record.id
        view = preview(owner)
        assert not view["synthesis"]
        plan = plan_narration(owner, locale="en-US")
        for row in record.data["narration"]["sequence"]:
            resolved = catalog.resource(row["key"], "en-US", domain="narration", fallback=False)[0]
            repetitions = row["repetitions"]
            for playback in range(1, repetitions + 1):
                pieces = [
                    segment["canonical_text"]
                    for segment in plan["segments"]
                    if segment["resource_key"] == row["key"] and segment["playback"] == playback
                ]
                assert "\n\n".join(pieces).encode() == resolved.text.encode()
        assert all("{{" not in resource["resolved_text"] for resource in view["resources"])


_EXTERNAL_OWNER = "OCF-FND-001"
_EXTERNAL_ID = "OCF-CMD-FND-001-PRIMARY"
_EXTERNAL_SYMBOL = f"cue.id.{_EXTERNAL_ID}"
_EXTERNAL_KEY = "commands.ocf-cmd-fnd-001-primary.spoken-cue"
_EXTERNAL_TITLE_KEY = f"functions.{_EXTERNAL_OWNER.lower()}.title"


def external_fixture(tmp_path):
    from dataclasses import replace

    owner, original, catalog = fixture(tmp_path)
    commanded = deepcopy(owner.data)
    commanded["canonical"].update(
        name="Access to Energy", command={"primary": "PLUS-ENERGIZE", "modes": []}
    )
    commanded["commands"][0].update(
        id=_EXTERNAL_ID,
        function_id=_EXTERNAL_OWNER,
        spoken="Plus Energize",
        localization={"spoken_cue_key": _EXTERNAL_KEY},
    )
    commanded["documentation"]["title_key"] = _EXTERNAL_TITLE_KEY
    commanded["narration"]["sequence"] = []
    remote = FunctionRecord(_EXTERNAL_OWNER, "energy", tmp_path / "energy.yaml", commanded)
    catalog._function_records = lambda: [owner, remote]
    values = catalog.canonical.entries
    values[_EXTERNAL_KEY] = NarrationResource(
        _EXTERNAL_KEY,
        "en-US",
        "narration",
        "Plus Energize",
        status="reviewed",
        file="energy.yaml",
        pronunciation={"Energize": {"piper": "En-er-gize"}},
        required_pronunciation=("Energize",),
    )
    values[_EXTERNAL_TITLE_KEY] = NarrationResource(
        _EXTERNAL_TITLE_KEY, "en-US", "ui", "Access to Energy", status="reviewed"
    )
    entry = replace(
        original,
        text=f"Think {{{{ {_EXTERNAL_SYMBOL} }}}}.",
        cue_template={
            "function_id": owner.id,
            "allowed": [_EXTERNAL_SYMBOL],
            "external_commands": {_EXTERNAL_ID: remote.id},
        },
    )
    values[entry.key] = entry
    return owner, remote, entry, catalog


@pytest.mark.unit
def test_declared_external_cue_and_title_follow_canonical_pronunciation_provenance(tmp_path):
    from dataclasses import replace
    from hashlib import sha256

    owner, remote, entry, catalog = external_fixture(tmp_path)
    title_symbol = f"function.title.{remote.id}"
    contract = deepcopy(entry.cue_template)
    contract["allowed"].append(title_symbol)
    contract["external_titles"] = [remote.id]
    raw = replace(
        entry,
        cue_template=contract,
        text=f"If you know {{{{ {title_symbol} }}}}, think {{{{ {_EXTERNAL_SYMBOL} }}}}.",
    )
    catalog.canonical.entries[entry.key] = raw
    resolved, result = catalog.resource(entry.key, "en-GB", domain="narration", fallback=False)
    assert resolved.text == "If you know Access to Energy, think Plus Energize."
    assert resolved.raw_template == raw.text
    assert result.origin_locale == "en-US"
    assert resolved.pronunciation == {"Energize": {"piper": "En-er-gize"}}
    assert resolved.required_pronunciation == ("Energize",)
    title, cue = [item["provenance"] for item in resolved.cue_provenance]
    assert title["source_key"] == _EXTERNAL_TITLE_KEY
    assert title["source_locale"] == "en-US"
    assert title["function_id"] == cue["function_id"] == remote.id
    assert cue["command_id"] == _EXTERNAL_ID
    assert cue["source_key"] == _EXTERNAL_KEY
    assert cue["source_file"] == "energy.yaml"
    assert cue["source_locale"] == "en-US"
    assert cue["source_sha256"] == cue["resolved_sha256"] == sha256(b"Plus Energize").hexdigest()


@pytest.mark.unit
@pytest.mark.parametrize(
    "scenario,pattern",
    [
        ("undeclared", "active commands"),
        ("extra", "extra or unused"),
        ("duplicate", "ambiguous"),
        ("misowned", "does not belong"),
        ("unknown", "unknown, inactive or ambiguous"),
        ("unknown-owner", "resolves 0 times"),
        ("inactive", "unknown, inactive or ambiguous"),
        ("unreviewed", "requires locale terminology review"),
        ("missing-speech", "missing spoken narration"),
        ("nested", "nested/circular"),
        ("wrong-local-owner", "different function"),
        ("external-title-undeclared", "explicit different owner"),
        ("extra-title", "extra or unused"),
        ("wrong-resource-owner", "not its declared reviewed shared narration owner"),
    ],
)
def test_external_reference_contract_rejects_invalid_provenance(tmp_path, scenario, pattern):
    from dataclasses import replace

    owner, remote, entry, catalog = external_fixture(tmp_path)
    contract = deepcopy(entry.cue_template)
    values = catalog.canonical.entries
    command = remote.data["commands"][0]
    if scenario == "undeclared":
        del contract["external_commands"]
    elif scenario == "extra":
        contract["external_commands"]["OCF-CMD-FND-001-EXTRA"] = remote.id
    elif scenario == "duplicate":
        owner.data["commands"].append(deepcopy(command))
    elif scenario == "misowned":
        command["function_id"] = owner.id
    elif scenario == "unknown":
        command["id"] = "OCF-CMD-FND-001-WRONG"
    elif scenario == "unknown-owner":
        contract["external_commands"][_EXTERNAL_ID] = "OCF-FND-999"
    elif scenario == "inactive":
        command["availability"] = "historical-lookup"
    elif scenario == "unreviewed":
        values[_EXTERNAL_KEY] = replace(values[_EXTERNAL_KEY], status="draft")
    elif scenario == "missing-speech":
        values.pop(_EXTERNAL_KEY)
    elif scenario == "nested":
        command["spoken"] = "{{ cue.primary }}"
        values[_EXTERNAL_KEY] = replace(values[_EXTERNAL_KEY], text=command["spoken"])
    elif scenario == "wrong-local-owner":
        contract["external_commands"][_EXTERNAL_ID] = owner.id
    elif scenario == "external-title-undeclared":
        symbol = f"function.title.{remote.id}"
        contract["allowed"] = [symbol]
        entry = replace(entry, text=f"{{{{ {symbol} }}}}")
    elif scenario == "extra-title":
        contract["external_titles"] = [remote.id]
    elif scenario == "wrong-resource-owner":
        del contract["function_id"]
        contract["shared_resource"] = entry.key
    with pytest.raises(CueTemplateError, match=pattern):
        expand(replace(entry, cue_template=contract), "en-US", catalog)


@pytest.mark.unit
def test_external_regional_speech_translation_identity_and_no_cross_language_fallback(tmp_path):
    from dataclasses import replace

    owner, remote, entry, catalog = external_fixture(tmp_path)
    translated = replace(entry, text=f"{{{{ {_EXTERNAL_SYMBOL} }}}} ahora.", locale="es")
    spanish = {
        entry.key: translated,
        _EXTERNAL_KEY: NarrationResource(
            _EXTERNAL_KEY, "es", "narration", "Dar energía", status="reviewed"
        ),
    }
    catalog.packs["es"] = LocalePack({"locale": "es", "status": "reviewed"}, spanish)
    spanish = catalog.packs["es"].entries
    catalog.packs["es-MX"] = LocalePack(
        {"locale": "es-MX", "status": "reviewed"},
        {
            _EXTERNAL_KEY: replace(
                spanish[_EXTERNAL_KEY],
                locale="es-MX",
                text="Activa tu energía",
                pronunciation={"energía": {"piper": "enerhía"}},
            )
        },
    )
    resolved, lookup = catalog.resource(entry.key, "es-MX", domain="narration", fallback=False)
    assert resolved.text == "Activa tu energía ahora."
    assert lookup.origin_locale == "es"
    assert resolved.cue_provenance[0]["provenance"]["source_locale"] == "es-MX"
    assert resolved.pronunciation == {"energía": {"piper": "enerhía"}}
    from ocf_tools.voice import _pronunciation_hints

    doc = {"timeline": [{"id": "training", "narration_key": entry.key}]}
    localized_doc = resolve_document(doc, "es-MX", catalog=catalog)
    resource = localized_doc["narration"]["resolved"][0]
    assert resource["locale"] == "es" and resource["cue_lookup_locale"] == "es-MX"
    assert _pronunciation_hints(localized_doc, "es-MX", catalog) == {
        "training": {"energía": {"piper": "enerhía"}}
    }
    catalog.packs.pop("es-MX")
    assert catalog.spoken(entry.key, "es-MX") == "Dar energía ahora."
    # Removing reference authorization in translation, even into literal text,
    # is not equivalent to moving the words around a still-authorized reference.
    spanish[entry.key] = replace(translated, text="Dar energía ahora.", cue_template=None)
    with pytest.raises(CueTemplateError, match="omitted authorized external references"):
        catalog.spoken(entry.key, "es")
    spanish[entry.key] = replace(
        translated,
        text="{{ cue.primary }} ahora.",
        cue_template={"function_id": owner.id, "allowed": ["cue.primary"]},
    )
    with pytest.raises(CueTemplateError, match="changed the authorized cue identities"):
        catalog.spoken(entry.key, "es")
    spanish[entry.key] = translated
    spanish.pop(_EXTERNAL_KEY)
    unrelated = NarrationResource(
        "fixture.unrelated", "es", "narration", "Escucha.", status="reviewed"
    )
    spanish[unrelated.key] = unrelated
    from ocf_tools.locale import iter_events
    from ocf_tools.session import compose

    template = {
        "id": "OCF-TPL-SESSION-TEST-001",
        "schema_version": "1.0",
        "sections": [
            {
                "id": "ordinary",
                "start": 0,
                "lines": [{"id": "only", "narration_key": unrelated.key}],
            },
            {
                "id": "optional-training",
                "start": 5,
                "enabled_by": "training",
                "lines": [{"id": "selected", "narration_key": entry.key}],
            },
        ],
    }
    disabled = compose(template, {}, title="Test", locale="es")
    assert [
        event["text"] for event in iter_events(resolve_document(disabled, "es", catalog=catalog))
    ] == ["Escucha."]
    selected = compose(template, {}, title="Test", locale="es", enabled_stages=["training"])
    with pytest.raises(CueTemplateError, match=r"missing spoken narration.*'es'"):
        resolve_document(selected, "es", catalog=catalog)


@pytest.mark.unit
def test_shared_resource_cannot_bind_to_session_host_primary(tmp_path):
    from dataclasses import replace

    owner, remote, entry, catalog = external_fixture(tmp_path)
    filename = "optional.yaml"
    catalog.canonical.manifest["resources"] = [{"file": filename, "domain": "narration"}]
    key = "fixture.shared.relax"
    contract = deepcopy(entry.cue_template)
    del contract["function_id"]
    contract["shared_resource"] = key
    shared = replace(entry, key=key, file=filename, cue_template=contract)
    catalog.canonical.entries[key] = shared
    for host in (owner, remote):
        document = {
            "function_id": host.id,
            "timeline": [{"id": "shared", "narration_key": key}],
        }
        result = resolve_document(document, "en-US", catalog=catalog)
        assert result["timeline"][0]["text"] == "Think Plus Energize."
        provenance = result["narration"]["resolved"][0]["cue_references"][0]["provenance"]
        assert provenance["function_id"] == remote.id
        assert provenance["shared_resource"] == key
    contract["allowed"] = ["cue.primary"]
    del contract["external_commands"]
    with pytest.raises(CueTemplateError, match="shared resource requires a declared explicit"):
        expand(replace(shared, text="{{ cue.primary }}"), "en-US", catalog)


@pytest.mark.unit
def test_external_update_changes_only_affected_speech_and_timing_identity(tmp_path, monkeypatch):
    from dataclasses import replace

    from ocf_tools import speech_cache
    from ocf_tools.narration_sources import text_fingerprint

    owner, remote, entry, catalog = external_fixture(tmp_path)
    monkeypatch.setattr(speech_cache, "voice_identity", lambda spec: {"voice": "test-only"})
    doc = {
        "locale": "en-US",
        "timeline": [
            {"id": "with-reference", "at": 0, "narration_key": entry.key},
            {"id": "unrelated", "at": 10, "text": "Keep listening."},
        ],
    }
    before = resolve_document(doc, "en-US", catalog=catalog)
    remote.data["commands"][0]["spoken"] = "Plus Vitality"
    cue = catalog.canonical.entries[_EXTERNAL_KEY]
    catalog.canonical.entries[_EXTERNAL_KEY] = replace(cue, text="Plus Vitality")
    after = resolve_document(doc, "en-US", catalog=catalog)
    assert before["timeline"][0]["text"] == "Think Plus Energize."
    assert after["timeline"][0]["text"] == "Think Plus Vitality."

    def keys(plan):
        return [
            (
                speech_cache._synthesis_identity({"locale": "en-US"}, event["text"])[1],
                text_fingerprint(event["text"]),
            )
            for event in plan["timeline"]
        ]

    old_keys, new_keys = keys(before), keys(after)
    assert all(old != new for old, new in zip(old_keys[0], new_keys[0], strict=True))
    assert old_keys[1] == new_keys[1]
    old_source = before["narration"]["resolved"][0]
    new_source = after["narration"]["resolved"][0]
    assert old_source["raw_template_sha256"] == new_source["raw_template_sha256"]
    assert old_source["resolved_text_sha256"] != new_source["resolved_text_sha256"]


@pytest.mark.integration
@pytest.mark.parametrize("host", ["OCF-FND-002", "OCF-FND-003"])
def test_composed_short_relax_and_ball_reminder_keep_external_owners(host):
    from ocf_tools.complete_session import build_complete_session_plan

    plan = build_complete_session_plan(
        host,
        locale="en-US",
        overrides={"relaxation": "short", "enabled_stages": ["energy-ball"]},
    )
    document = resolve_document(plan["template_plan"], "en-US", strict=True)
    assert document["function_id"] == host
    refs = {
        (reference["provenance"]["function_id"], reference["provenance"]["command_id"]): (
            reference["text"],
            row["key"],
        )
        for row in document["narration"]["resolved"]
        for reference in row.get("cue_references", ())
        if reference["provenance"].get("shared_resource")
        and "command_id" in reference["provenance"]
    }
    assert refs == {
        ("OCF-FND-004", "OCF-CMD-FND-004-PRIMARY"): (
            "Plus Relax",
            "hplus.shared.settling.brief",
        ),
        ("OCF-EXP-007", "OCF-CMD-EXP-007-PRIMARY"): (
            "Plus Inflate",
            "hplus.optional.energy-ball.v3.begin",
        ),
        ("OCF-EXP-007", "OCF-CMD-EXP-007-DEFLATE"): (
            "Plus Deflate",
            "hplus.optional.energy-ball.v3.complete",
        ),
    }


@pytest.mark.unit
def test_external_reference_schema_and_yaml_duplicate_keys_fail_closed():
    from ocf_tools.utils import yaml_safe_load
    from ocf_tools.validators import _load_schema, validate_against_schema
    from yaml.constructor import ConstructorError

    contract = {
        "shared_resource": "fixture.shared.relax",
        "allowed": [_EXTERNAL_SYMBOL],
        "external_commands": {_EXTERNAL_ID: _EXTERNAL_OWNER},
    }
    row = {
        "schema_version": "1.0",
        "locale": "en-US",
        "domain": "narration",
        "entries": {
            "fixture.shared.relax": {
                "text": f"Think {{{{ {_EXTERNAL_SYMBOL} }}}}.",
                "cue_template": contract,
            }
        },
    }
    schema = _load_schema("locale-resource.schema.json")
    assert not validate_against_schema(row, schema)
    contract["function_id"] = "OCF-COG-999"
    assert validate_against_schema(row, schema)
    del contract["function_id"]
    contract["external_commands"] = {"not-stable": "OCF-999"}
    assert validate_against_schema(row, schema)
    with pytest.raises(ConstructorError, match="duplicate key"):
        yaml_safe_load(
            f"external_commands:\n  {_EXTERNAL_ID}: {_EXTERNAL_OWNER}\n"
            f"  {_EXTERNAL_ID}: OCF-COG-999\n"
        )
