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

Malformed, unresolved, inactive, ambiguous, undeclared external, or unreviewed
cue references fail validation. Literal braces use `\{` or `\}`; final speech may not
contain unexpanded template markers. Templates cannot evaluate code, access
environment/filesystem/network state, or accept caller-supplied ICU variables.

## Explicit external references

An owned audition resource can cite another function's vocabulary without
changing narration ownership. Use a stable command ID in the text, authorize
the exact token in `allowed`, and declare its owning function in
`external_commands`. An optional external title uses a function ID in the
`function.title.ID` selector and an `external_titles` declaration; bare
`function.title` still refers to the narration owner.

```yaml
entries:
  hplus.function.ocf-exp-007.example:
    status: reviewed
    version: 1.0.0
    cue_template:
      function_id: OCF-EXP-007
      allowed: [function.title.OCF-FND-001, cue.id.OCF-CMD-FND-001-PRIMARY]
      external_titles: [OCF-FND-001]
      external_commands:
        OCF-CMD-FND-001-PRIMARY: OCF-FND-001
    text: |-
      If you have learned {{ function.title.OCF-FND-001 }},
      think or say in your mind, "{{ cue.id.OCF-CMD-FND-001-PRIMARY }}."
```

The example key must also be listed in Energy Ball's narration sequence if
authored there. References are substitutions, not activation, required
learning, imported procedures, or dependencies on a published recording.
Extra declarations fail, as does any owner mismatch or duplicate command
identity. The referenced spoken value must be reviewed and literal. Translated
grammar may change but the declared function and command identities must
not change or disappear. Same-language regional lookup follows the requested
locale, with provenance naming the actual locale used; missing external
speech fails rather than falling back to another language.

A reviewed shared narration entry uses its exact, stable resource key as
`shared_resource` rather than claiming a function as owner. The resource's
file must be declared as shared narration in the locale manifest. This is
independent of the composition's selected function; shared entries never
resolve implicit `cue.primary`, role selectors, or bare `function.title`.
The following example is an independent shared resource, not part of Relax's
own narration sequence.

```yaml
schema_version: '1.0'
locale: en-US
domain: narration
entries:
  hplus.shared.example-brief-relaxation:
    status: reviewed
    version: 1.0.0
    cue_template:
      shared_resource: hplus.shared.example-brief-relaxation
      allowed: [cue.id.OCF-CMD-FND-004-PRIMARY]
      external_commands:
        OCF-CMD-FND-004-PRIMARY: OCF-FND-004
    text: |-
      Think or say in your mind, "{{ cue.id.OCF-CMD-FND-004-PRIMARY }}."
```

Shared `state.access.open` and `state.access.close` are separate state
intentions with their own contract, not application commands. Neither can
be used as an external function cue. Optional stages that do not compose
into the selected session do not introduce spoken reference dependencies.

## Resolution and integrity

`LocaleCatalog.resource` returns effective text plus provenance. Raw template
and resolved-text fingerprints are computed before segmentation, pronunciation,
TTS/cache identity, and recording fingerprints. They are derived runtime/cache
metadata, not source checksums or approval hashes editors maintain. Final
rendering, recording selection, and transcripts reject unresolved tokens.
Cue pronunciation hints follow the selected canonical command; conflicting hints
require an explicit reviewed variant. External provenance records the target
function and command (or title), actual source locale, canonical key, and
source/resolved text fingerprints.

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
