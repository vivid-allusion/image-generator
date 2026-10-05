# Part report — phase_1.md

> Per-unit report (PLAN §4.4), written by `/part-close` from actual gate and verifier results — never from memory.

- **Status:** DONE
- **Part:** phase_1.md (M1 — preset reference media reaches the Engine boundary)
- **Date:** 2026-10-05T19:08:26Z
- **Repo / branch:** /home/admin/GENERATORS/image-generator · master
- **Commit:** —

## Gate results

| Gate | Exact command | Exit | Result |
|---|---|---|---|
| Unit `## Verification` | `./venv/bin/python -m pytest tests/ -q` | 0 | pass — 92 passed, 1 skipped, 0 failures |
| Resolver `verify=` | `./venv/bin/python -m pytest tests/` | 0 | pass |
| Resolver `lint=` | `./venv/bin/ruff check` | 0 | pass — All checks passed! |
| File-size scan | `wc -l` over changed/untracked `.py` | — | breaches: `main_simple.py` 353 (soft 250, accepted-divergence entry point, under hard 400); others: `engine_helpers.py` 183, `profiles.py` 53, new test 124 |

Baseline was 86 passed / 1 skipped; the new file adds 6 passing tests
(0 failures, 0 skips, no test weakened).

## Verifier verdict

`VERDICT: APPROVE` — the pinned `verifier` subagent, fresh context, no tools.

- R1 `preset_reference_urls()` added, validated (`None`→`[]`, non-list/non-string → `ConfigurationError`): MET.
- R2 `build_inputs(..., profile=)` imports and merges `[*md_refs, *preset_refs]`: MET.
- R3 `_execute_pipeline` passes `profile=ctx.profile`: MET.
- R4 new `tests/test_preset_reference_media.py` with tests 1–4 + 7: MET.
- Whole-plan AC1 (accessor behaviour): MET. AC2 (merge order + absent/empty/None): MET.
- AC3 (payload provenance): not in this unit (Part 2). AC4 (call site + green gate): MET.
- MUST-FIX: none.

## Evidence per acceptance criterion

- "preset_reference_urls returns a profile's reference_images list, returns an empty list for an absent or None value, and raises ConfigurationError for a non-list or a list holding a non-string entry.": `src/processing/profiles.py` hunk `@@ -34,3 +34,20 @@`; tests `test_build_inputs_absent_key_is_unchanged`, `test_build_inputs_empty_list_is_unchanged`, `test_build_inputs_malformed_reference_images_raises` (parametrized `"https://x.png"`, `[1, 2]`).
- "build_inputs gives each Engine InputFile the Markdown file's own reference_urls followed by the profile's reference_images, and leaves the Engine's list equal to the Markdown file's own when the key is absent, empty, or None.": `reference_urls=[*b["reference_urls"], *preset_refs]` in `src/engine_helpers.py`; test `test_build_inputs_appends_preset_urls_after_bullet_urls` asserts `[BULLET, *PRESET]`.
- "compose_payload adds the optional preset_reference_urls key only when the preset list is non-empty and keeps the recipe schema equal to 1.": deferred to `phase_2.md` (Part 2); not asserted or implemented here by design.
- "_execute_pipeline passes ctx.profile to build_inputs, and the W22 preset-reference tests pass under the repo gate with zero failures.": `src/main_simple.py` line 95 hunk; test `test_execute_pipeline_passes_profile_to_build_inputs` asserts `seen["profile"] is ctx.profile`; gate `92 passed, 1 skipped`.

## Design

- **Marker:** `**Design:** no — internal Python transport (profile → engine boundary); no user-facing surface.` (`tools/design-scope.sh` → `DESIGN=no`).
- **Captures:** not applicable — DESIGN=no.
- **Comparison:** no mock-up.
- **Design verdict:** not run — DESIGN=no (D8).
- **Must-fix:** none.
- **Honest gaps:** none.

## Carried forward

- none

## Next pointer

- `phase`: `phase_2.md` (M2 — recipe payload provenance)
