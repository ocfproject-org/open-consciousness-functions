# Energy Ball and optional preparation

The owner's November 21, 2026 approval authorizes English wording and command
behavior, not a listening edition or release.

- **Energy Ball (`OCF-EXP-007`)**: mentally say **Plus Inflate**
  (`OCF-CMD-EXP-007-PRIMARY`) to establish one ball or reaffirm its current
  extent. Mentally say **Plus Deflate** (`OCF-CMD-EXP-007-DEFLATE`) to draw the
  entire current ball back within. Learned availability remains. Neither cue
  requires a target, special breathing, a movement, or a particular sensation.
- The lesson starts with its purpose, body comfort, transmutation box and one
  One-to-Ten relaxation. After Focus Ten recognition and optional tuning, the
  detailed practice and the shorter rehearsal each establish and draw the ball
  back within once. The independent third practice is no longer in the lesson.
- Open Access after those two guided cycles. At Focus Eleven and in the quieter
  sleep reinforcement, hear the same brief cue association twice each, without
  another exercise. Access closes before the sleep reinforcement. The usual
  waking return and single closer remain, and the ball ends deflated.
- The routine reminder (`OCF-TPL-STAGE-HPLUS-ENERGY-BALL-003`) is for people
  who already learned it. It leaves the ball established for the next
  exercise, with a reminder of how to draw it back within.
- Resonant Tuning (`OCF-TPL-STAGE-HPLUS-TUNING-003`) is reusable on its own.
  After “Begin now,” the existing bed continues for two minutes in this lesson
  before completion narration, with no added chant or required pitch. The
  separate routine and Preparation Learning variants still use 30 seconds.

The sole Energy Ball source is `locales/en-US/OCF-EXP-007-Energy-Ball.yaml`.
The two optional stages resolve `locales/en-US/optional-preparation-003.yaml`.
Earlier locked stage resources and existing functions' default plans remain
unchanged. On other sessions, both optional stages are off by default.

## Preview without audio

The Energy Ball binding selects `OCF-PACING-ENERGY-BALL-LEARNING-002` and opts
into Resonant Tuning once at Focus Ten, outside the repeated reinforcement.
The long-form One-to-Ten relaxation is the default:

```sh
python scripts/ocf.py audio plan OCF-EXP-007 --locale en-US --expand
```

To use the concise, slow One-to-Ten count, put `{"relaxation":"short"}` in an
overrides file. To omit tuning independently, add `"enabled_stages":[]`. Use
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

## Timing and audition review

The detailed first exercise and shorter rehearsal preserve the previously
approved wording and 15 five-second landings. Five seconds are reserved after
each exercise. The restructured lesson omits the third practice and its holds;
Git history and the prior private audition preserve that version.

The short option retains the same Focus Ten recognition after the single
count, with a four-second pause after each number. The stand-alone two-minute
tuning interval is separate from its narration and only applies to this lesson.
Normal access closure, sleep levels and waking return are unchanged.

New passive wording for private audition review:

> Plus Inflate is the cue for establishing your Energy Ball.
> Plus Deflate is the cue for drawing the whole ball back within.

Technical composition checks, proposed narration and a private audition do not
approve public audio or make any claim about physical effects.
