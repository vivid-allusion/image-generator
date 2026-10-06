# Part 1 — M1: Image Generator `-l`/`--logs` flag + resolved gate (E1–E3)

> Scope: `src/cli.py` (E1), `src/processing/context.py` (E2),
> `src/main_simple.py` (E3), and the `_run_pipeline` fixture update in
> `tests/test_logging.py` that keeps the existing log-content tests green.
> Depends on nothing. This is the **Image Generator half** of W32; the Video
> Generator half (plan §3b/§4b) is a separate cross-repo job.
> Input plan: `docs/implementation/handoffs/W32-run-logging-plan.md` §2, §3a,
> §4a (fixture update), §6 M1.
> Branch: `master`.

**Design:** no — internal CLI/logging behaviour (flag + gate); no user-facing visual surface.

## Goal

A normal Image Generator run writes **no** log file; `-l`/`--logs` in a
**standalone** run writes one as today; a driven (studiolot) run never writes a
log. The gate is a single resolved boolean on `PipelineContext`, computed by one
helper `_logs_enabled()`. Existing log **content** is untouched — the call is
gated, the writer is not rewritten.

## Requirements

### R1 — `src/cli.py`: add the `-l`/`--logs` argument (E1)

Append to `_ARGUMENTS` after the `--verbose` block (the list ends at line 72 at
plan time) and before `--cost-estimation`:

```python
    {
        "flags": ["-l", "--logs"],
        "kwargs": {
            "action": "store_true",
            "help": "Write run logs beside generated files (standalone only; default off)",
        },
    },
```

`store_true` with no explicit default yields `False`. No other CLI change.

### R2 — `src/processing/context.py`: add the resolved gate (E2)

Add **one** field to `PipelineContext` (after `save_payloads`):

```python
    logs: bool = False
```

This is the **resolved** "write logs this run" boolean, not the raw flag — the
single interpretation point is `_logs_enabled()` (R3).

### R3 — `src/main_simple.py`: helper + gate + capture gate (E3)

Add one small helper (near `_make_pipeline_context`):

```python
def _logs_enabled(args: Any, run_mode: str) -> bool:
    """Run logs are opt-in (-l/--logs) and standalone-only."""
    return bool(getattr(args, "logs", False)) and run_mode == "standalone"
```

Then, at plan-time line anchors (re-derive from the tree if W22 shifted them):

- `_make_pipeline_context` (constructor call at `:123–133`) — add:
  ```python
      logs=_logs_enabled(args, run_mode),
  ```
- `_execute_pipeline` — gate the writer at `:106`:
  ```python
      if ctx.logs:
          write_run_logs(generated + placeholders, ctx.output_dir, ctx, payloads, results)
  ```
- `main` — gate capture (replaces `:212`, with `is_studiolot` already computed at
  `:211`):
  ```python
      is_studiolot = bool(args.profile or args.input_dir or args.output_dir)
      run_mode = "studiolot" if is_studiolot else "standalone"
      if _logs_enabled(args, run_mode):
          start_output_capture()
  ```

Do not change `run.py`, `src/utils/logging.py`, profiles, or any engine.

### R4 — `tests/test_logging.py`: keep existing tests green

Existing `TestPerFileLogs` / `TestFallbackWriter` / `TestRealLogReplay` assert
that logs **are** written. With the new gate they must exercise the enabled path
explicitly:

- Extend `_run_pipeline` (`:169–194`): add a `logs: bool = True` parameter and
  pass `logs=logs` into the `PipelineContext` (`:181–191`). `start_output_capture()`
  at `:180` stays (capture writes no file by itself).
- Every existing assertion stays **unchanged** — do not weaken or delete any.
  (`TestFallbackWriter.test_write_run_logs_with_empty_paths` calls
  `write_run_logs` directly and is unaffected.)

## Verification (gate before Part 2)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/python -m pytest tests/ -q      # baseline 97 passed, 1 skipped; ZERO failures after
./venv/bin/ruff check                      # All checks passed!
find src tests -name '*.py' -exec wc -l {} + | sort -n | tail -6
```

Expected: `97 passed, 1 skipped`, zero failures; ruff clean. `main_simple.py`
remains 353 lines (a pre-existing soft breach, under the hard 400 — report, do
not split).

## Files

- `src/cli.py` (E1)
- `src/processing/context.py` (E2)
- `src/main_simple.py` (E3)
- `tests/test_logging.py` (fixture update only)

## Not in this part

- New default-off / flag-on / standalone-only / context-resolution tests — Part 2.
- Video Generator changes — separate cross-repo job.
- Owner-gated author verification + closure/bookkeeping — end-of-build.
