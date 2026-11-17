# Editing canonical OCF functions

Each `locales/<locale>/OCF-*.yaml` file is the current source of truth for its
function and locale. Edit that file directly for descriptions, narration,
commands, procedures, lifecycle, safety metadata, and other supported fields.
Git history is the record of earlier versions.

## Supported workflow

1. Edit the canonical YAML resource.
2. Validate the complete locale and command/lifecycle contracts:

   ```bash
   python scripts/ocf.py validate --all
   python scripts/ocf.py locale validate --locale en-US
   ```

3. Regenerate derived indexes, command guides, and audio session-plan
   declarations, then check freshness:

   ```bash
   python scripts/ocf.py build-index
   python scripts/ocf.py audio plan --all --locale en-US
   python scripts/ocf.py build-index --check
   python scripts/ocf.py audio plan --all --locale en-US --check
   ```

No source-text checksum, approval hash, or secondary wording manifest needs a
manual update. Generated fingerprints are deterministic outputs for cache,
recording-compatibility, and freshness checks; they do not override canonical
YAML.

## Existing audio and release boundaries

Changing canonical text does not rewrite a published recording or release
manifest. Existing audio artifacts remain immutable. A regenerated session plan
is a source-derived declaration, not synthesized audio, listening approval, or
release approval. Rendering, listening review, and release packaging remain
separate explicit workflows.

Source-first working blocks are optional when an editor needs source comparison,
rights review, or transcript analysis. They are not an editing gate and do not
replace the canonical YAML. See [per-locale function authority](PER_LOCALE_FUNCTION_AUTHORITY.md),
[audio pipeline](AUDIO_PIPELINE.md), and [source-first authoring](SOURCE_FIRST_AUTHORING.md).
