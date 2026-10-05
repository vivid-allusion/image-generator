# W22 — Image Generator consumes a preset's embedded reference media — Shared Plan Context (parts 1–4)

> Read me first, every loop. I do not change between parts.
> Input plan (read-only): `docs/implementation/handoffs/W22-preset-refmedia-plan.md`.
> Workstream: W22 — the Image Generator half of the W95 concat-presets work
> (the W95 plan calls the FC half "W95b"; the W95 closure names it **W209**;
> Video Generator is W98).
> Branch: `master`.

## Goal

The Image Generator consumes an optional top-level `reference_images` list a
TUI-composed profile carries — a preset's embedded reference media — by
appending those URLs, in authored order, **after** each Markdown file's own
`reference_urls`, so they reach the Engine's `InputFile.reference_urls` at the
engine boundary. Provenance is recorded in the image's embedded recipe as an
optional `preset_reference_urls` key. Absent/empty/`None` behaves exactly as
today; malformed input fails loud (`ConfigurationError`). No new CLI flag, no
`USER-FILES/04.INPUT/` writes, no format change.

## Repos & key paths

| What | Path |
|---|---|
| Repo root (the loop's GUARD path) | `/home/admin/GENERATORS/image-generator` |
| Profile loader / new accessor | `src/processing/profiles.py` (`preset_reference_urls`) |
| Input construction (single `InputFile` site) | `src/engine_helpers.py::build_inputs` |
| Pipeline call site | `src/main_simple.py::_execute_pipeline` |
| Recipe payload | `src/processing/payload.py::compose_payload` |
| Shared pipeline state | `src/processing/context.py` (`PipelineContext.profile`) |
| New tests | `tests/test_preset_reference_media.py` |
| Test gate | `./venv/bin/python -m pytest tests/` (baseline **86 passed, 1 skipped, 0 failures**) |
| Lint gate | `./venv/bin/ruff check` |
| Plan / questions / TODO | `docs/implementation/plan/`, `docs/implementation/questions.md`, `TODO.md` |

## Constraints (non-negotiable)

- Python; `pathlib.Path`; type hints; ruff clean; soft 250 / hard 400 lines.
  Touched sizes: `profiles.py` 36→~52, `engine_helpers.py` 173→~180,
  `payload.py` 184→~188, `main_simple.py` unchanged ±1 line.
- Module-per-concern; the shared key accessor has exactly one home
  (`profiles.py`). Never `git add -A`; never commit `venv/` or log artifacts;
  never push.
- Suite gate: **zero new failures** in every part; never weaken an existing
  test.
- Merge order is fixed: `merged = [*md_file.reference_urls, *profile["reference_images"]]`
  (the run's bullets are the subject; the preset's refs are its own
  example/style support). No dedup (a URL in both appears twice — documented).
- Recipe `schema` stays `1`; `preset_reference_urls` is additive and omitted
  when empty. Frozen formats (sidecar / Markdown-file / bullet) untouched.
- Preset refs arrive via the profile and are **not** re-validated by IG at read
  time (reachability stays generation-time, rejected by the engine/provider) —
  the Owner-approved default (parity with the Markdown refs).
- `USER-FILES/` is read-only for this plan (no `04.INPUT/` writes).
- No `video-generator`, no contract/engine repos, no CLI flag.

## Design trigger + evidence rules (W16)

- Each part carries exactly one `**Design:** yes|no — <surface/why>` marker.
  A missing/unmarked unit **engages** the design path (ambiguous is cheap to
  look at).
- This plan has no designed user-facing surface: all four parts are internal
  Python, tests, or a docs proposal, so each marker is `no`. The Manager vets
  the marker at plan review and the **Owner may flip any unit**.
- If (only if) a part is flipped to `yes`: design captures are mandatory, a
  mock-up requires a side-by-side mock-up-vs-actual comparison, and the design
  gate sits before hand-over.

## Part map

| Part | Milestone | Scope | Files |
|---|---|---|---|
| 1 | M1 | E1 `preset_reference_urls()` + E2 `build_inputs` merge + E3 call site | `profiles.py`, `engine_helpers.py`, `main_simple.py`, new test file |
| 2 | M2 | E4 provenance — optional `preset_reference_urls` recipe key | `payload.py`, test file |
| 3 | M3 | Cross-repo pilot: stub-engine engine-boundary proof | test file (test scaffolding only) |
| 4 | M4 | Propose-only IG doc touch-points (Owner-gated) | `questions.md` proposal; no edit applied |

M1 and M2 land in order (M2's key is only meaningful once M1 sends the URLs).
M3 requires the shipped W95 studiolot half and is strengthened by M2. M4 is
proposal-only.

## Whole-plan acceptance criteria

1. `preset_reference_urls` returns a profile's `reference_images` list, returns an empty list for an absent or `None` value, and raises `ConfigurationError` for a non-list or a list holding a non-string entry.
2. `build_inputs` gives each Engine `InputFile` the Markdown file's own `reference_urls` followed by the profile's `reference_images`, and leaves the Engine's list equal to the Markdown file's own when the key is absent, empty, or `None`.
3. `compose_payload` adds the optional `preset_reference_urls` key only when the preset list is non-empty and keeps the recipe `schema` equal to `1`.
4. `_execute_pipeline` passes `ctx.profile` to `build_inputs`, and the W22 preset-reference tests pass under the repo gate with zero failures.

## Close-out (after the LAST part)

Archive the plan dir to `docs/implementation/features/ARCHIVED_<ts>_w22_plan/`
(copy, then delete the working dir), delete `docs/implementation/questions.md`,
blank `TODO.md`, and let the closure land per the W95/W209 closure process.
