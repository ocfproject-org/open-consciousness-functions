# Reviewed common-use examples, 2026-11-18

This import applies the owner's reviewed discovery examples to canonical en-US
`common_uses` only. It is not a narration revision, a clinical-efficacy finding,
or an audio release. Canonical locale YAML remains the sole runtime authority;
no duplicate dataset or alternate registry is introduced.

## Input audit

Dataset identity:
`447b583151bb3b73127f2f19f42d81e787b2bd8d7a15221c2ad6a1f5ea625da6`

- Approved YAML SHA-256:
  `9f1a49fb9604f81d11d76922927751137e97b98e7254a5d9844b7def22d3a305`
- Decision JSON SHA-256:
  `5415e7b46cd3fa0990dcf427251914844bb3bb8d375cb155bb927a2e0350a8da`
- Baseline: `3bcb8c13214d4d934fb1cddfbe360103c7be0778`.
- 277 candidates in 58 functions: 206 approved, 64 rejected, 5 pending, 2 revise.
- 206 additions across 57 functions; no matching drafts required promotion,
  no already-present approved rows, and no conflicts or nonapproved overlaps.
- Clear Zone (`OCF-EXP-005`) is byte-for-byte unchanged.

The input attachments were transferred without changing their bytes (their
uploaded names end in `.yaml.txt` and `.json.txt`); their hashes match the owner's
implementation prompt. Every input row was parsed. Function identities,
semantic-ID uniqueness, decision statuses, exact final wording, reviewed status,
and provenance notes were checked before insertion. The edited Access to Energy
example uses the owner's final wording, without the original word “subjective.”

The import preserves every existing row and status. A second pass found all 206
approved rows already present and made zero changes. All 71 nonapproved
candidates remain excluded from this import. Full parsed resources outside
`common_uses` match the baseline; existing resource text outside the inserted
rows is unchanged. Commands, titles, narration, lifecycle, voice/audio defaults,
release manifests, and historical lookup material are not edited.

These hashes document the supplied editorial artifacts; they are not additional
source authority, an ongoing source-checksum gate, or a substitute for review.
The canonical entries carry their supplied `semantic_id` and provenance `notes`;
Git history records this import. Subsequent editorial changes follow the normal
canonical workflow, not an import replay.

## Public website integration

The existing public-guide exporter projects the canonical values with their
editorial statuses. The existing website renderer displays canonical/reviewed
values and excludes drafts from pages and search. No manual copy of the examples
belongs in the audio repository. The website source pin must advance only to a
verified merged source commit, after reviewing the complete cross-pin delta.
A candidate preview is not a production deployment or approval to change audio.

Regression coverage checks the batch's completeness, the edited example, Clear
Zone exclusion, uniqueness, and exact text/status export. The original input
artifacts and one-shot import receipts remain task evidence, not runtime inputs.
