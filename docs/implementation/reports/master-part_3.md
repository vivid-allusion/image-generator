# Part report — phase_3.md

> Per-unit report (PLAN §4.4), written by `/part-close` from actual gate and verifier results — never from memory.

- **Status:** DONE
- **Part:** phase_3.md (M3 — stub-engine engine-boundary pilot)
- **Date:** 2026-10-05T19:18:19Z
- **Repo / branch:** /home/admin/GENERATORS/image-generator · master
- **Commit:** —

## Gate results

| Gate | Exact command | Exit | Result |
|---|---|---|---|
| Unit `## Verification` | `./venv/bin/python -m pytest tests/ -q` | 0 | pass — 97 passed, 1 skipped, 0 failures |
| Resolver `verify=` | `./venv/bin/python -m pytest tests/` | 0 | pass |
| Resolver `lint=` | `./venv/bin/ruff check` | 0 | pass — All checks passed! |
| File-size scan | `wc -l` over changed files | — | breaches: none (`test_preset_reference_media_pilot.py` 162; `test_preset_reference_media.py` 173 unchanged) |

No `src/` change (R3). The Part-3 tests live in the companion
`tests/test_preset_reference_media_pilot.py` (plan §3 M3 permits "a companion
test module") so both test files stay under the soft 250.

## Verifier verdict

`VERDICT: APPROVE` (second pass) — the pinned `verifier` subagent, fresh context, no tools.

- R1 pilot + `--dry-run` + CLI-flag checks: MET.
- R2 manual headless command + the three assertions recorded in the companion docstring: MET (non-blocking).
- R3 no `src/` change: MET.
- Whole-plan AC1/AC2 (Part 1), AC3 (Part 2), AC4 (call site + green gate): MET.
- MUST-FIX: none.

**First pass:** `REJECT` — R1 missing the `--dry-run`/`PreflightExit` assertion
and the "no new CLI flag" check; R2's manual pilot command was not recorded.
Fixed by moving the Part-3 tests to the companion module and adding
`test_dry_run_preflight_exits_without_composing` and
`test_no_new_cli_flag_profile_is_the_only_transport`, and by recording the
manual command in the companion docstring; re-verified APPROVE. No test was
weakened (the pilot's original three assertions are unchanged).

## Evidence per acceptance criterion

- Pilot engine-boundary assertion (`[bullet_ref, preset_one, preset_two]`, `--input_dir` unchanged, payload provenance): `test_cross_repo_pilot_stub_engine_boundary` asserts `recorded["inputs"][0].reference_urls == [BULLET, preset_one, preset_two]`, `sorted(input_dir.iterdir()) == before`, `payload["reference_urls"] == [BULLET]`, `payload["preset_reference_urls"] == [preset_one, preset_two]`, `payload["schema"] == 1`.
- `--dry-run` composes nothing: `test_dry_run_preflight_exits_without_composing` asserts `PreflightExit` and an empty out dir.
- No new CLI flag: `test_no_new_cli_flag_profile_is_the_only_transport` locks `src.cli._ARGUMENTS` to the known flag set and asserts none contains `reference`/`preset`.
- Manual throwaway pilot (R2, recorded): `./venv/bin/python -m src.main_simple --input_dir <throwaway>/in --profile <composed.yaml with reference_images> --output_dir <throwaway>/out --platform stub` — stub engine records the three assertions above; no provider key needed.

## Design

- **Marker:** `**Design:** no — test scaffolding and an engine-boundary assertion; no user-facing surface.` (`tools/design-scope.sh` → `DESIGN=no`).
- **Captures:** not applicable — DESIGN=no.
- **Comparison:** no mock-up.
- **Design verdict:** not run — DESIGN=no (D8).
- **Must-fix:** none.
- **Honest gaps:** none.

## Carried forward

- none

## Next pointer

- `phase`: `phase_4.md` (M4 — propose-only IG doc touch-points)
