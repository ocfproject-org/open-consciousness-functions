# Energy Ball and optional preparation

The owner's November 22, 2026 approval covers English wording and command
behavior, not listening approval or a public audio release.

Form a spinning Energy Ball around yourself or a chosen space, fill it with
qualities you choose, and keep it around you or draw it back within.

Recommended learning: Access to Energy, for the optional energizing practice.
That is an optional recommendation, not a prerequisite or a claim that an
official recording is available.

## Use and sequence

- Deliberately think or say in your mind **Plus Inflate**
  (`OCF-CMD-EXP-007-PRIMARY`) to establish the familiar personal ball when
  none is active. Repeating it renews the same active ball at its chosen
  extent and with its chosen qualities; it does not stack a second ball,
  reset an enlarged ball, or enlarge it automatically.
- Deliberately think or say in your mind **Plus Deflate**
  (`OCF-CMD-EXP-007-DEFLATE`) to draw the entire current ball back within,
  including any enlarged extent. This ends only that application; learned
  availability and unrelated functions remain unchanged. Merely hearing or
  reading either cue does not invoke it.
- Ordinary cue use does not require an image, sensation, special breath,
  posture, movement, or eye closure. Size, color, visibility, speed, and
  imagined qualities remain choices. Neither speed nor invisibility is a
  requirement. The guided intentions do not promise physical protection or
  treatment.
- After body comfort, the order is Transmutation Box, unnumbered relaxation,
  Resonant Tuning, both guided practices, optional main affirmation, and one
  count into Focus Ten. The first practice focuses on healing and restoration,
  and the second on protection and balance. Each has a full minute after its
  “Begin now.” The ten-second exercise between them offers withdrawal or
  continued rest. If you withdrew, the second practice restores the ball;
  otherwise it continues with the same ball. These are practice intentions,
  not command modes.
- The guided practices omit the new Inflate and Deflate prompts. Both invite
  people who have learned Access to Energy to choose their intended result,
  mentally use **Plus Energize**, and hold the result in awareness. It is
  entirely optional and does not close the separate Access Channel.
- Open Access teaches the Energy Ball cues with the same short association
  body twice at Focus Eleven and twice during quieter sleep reinforcement.
  Closing Access allows the ball to stay around you. Sleep entry, waking,
  the closer, and playback completion do not deflate it or apply a blanket
  Release. The ball may remain active beyond playback, but its application is
  temporary, not permanent.
- The reusable Energy Ball reminder is for listeners who have already
  learned the practice. It offers a 15-second interval after Plus Inflate
  and a brief voluntary Plus Deflate reminder. It does not repeat the lesson
  or require Energize. The lesson excludes the routine reminder.
- The lesson uses 120 seconds of Resonant Tuning after “Begin now,” followed
  by its completion narration. The standalone and reusable preparation
  versions use 30 seconds. All preserve the existing background without
  a recorded chant or required pitch.

The sole Energy Ball function source is
`locales/en-US/OCF-EXP-007-Energy-Ball.yaml`. The recommendation resolves the
localized title of `OCF-FND-001`, Access to Energy, by stable reference. See
[Symbolic cues](SYMBOLIC_CUES.md) for declaring external command references and
identifying their canonical spoken locales. Shared relaxation and routine
reminders explicitly reference the owners of their cues, never the host
function. Optional stages do not require their spoken references when they are
not selected.

## Preview and render privately

Preview the approved default composition with no synthesis:

```sh
python scripts/ocf.py audio plan OCF-EXP-007 --locale en-US --expand
```

Full unnumbered relaxation is the default. Short relaxation prompts
**Plus Relax** for listeners who have already learned it, plus a settling
fallback for anyone else. It never replaces the later One-to-Ten count.
Select short relaxation and short waking in an overrides file:

```json
{
  "relaxation": "short",
  "waking_style": "short"
}
```

Either choice can be specified independently. The lesson selects Resonant
Tuning unless `"enabled_stages": []` is specified. To include the original
main affirmation after the two practices and before the count, select
`"affirmation": "OCF"` and add `"affirmation"` to the explicitly enabled
stages; retain `"resonant-tuning"` in that list if wanted. Standard routine
sessions leave tuning, Energy Ball and affirmation off unless selected.
A routine such as Focus can explicitly select the reusable 30-second tuning
and Energy Ball reminder:

```json
{
  "pacing_profile": "OCF-PACING-OPTIONAL-PREPARATION-001",
  "enabled_stages": ["resonant-tuning", "energy-ball"]
}
```

Use `--overrides FILE.json` with the expanded preview or private render,
substituting `OCF-FND-002` for the Focus routine. Standalone Preparation
Learning can select the same reusable 30-second tuning using
`OCF-PACING-OPTIONAL-PREPARATION-LEARNING-001` and explicit stage selection.

For complete local auditions, choose a new output directory for each edition.
Set `OCF_REVIEW_VOICE`, `OCF_REVIEW_MIX`, and `OCF_REVIEW_RATE` to the
confirmed local review configuration. Save the short JSON above as
`short-guidance.json`. First run both commands with `--dry-run` and confirm
that the resolved plans use the intended voice, mix, rate, and overrides.
Start actual synthesis only after both plans pass that check:

```sh
python scripts/ocf.py audio render OCF-EXP-007 --locale en-US \
  --voice "$OCF_REVIEW_VOICE" --mix-profile "$OCF_REVIEW_MIX" \
  --rate "$OCF_REVIEW_RATE" --output .ocf-work/energy-ball-full-audition
python scripts/ocf.py audio render OCF-EXP-007 --locale en-US \
  --voice "$OCF_REVIEW_VOICE" --mix-profile "$OCF_REVIEW_MIX" \
  --rate "$OCF_REVIEW_RATE" --overrides short-guidance.json \
  --output .ocf-work/energy-ball-short-audition
```

Use the same confirmed settings for both editions. Neither tuning nor the
two practice intervals is shortened in the short edition. Follow the
[audio pipeline's private edition export procedure](AUDIO_PIPELINE.md)
for lossless FLAC and 320 kbps CBR MP3. Private review credentials, voice
assets, and audition outputs are not included in Git.

## Timing and listening review

The first practice has six five-second pauses before its minute-long
practice. The second has four such pauses before its own minute-long
practice and a further five-second pause after the continuation. Each
60-second interval starts after the measured end of “Begin now.” The
optional withdrawal interval remains ten seconds whether or not the
listener withdraws. Training is never repeated in later passes.

Both waking options retain the descent from Twenty to Ten. Full continues
from Nine to One. Short cues the thought of One for C1, normal waking
consciousness, and gives exactly 30 seconds from the instruction's end to
the closer. The independent 30-second stereo C1 tail follows the final
measured closer words in both editions. The closer mentions availability
without repeating the Inflate or Deflate cues.

See the [private Smart Play audition client](../examples/smart-playback/README.md)
for playback controls. A browser or audio-file check is not a listening
approval. Earlier templates and private editions are preserved.
