# Source-only editorial batch: 23-function follow-up — 14 November 2026

**State:** draft implementation for independent review; not merged, rendered, released, published, or approved for listening.

**Authority:** the complete owner-supplied local text attachment `OCF_OpenCode_Approved_23_Functions_Prompt.txt`, copied byte-for-byte to `tests/fixtures/approved-editorial-batch-20261114.txt` for offline conformance tests. The copied attachment is 70,115 bytes with SHA-256 `d21984367701da8475e0dd741f3e047e380466339fc869113632afb2d071700b`. No JSON companion was supplied or treated as authority, and no approval-content JSON was invented. The separate `source-only-editorial-successor-23-20261114.json` is a generated hash-only integrity record (predecessor/current digests and the attachment hash); it contains no approved prose and grants no approval. The owner clarification `msg_1db80fb59001fLY2eWTrTs7SMN` resolves the three description conflicts: “Latest directions override previous ones so yes new for all”.

**Source state:** branch `editorial/approved-batch-20261114`, based on merged source main `6b4a9861ab89bea849ef6a97575af9cac6065d9b`, after the pypdf update was merged normally. The earlier source-only nine-function work was reconciled rather than replayed independently. Its source checkpoint evidence and HPLUS-021 lock remain unchanged.

## 23-by-23 parity

Every narration opener, body, and closer is resolved through the canonical primary/secondary cue template architecture and tested against the exact attachment; all schedules remain 1 opener / 4 body passes / 1 closer. All 23 descriptions now match the latest attachment. The owner’s follow-up clarification, “Latest directions override previous ones so yes new for all,” resolves the three formerly conflicting fields.

| Function | Narration | Description |
| --- | --- | --- |
| `OCF-BOD-001` Brain Flow | Exact opener/body/closer | Exact latest approved description |
| `OCF-BOD-006` Heart Flow | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-003` Comfort | Exact opener/body/closer | Exact approved description |
| `OCF-SLP-002` Sleep | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-004` Detox | Exact opener/body/closer | Exact latest approved description |
| `OCF-BOD-002` Circulation | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-007` Blood Pressure Balance | Exact opener/body/closer | Exact approved description |
| `OCF-SLP-001` Restorative Sleep | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-009` Breathe Better | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-008` Immune Readiness | Exact opener/body/closer | Exact latest approved description |
| `OCF-BOD-010` Nutricia | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-011` Hormonal Transitions | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-013` Body Tune-Up | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-014` Regenerate | Exact opener/body/closer | Exact approved description |
| `OCF-BOD-015` Temporary Numbing | Exact opener/body/closer | Exact approved description |
| `OCF-COG-001` Information Access | Exact opener/body/closer | Exact approved description |
| `OCF-COG-002` Mental Calculation | Exact opener/body/closer | Exact approved description |
| `OCF-COG-007` Think Fast | Exact opener/body/closer | Exact approved description |
| `OCF-COM-001` Speak Up | Exact opener/body/closer | Exact approved description |
| `OCF-PRF-003` Coordination | Exact opener/body/closer | Exact approved description |
| `OCF-FND-001` Access to Energy | Exact opener/body/closer | Exact approved description |
| `OCF-AUT-001` Automatic Action | Exact opener/body/closer | Exact approved description |
| `OCF-PRF-001` Do This Now | Exact opener/body/closer | Exact approved description |

## Active procedure and lifecycle scope

- Sleep now uses its own `OCF-PROC-SLEEP-HOLD`: close eyes → inhale → gently hold → silently use Plus Sleep while holding → exhale → continue natural breathing with eyes remaining closed. Its former purpose selection is removed. `OCF-PROC-SLEEP-EXHALE` remains unchanged for every other consumer.
- Nutricia preserves two distinct mode cues. There is no default before a deliberate selection; Food More and Food Less both set the persistent last-selected baseline, which remains across meals/rest/sleep until switched. Switching replaces the previous mode; repeating the selected command is optional reinforcement. Selection is not repeated per meal; no eye steps or automatic per-meal action.
- Comfort retains one selected-area step before inhalation in a function-specific procedure. Regenerate still requires naming a specific part; Body Tune-Up and Restorative Sleep remain whole-body by default with optional area attention. Body Tune-Up closes the eyes before offering optional area selection, and its lifecycle metadata says the whole-body baseline does not require a selected area. Temporary Numbing requires the selected target both for Plus Numb and Plus Release.
- Information Access selects a question before its command and contains no breath sequence. Access to Energy requires a chosen purpose, with no breath or visualization gate; after Plus Energize, its active steps hold the intended result in awareness without requiring a picture. Its separate Plus Release Eleven Access channel-close cue remains byte-for-byte unchanged.
- Eye-opening/closure, mouth exhalation and target rules remain function-specific, including Circulation's closer-only eye opening. No shared procedure behavior was changed for unrelated functions. The candle analogy is absent from all 23 active replacement narrations and their updated procedures.
- Adaptive baselines remain distinct from temporary manual applications for Blood Pressure Balance, Hormonal Transitions, Body Tune-Up, Information Access and Automatic Action. Restorative Sleep's learned capability remains lasting while each sleep application is temporary. Automatic Action continues to require a consciously chosen activity and does not cause involuntary performance.

