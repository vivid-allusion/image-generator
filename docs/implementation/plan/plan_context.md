# W32 — Generator run-logging (opt-in `-l` / `--logs`) — Image Generator half — Shared Plan Context (parts 1–2)

> Read me first, every loop. I do not change between parts.
> Input plan (read-only): `docs/implementation/handoffs/W32-run-logging-plan.md`.
> Workstream: W32 (queue item `W32-run-logging.md`; was W94 pre-W103). Lead repo
> `~/GENERATORS/image-generator` (alias **image-generator**). This loop carries
> the **Image Generator half** only — see "Cross-repo + end-of-build" below.
> Branch: `master`.

## Goal

A normal Image Generator run leaves **no log file**; a **standalone** run opts
back in with **`-l` / `--logs`**. Concretely: the `-l`/`--logs` flag is added
(`store_true`, default off); the resolved gate `PipelineContext.logs` is computed
once by `_logs_enabled(args, run_mode)` ("flag set **and** standalone"); the file
writer and the in-memory output capture run only when that gate is true; and the
driven (studiolot-mode) path never writes a log even if `-l` is passed. Existing
log **content** is unchanged — we gate the call, not rewrite the writer. No
engine change, no profile/TOML key, no `USER-FILES/04.INPUT/` write.

## Repos & key paths

| What | Path |
|---|---|
| Repo root (the loop's GUARD path) | `/home/admin/GENERATORS/image-generator` |
| CLI argument table | `src/cli.py` (`_ARGUMENTS`) |
| Shared pipeline state (resolved gate) | `src/processing/context.py` (`PipelineContext.logs`) |
| Gate helper + wiring | `src/main_simple.py` (`_logs_enabled`, `_make_pipeline_context`, `_execute_pipeline`, `main`) |
| The file writer (unchanged) | `src/utils/logging.py::write_run_logs` |
| Tests | `tests/test_logging.py` |
| Test gate | `./venv/bin/python -m pytest tests/` (baseline **97 passed, 1 skipped, 0 failures**) |
| Lint gate | `./venv/bin/ruff check` |
| Plan / questions / TODO | `docs/implementation/plan/`, `docs/implementation/questions.md`, `TODO.md` |

## Constraints (non-negotiable)

- Python; `pathlib.Path`; type hints; ruff clean; soft 250 / hard 400 lines.
  Touched sizes at plan time: `cli.py` 83 → ~92, `context.py` 26 → ~27,
  `main_simple.py` **unchanged ±1 line** (353 lines today — a pre-existing soft
  breach, accepted per AGENTS.md's twin table / Owner ruling Q3, and under the
  hard 400), `tests/test_logging.py` 322 → ~380.
- Module-per-concern; the single interpretation point is `_logs_enabled()`. Do
  not scatter flag logic.
- **Never** `git add -A`; never stage `venv/`, `__pycache__/`, or `*.log`; never
  push (the autopush timer publishes per policy).
- Suite gate: **zero new failures** in every part; **never weaken or delete an
  existing test assertion** to go green.
- **Standalone-only is deliberate**: `-l` is honoured in standalone mode only;
  studiolot (driven) mode stays off even with the flag. f-capacitor's
  `build_command` never passes `-l`, so "a driven run leaves no log" is true by
  construction.
- One log per generated file (`<stem>.log` beside the media) plus the single
  timestamped fallback when nothing was generated — unchanged. Console logging
  (`--debug` / `--verbose` / `setup_logging`) is separate and untouched.
- No engine change (`engine-replicate` is untouched; the log writing is 100%
  generator-side); no profile/TOML key; no engine id/package change.
- `USER-FILES/` is read-only for this plan (no `04.INPUT/` writes).

## Design trigger + evidence rules (W16)

- Each part carries exactly one `**Design:** yes|no — <surface/why>` marker. A
  missing/unmarked unit **engages** the design path (ambiguous is cheap to look
  at).
- This plan has no designed user-facing surface: every part is internal Python
  or tests, so each marker is `no`. The Manager vets the marker at plan review
  and the **Owner may flip any unit**.
- If (only if) a part is flipped to `yes`: design captures are mandatory, a
  mock-up requires a side-by-side mock-up-vs-actual comparison, and the design
  gate sits before hand-over.

## Part map

| Part | Milestone | Scope | Files |
|---|---|---|---|
| 1 | M1 | E1 flag + E2 `PipelineContext.logs` + E3 helper/gate/capture gate + `_run_pipeline` fixture update (keeps existing tests green) | `src/cli.py`, `src/processing/context.py`, `src/main_simple.py`, `tests/test_logging.py` |
| 2 | M2 | New logging tests: default-off, flag-on, standalone-only, context resolution (last unit → retires the plan) | `tests/test_logging.py` |

Part 2 depends on Part 1 (it pins Part 1's wiring).

## Whole-plan acceptance criteria

1. `src/cli.py` registers the `-l`/`--logs` `store_true` flag for the Image Generator, and `parse_args()` leaves it off by default.
2. `src/main_simple.py` defines `_logs_enabled(args, run_mode)` returning true only when the flag is set and `run_mode` is `standalone`, wires it into `PipelineContext.logs` through `_make_pipeline_context`, calls `write_run_logs` only when `ctx.logs` is true, and starts output capture only when `_logs_enabled` is true.
3. `tests/test_logging.py` contains the default-off, flag-on, standalone-only, and context-resolution logging tests, and `./venv/bin/python -m pytest tests/` passes with zero failures.

## Cross-repo + end-of-build (not units of this loop)

- **Video Generator half — separate cross-repo job.** The input plan's §3b and
  §4b cover `~/GENERATORS/video-generator` (VG). This loop's root is
  `image-generator`; the loop's commit/verify layer stages files only under
  `<root>` (`/part-close` step 10), so VG edits cannot be committed or verified
  from here. Following the W109 precedent (`handoffs/2026-10-02-job-w109-vg.md`),
  VG is a **separate bounded job** on the `video-generator` alias, with the same
  flag, default, standalone-only guard, and `_logs_enabled` rule. The plan's VG
  baseline is **100 passed, 0 failures**.
- **Owner-gated author verification (M5) — end-of-build.** The real standalone
  runs (`python3 run.py` → no log; `python3 run.py -l` → ≥1 log) and the driven
  run (studiolot argv → no log) spend provider credit and need credentials, so
  they are the Owner's end-of-build action, not a loop unit. Commands are in the
  input plan §5; results are recorded in the closure.
- **Docs/bookkeeping (M6) — end-of-build.** The per-repo `docs/HISTORY.md` note,
  the closure doc at `~/PLATFORM/theia-platform/docs/handoffs/W32-run-logging-closure.md`,
  and the queue `done` are Owner/Manager steps outside this loop's root.
- **Owner verification is an end-of-build step** — this loop has no Owner
  questions and no paid runs.

## Close-out (after the LAST part)

`/part-close` retires the plan on the last clean unit: it deletes
`docs/implementation/plan/` and asserts `test ! -d docs/implementation/plan`.
The per-plan question log `docs/implementation/questions.md` stays (the next
bootstrap blanks it). The W32 closure + queue archive + Owner verification are
the end-of-build steps above.
