# Part report — phase_1.md

> Per-unit report (PLAN §4.4), written by `/part-close` from actual gate and verifier results — never from memory.

- **Status:** DONE
- **Part:** phase_1.md (M1 — IG `-l`/`--logs` flag + resolved `PipelineContext.logs` gate)
- **Date:** 2026-10-06T10:58:00Z
- **Repo / branch:** /home/admin/GENERATORS/image-generator · master
- **Commit:** —

## Gate results

| Gate | Exact command | Exit | Result |
|---|---|---|---|
| Unit `## Verification` | `./venv/bin/python -m pytest tests/ -q` | 0 | pass — 97 passed, 1 skipped, 0 failures (baseline 97/1) |
| Resolver `verify=` | `./venv/bin/python -m pytest tests/` | 0 | pass |
| Resolver `lint=` | `./venv/bin/ruff check` | 0 | pass — All checks passed! |
| File-size scan | `wc -l` over changed `.py` | — | breaches: `main_simple.py` 362 (soft 250, accepted-divergence entry point, under hard 400), `utils/logging.py` 251, `markdown_parser.py` 255 (both pre-existing soft); none over hard 400 |

Extra behaviour check (beyond the suite): `parse_args()` no-args → `logs False`; `-l` → `True`; `--logs` → `True`; `_logs_enabled` standalone+True→True, standalone+False→False, studiolot+True→**False**, studiolot+False→False.

## Verifier verdict

`VERDICT: APPROVE` — the pinned `verifier` subagent, fresh context, no tools (`ses_eef25cf72ffeua6dFMyeCMd5m3`).

- R1 `-l`/`--logs` added after the `--verbose` block, `store_true`, default off: MET.
- R2 exactly one new field `logs: bool = False` on `PipelineContext`: MET.
- R3 `_logs_enabled` + `_make_pipeline_context` wiring + gated `write_run_logs` + gated `start_output_capture()`: MET.
- R4 `_run_pipeline` gains `logs: bool = True`, passed into the context; no log-content assertion altered: MET.
- Whole-plan AC1/AC2 (in Part 1's scope): MET. AC3's new tests are Part 2 by design; the fixture-only change keeps the suite green: MET.
- MUST-FIX: none.

## Evidence per acceptance criterion

- "src/cli.py registers the -l/--logs store_true flag for the Image Generator and parse_args() leaves it off by default": `src/cli.py` hunk `@@ -44,6 +44,13 @@`; behaviour check no-args → `False`.
- "src/main_simple.py defines _logs_enabled(args, run_mode) returning true only when the flag is set and run_mode is standalone, wires it into PipelineContext.logs through _make_pipeline_context, calls write_run_logs only when ctx.logs is true, and starts output capture only when _logs_enabled is true": `src/main_simple.py` hunks at `_execute_pipeline` (`if ctx.logs:`), the new `_logs_enabled`, `_make_pipeline_context` (`logs=_logs_enabled(args, run_mode)`), and `main` (`if _logs_enabled(args, run_mode): start_output_capture()`).
- "tests/test_logging.py contains the default-off, flag-on, standalone-only, and context-resolution logging tests…": deferred to `phase_2.md` (Part 2) by design; Part 1 gives `_run_pipeline` its `logs` parameter and keeps the suite green (`97 passed, 1 skipped`).
- Plan-defect remediation: two stale W22 pilot assertions updated in `tests/test_preset_reference_media_pilot.py` (exact CLI flag set now includes `-l`/`--logs`; the payload-capture hook sets `logs=True`); recorded in `docs/implementation/questions.md`.

## Design

- **Marker:** `**Design:** no — internal CLI/logging behaviour (flag + gate); no user-facing visual surface.` (resolved by `tools/design-scope.sh`; `DESIGN=no`).
- **Captures:** not applicable — DESIGN=no.
- **Comparison:** no mock-up.
- **Design verdict:** not run — DESIGN=no (D8).
- **Must-fix:** none.
- **Honest gaps:** none.

## Carried forward

- none

## Next pointer

- `phase`: `phase_2.md`
