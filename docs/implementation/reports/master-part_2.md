# Part report — phase_2.md

> Per-unit report (PLAN §4.4), written by `/part-close` from actual gate and verifier results — never from memory.

- **Status:** DONE
- **Part:** phase_2.md (M2 — recipe payload provenance)
- **Date:** 2026-10-05T19:12:28Z
- **Repo / branch:** /home/admin/GENERATORS/image-generator · master
- **Commit:** —

## Gate results

| Gate | Exact command | Exit | Result |
|---|---|---|---|
| Unit `## Verification` | `./venv/bin/python -m pytest tests/ -q` | 0 | pass — 94 passed, 1 skipped, 0 failures |
| Resolver `verify=` | `./venv/bin/python -m pytest tests/` | 0 | pass |
| Resolver `lint=` | `./venv/bin/ruff check` | 0 | pass — All checks passed! |
| File-size scan | `wc -l` over changed files | — | breaches: none (`payload.py` 188, test file 173) |

Part 1 added 6 tests; Part 2 adds 2 → 94 passed / 1 skipped, 0 failures. No
existing test weakened.

## Verifier verdict

`VERDICT: APPROVE` — the pinned `verifier` subagent, fresh context, no tools.

- R1 `compose_payload` import + `preset_refs` + optional key block: MET.
- R2 tests 5–6 (`test_compose_payload_records_preset_reference_urls`, `test_compose_payload_omits_key_when_no_preset_refs`): MET.
- Whole-plan AC1/AC2 (Part 1, still green in the full suite): MET. AC3 (optional key, schema 1): MET. AC4 (call site + green gate): MET.
- MUST-FIX: none.

## Evidence per acceptance criterion

- "compose_payload adds the optional preset_reference_urls key only when the preset list is non-empty and keeps the recipe schema equal to 1.": `src/processing/payload.py` hunk `@@ -74,6 +76,8 @@` adds `if preset_refs: payload["preset_reference_urls"] = preset_refs`; `test_compose_payload_records_preset_reference_urls` asserts `payload["preset_reference_urls"] == PRESET` and `payload["schema"] == 1`; `test_compose_payload_omits_key_when_no_preset_refs` asserts the key is absent and `set(payload) == PRE_W22_KEYS` for both `{}` and `{"reference_images": []}`.
- "_execute_pipeline passes ctx.profile to build_inputs, and the W22 preset-reference tests pass under the repo gate with zero failures.": gate `94 passed, 1 skipped in 1.20s`; `./venv/bin/ruff check` → `All checks passed!`.

## Design

- **Marker:** `**Design:** no — recipe JSON provenance; machine-readable, no user-facing surface.` (`tools/design-scope.sh` → `DESIGN=no`).
- **Captures:** not applicable — DESIGN=no.
- **Comparison:** no mock-up.
- **Design verdict:** not run — DESIGN=no (D8).
- **Must-fix:** none.
- **Honest gaps:** none.

## Carried forward

- none

## Next pointer

- `phase`: `phase_3.md` (M3 — cross-repo stub-engine engine-boundary proof)
