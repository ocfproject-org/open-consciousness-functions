# Canonical narration cue references

Each `locales/<tag>/OCF-*.yaml` resource owns that function's exact local cue
wording and narration entries. Its `narration.sequence` declares authorized
resource keys, order, roles, and repetitions. Command controls and lifecycle
semantics are in the same resource. No legacy function YAML, cue preview file,
or replay ledger is loaded as a fallback.

## Strict template contract

An entry may use explicitly approved symbolic references instead of copying a
cue into narration:

```yaml
entries:
  hplus.function.ocf-slp-005.closer:
    status: reviewed
    version: 1.2.1
    cue_template:
      function_id: OCF-SLP-005
      allowed: [cue.primary]
    text: |-
      Think or say in your mind, "{{ cue.primary }}."
```

The key must occur in the owning function's narration sequence. `allowed` must
list exactly the distinct symbols used, with no duplicates. Supported selectors
include `cue.primary`, role-specific mode/release/cancel/close/retrieval cues,
`cue.id.OCF-CMD-…` for an explicit active command owned by the same function,
and `function.title` for localized title text. A reviewed `.variant.NAME` suffix
selects only a declared variant. Labels and explanations are never spoken cue
fallbacks.

Malformed, unresolved, inactive, ambiguous, cross-function, or unreviewed cue
references fail validation. Literal braces use `\{` or `\}`; final speech may not
contain unexpanded template markers. Templates cannot evaluate code, access
environment/filesystem/network state, or accept caller-supplied ICU variables.

## Resolution and integrity

`LocaleCatalog.resource` returns effective text plus provenance. Raw template
and resolved-text fingerprints are computed before segmentation, pronunciation,
TTS/cache identity, and recording fingerprints. They are derived runtime/cache
metadata, not source checksums or approval hashes editors maintain. Final
rendering, recording selection, and transcripts reject unresolved tokens.
Cue pronunciation hints follow the selected canonical command; conflicting hints
require an explicit reviewed variant.

All 59 canonical functions are validated from their current locale YAML for
schema, command/cue consistency, lifecycle structure, entry ownership, and
narration schedule. Git history provides previous wording when a review needs it;
there is no frozen-current-text baseline. Audio defaults lock engineering
profiles, not function wording. Existing recording/release manifests remain
immutable; technical validation is not listening or release approval.

Spanish remains explicitly partial; missing speech is never silently inherited.
Edit the owning locale resource and validate the locale rather than generating
comment banners or copying another locale's narration.

```bash
python scripts/ocf.py functions describe OCF-SLP-005 --rich --json
python scripts/ocf.py narration validate OCF-SLP-005 --locale en-US
python scripts/tools/check_hplus_narration_integrity.py
```
