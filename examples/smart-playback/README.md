# Private Smart Play audition client

This is the source for the Energy Ball and Quiet Focus review interface.
It is a private preview, not a public playback endpoint or a recording release.
The normal listen/download link continues to use the original Full master.

- The gear opens per-session controls and shows the active guidance preset.
  Defaults are saved only when the listener chooses to save them.
- An audition bookmark seeks to the retained material before a stage and does
  not switch guidance modes.
- Full, Reminder, and Off are shown only where there is measured support.
  Required lesson practices, cue teaching and retained return stages cannot be
  skipped merely by adding a button. An unavailable choice is hidden.
- A selected edit uses one native, seekable audio stream. The serving layer
  needs HTTP byte ranges and should authenticate all manifests and audio.
  Screen-off playback still needs checking on a physical device.

The operator supplies the independently verified `eb-official.json` and its
same-origin media for the two previews. The Full master, inserts, measured
timelines, route index and account settings are not included here. Serve only
a verified, authenticated bundle. Never publish your local review media.

To check the selected audio routes against the private manifest:

```sh
node examples/smart-playback/check-profiles.mjs /path/to/eb-official.json
```
