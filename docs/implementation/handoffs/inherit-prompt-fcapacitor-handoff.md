# inherit_prompt — the f-capacitor half (handoff seed)

> **Status:** brief only — no code. Written 2026-10-17 from the image-generator
> side (m70q) for a workstream in the f-capacitor repo, which owns the driven
> path. This note is the seed for that workstream's plan; give it a W number
> there if the loop system asks.
>
> **Read first:** the image-generator side is complete and pushed
> (`origin/master`, repo now named `vivid-allusion/image-generator`).

## What already landed in image-generator (the IG side)

- **Profile key `inherit_prompt`** (top-level, default `false`): when on, a
  run's *first* reference image is fetched before generation, its embedded
  recipe read back, and the source's prompt (text, prefix, suffix) becomes the
  new file's prompt of record. This run's endpoint, parameters and timestamps
  stay truthful; the run's own wording is kept in the recipe as `instruction`
  and the source image (URL, generation date, endpoint) as `inherited_from`.
  Recipe `schema` stays `1` — additive keys only.
- **Fallbacks:** an unusable first reference (fetch failure, foreign image,
  error placeholder, recipe without prompt text) warns and falls back to the
  run's own prompt; a file without references is a no-op. Batches never stop
  for inheritance.
- **CLI note:** `--inherit-prompt` / `--no-inherit-prompt` exist for
  standalone runs only. The driven path needs **no argv change** — f-capacitor
  composes profiles, and its `build_command` never passes new flags
  (W32 finding).
- **Parser, same release:** Markdown prompts may be a fenced block (```` ```prompt ````
  or a bare ```` ``` ````; multi-line; may be empty) and an empty prompt is
  admitted when the profile carries `prompt_prefix`/`prompt_suffix`. This makes
  the pre-upscale style files (“empty fence + one reference”) run with the
  prefix as the whole instruction, references intact.

## What f-capacitor needs to do (mirrors the W95/W22 `reference_images` flow)

1. **Preset schema:** an optional boolean on the prompt preset — “keep the
   source image's own prompt (edits/upscales)”.
2. **Wizard / preset editor:** surface that toggle where the preset's other
   knobs live (`hc/presets.py` territory).
3. **Profile composition:** `hc/profiles.py::compose_profile` must emit
   `inherit_prompt: true` explicitly when the preset carries it (same pattern
   as `reference_images`). Check whether composed profiles are validated
   against a closed key list — add the key if so.
4. **Nothing else:** no argv changes, no generator version gate required for a
   first cut. (If you *want* a support check, the recipe's `generator.version`
   and the new payload keys are the places to look, but the key is simply
   ignored by older generators — absent/off is the byte-identical path.)

## Awareness items (verify, likely no change)

- **Anything that shows a job's prompt** (TUI captions, sidecars) will now show
  the *source's original* prompt for inherited runs — intended. `instruction`
  holds the run's own wording if a UI ever wants it.
- **Theia IDE:** the XMP packet structure is untouched (only the
  dc:description content changes; cull-mark merging unchanged), so no TS-side
  change is expected. Worth one confirmation that nothing validates recipe
  fields strictly.
- **Video Generator parity:** its parser already accepts fenced prompts;
  `inherit_prompt` is IG-only today. Decide separately whether VG should
  inherit too.

## Verification expected in f-capacitor

- A preset without the toggle composes exactly as today (no new key).
- A preset with the toggle composes a profile carrying `inherit_prompt: true`.
- A driven run with such a profile (first reference = one of our generated
  images) stamps the source's prompt on the output and records
  `inherited_from`; without the toggle nothing changes.