## Source-only configuration and integrity

An additive immutable source configuration successor `OCF-AUDIO-DEFAULTS-HPLUS-022` captures the 23 canonical resource digests. HPLUS-021 and HPLUS-020 remain byte-for-byte unchanged. Template, pacing and DSP identities/versions are unchanged; `human_listening_approval` remains null and `release_ready` remains false. All 58 source session plans are regenerated solely for exact current resource/default fingerprints. Tests compare the other 35 functions' plan semantics (with only the shared fingerprint normalized) and preserve all 58 binding hashes.

No render, audio export, transcript regeneration, voice/private asset access, source release, merge, publication or deployment occurred. Historical releases and receipts remain unchanged.

## Local validation and full-suite status

- Post-clarification and independent-review focused exact-text, cue interpolation, activation/lifecycle, integrity-chain, command documentation, current-report and unchanged-function/binding regressions: **88 passed**.
- `make check` passed: validate-all has zero errors (nine pre-existing warnings), generated indexes are fresh, all 58 source plans validate, and editorial/docs/cue checks are fresh. `make lint` passed with worktree-local Ruff; optional markdownlint is not installed. Docs inventory: 222 documents, zero broken references.
- HPLUS-022 source lock SHA-256: `05fcb04b428949613122bd50b92c6f6175be5af3dda65a25d0062c26c99e11bf`; hash-only successor record SHA-256: `b5d9189e312689e88ec86cb1079aa268a0a91f6663c4841176fc7e0381143eeb`.
- Local full coverage runs `d412b2316f` and `276f97d67d` terminated near 99% and 97% respectively without valid terminal test summaries. Neither is reported as a pass. Available diagnostics are preserved under the shared `.ocf-work/logs/coverage/` and `.ocf-work/logs/editorial23-test-full*` paths. No kernel journal entry identified a cause; `dmesg` was inaccessible, so the termination cause remains unknown.
- The final unfiltered full suite/coverage gate is delegated to exact-head remote CI for this draft PR; no local full-suite retry is planned.

## Deferred/unreviewed functions (35)

No function content for these identities was changed by this batch; generated all-function indexes/plans only carry the shared current-source fingerprint where applicable.

- `OCF-BOD-005` — Appetite Choice
- `OCF-BOD-012` — Sex Drive
- `OCF-COG-003` — Contemplation
- `OCF-COG-004` — Imprint
- `OCF-COG-005` — Options
- `OCF-COG-006` — Recall
- `OCF-EMG-001` — Injury Response
- `OCF-EMG-002` — Toxic Exposure Response
- `OCF-EMO-001` — Let Go
- `OCF-EMO-002` — Offload
- `OCF-EMO-003` — Empathize
- `OCF-EXP-001` — Manifest
- `OCF-EXP-002` — Insulate
- `OCF-EXP-003` — Dissolve
- `OCF-EXP-005` — Clear Zone
- `OCF-EXP-006` — Intuition
- `OCF-FND-002` — Focus
- `OCF-FND-003` — Quick Recharge
- `OCF-FND-004` — Relax
- `OCF-FND-005` — Reset
- `OCF-FND-006` — Release
- `OCF-LIF-001` — Habit Freedom
- `OCF-PRF-002` — Inner Power
- `OCF-PRF-004` — Light Foot
- `OCF-PRF-005` — Make Your Day
- `OCF-PRF-006` — Strong-Quick
- `OCF-SEN-001` — Hearing
- `OCF-SEN-002` — Seeing
- `OCF-SEN-003` — Smell
- `OCF-SEN-004` — Taste
- `OCF-SEN-005` — Touch
- `OCF-SLP-003` — Dream Theme
- `OCF-SLP-004` — Sleep Insight
- `OCF-SLP-005` — Sleep Easy
- `OCF-SLP-006` — Stay Awake
