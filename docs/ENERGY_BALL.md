# Energy Ball and optional preparation

The owner's November 21, 2026 approval authorizes English wording and command
behavior, not a listening edition or release.

- **Energy Ball (`OCF-EXP-007`)**: mentally say **Plus Inflate**
  (`OCF-CMD-EXP-007-PRIMARY`) to establish one ball or reaffirm its current
  extent. Mentally say **Plus Deflate** (`OCF-CMD-EXP-007-DEFLATE`) to draw the
  entire current ball back within. Learned availability remains. Neither cue
  requires a target, special breathing, a movement, or a particular sensation.
- The teaching is part of the locked routine session: its opener and closer
  occur once; the same body occurs twice at Focus Eleven and twice in the
  existing quieter sleep-reinforcement section. It ends deflated. The learning
  binding explicitly excludes routine Energy Ball preparation.
- The routine reminder (`OCF-TPL-STAGE-HPLUS-ENERGY-BALL-003`) is for people
  who already learned it. It leaves the ball established for the next
  exercise, with a reminder of how to draw it back within.
- Resonant Tuning (`OCF-TPL-STAGE-HPLUS-TUNING-003`) is reusable on its own.
  After “Begin now,” the existing bed continues for exactly 30 seconds before
  completion narration, with no added chant or required pitch.

The sole Energy Ball source is `locales/en-US/OCF-EXP-007-Energy-Ball.yaml`.
The two optional stages resolve `locales/en-US/optional-preparation-003.yaml`.
Earlier locked stage resources and existing functions' default plans remain
unchanged. On other sessions, both optional stages are off by default.

## Preview without audio

The Energy Ball binding selects `OCF-PACING-ENERGY-BALL-LEARNING-001` and opts
into Resonant Tuning once, outside the repeated body:

```sh
python scripts/ocf.py audio plan OCF-EXP-007 --locale en-US --expand
```

To omit tuning, put `{"enabled_stages":[]}` in an overrides file and use
`--overrides FILE.json`. To preview a routine that uses both new reusable
stages, create an overrides file such as:

```json
{
  "pacing_profile": "OCF-PACING-OPTIONAL-PREPARATION-001",
  "enabled_stages": ["resonant-tuning", "energy-ball"]
}
```

Run `python scripts/ocf.py audio plan OCF-FND-002 --locale en-US --expand
--overrides FILE.json`. Remove either item from `enabled_stages` to omit
that stage without changing the other. Standalone Preparation Learning accepts
`OCF-PACING-OPTIONAL-PREPARATION-LEARNING-001` in its existing pacing-profile
option, together with an explicit stage selection; no Preparation Learning
wording or default changes.

With the configured Piper backend and model, this command prepares the private
audition plan without synthesizing anything:

```sh
python scripts/ocf.py audio render OCF-EXP-007 --locale en-US \
  --voice OCF-VOICE-0002 --output .ocf-work/energy-ball-audition --dry-run
```

Actual rendering is a separate operation. Existing enabled voice profiles
and local prerequisites still apply; the stock source does not register the
local Mike voice profile.

## Timing and one-time integration review

Exact spoken-text parity passed for the Opener + Body + Closer and both
optional begin + completion pairs after cue resolution and whitespace-only
normalization. Production annotations are not narration tokens. Tuning and
the routine reminder have one annotation each. Each teaching body has 15
ordinary landing annotations and two independent practice annotations, in
order. The final independent hold is part of the measured body before the
existing inter-pass wait, not a replacement for that wait.

The approved tuning interval is 30 seconds. Provisional learning values are
5 seconds per landing (matching the locked relaxation landing) and 15 seconds
per independent practice, with ordinary
sentence/paragraph cadence of 0.4 seconds. The stage uses 1.00× voice
timing. The routine reminder inherits the selected optional-stage practice
value (15 seconds in the example profile); this does not change affirmation
practice. Adjust body pause values through the existing overrides
`pacing.narration_pacing.profiles.energy-ball-body.pauses` mapping. Preserved
repetition gaps are distinct from those pauses.

At 150 words per minute, without running TTS, the event schedule estimates
48:40.2 for learning with tuning, 46:34.8 without tuning, and 28:35.8 for the
routine Focus session with both optional stages. Actual spoken lengths, mix,
and audio duration require later verification; the longer estimate is not used
to cut narration or speed up the session.
