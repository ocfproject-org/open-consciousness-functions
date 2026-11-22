# Energy Ball and optional preparation

The owner's November 21, 2026 approval authorizes English wording and command
behavior, not a listening edition or release.

- **Energy Ball (`OCF-EXP-007`)**: mentally say **Plus Inflate**
  (`OCF-CMD-EXP-007-PRIMARY`) to establish one ball or reaffirm its current
  extent. Mentally say **Plus Deflate** (`OCF-CMD-EXP-007-DEFLATE`) to draw the
  entire current ball back within. Learned availability remains. Neither cue
  requires a target, special breathing, a movement, or a particular sensation.
- After the opener and body comfort, the order is Transmutation Box, unnumbered
  relaxation, optional Resonant Tuning, Energy Ball, optional main affirmation,
  and one slow count into Focus Ten. The detailed practice and the shorter
  rehearsal each establish and draw the ball back within once, without asking
  the listener to think or say a cue. The independent third practice is no
  longer in the lesson.
- Open Access after those two guided cycles. The Focus Eleven function body
  teaches which mental cue establishes the ball and which draws it back within.
  Hear the same brief cue association twice at Focus Eleven and twice in the
  quieter sleep reinforcement, without another physical or imagined exercise.
  Access closes before the sleep reinforcement. Both waking options count all
  the way from Twenty down to Ten, becoming more awake and alert. Full guidance
  continues from Nine to One. The short option asks the listener to think of
  the number One to return to C1, normal waking consciousness, without invoking
  a separate OCF command. A 30-second quiet interval precedes the closer.
  Both use the same cue-free closer and stereo C1 finish. The ball ends deflated.
- The routine reminder (`OCF-TPL-STAGE-HPLUS-ENERGY-BALL-003`) is for people
  who already learned it. It prompts Plus Inflate without repeating the guided
  sequence and leaves the ball established for the next exercise, with a brief
  Plus Deflate reminder for when the listener chooses to draw it back within.
- Resonant Tuning (`OCF-TPL-STAGE-HPLUS-TUNING-003`) is reusable on its own.
  After “Begin now,” the existing bed continues for two minutes in this lesson
  before completion narration, with no added chant or required pitch. The
  separate routine and Preparation Learning variants still use 30 seconds.

The sole Energy Ball source is `locales/en-US/OCF-EXP-007-Energy-Ball.yaml`.
The two optional stages resolve `locales/en-US/optional-preparation-003.yaml`.
The previous locked templates and rendered audio are unchanged. New shared
plans use this preparation order. In routine sessions, tuning, Energy Ball
and the main affirmation remain opt-in.

## Preview without audio

The Energy Ball binding selects `OCF-PACING-ENERGY-BALL-LEARNING-002` and opts
into Resonant Tuning before the ball practice, outside repeated reinforcement.
Full, unnumbered relaxation is the default:

```sh
python scripts/ocf.py audio plan OCF-EXP-007 --locale en-US --expand
```

Short preparation relaxation opens with **Plus Relax** for listeners who have
already learned the function; it does not count. To select it, put
`{"relaxation":"short"}` in an overrides file. To omit tuning independently, add `"enabled_stages":[]`. Use
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
wording or default changes. On the Energy Ball lesson only, add
`"waking_style":"short"` to use the number-One waking instruction after Ten.

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

The detailed first exercise and shorter rehearsal remove the cue prompts
while retaining 15 five-second landings. Five seconds are reserved after
each exercise. The restructured lesson omits the third practice and its holds;
Git history and the prior private audition preserve that version.

The short option retains the same Focus Ten recognition after the single
count, with a four-second pause after each number. The stand-alone two-minute
tuning interval is separate from its narration and only applies to this lesson.
Normal Access closure and sleep levels are unchanged. Both waking styles
retain the descent through Ten; the shared closer anchors the same C1
fade and 30-second tail after the last measured words.

In Focus Eleven Access, the cue-association wording now starts:

> From now on, whenever you choose to establish your Energy Ball, the cue to
> think is Plus Inflate.
> Whenever you choose to draw the whole ball back within, the cue to think is
> Plus Deflate.

Technical composition checks, proposed narration and a private audition do not
approve public audio or make any claim about physical effects.
