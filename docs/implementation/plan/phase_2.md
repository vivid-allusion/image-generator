# Part 2 — M2: Image Generator logging tests (default-off, flag-on, standalone-only, context resolution)

> Scope: `tests/test_logging.py` only — the new W32 tests. Depends on Part 1
> (it pins Part 1's wiring). **This is the LAST unit**: `/part-close` retires the
> plan dir on a clean close.
> Input plan: `docs/implementation/handoffs/W32-run-logging-plan.md` §4a
> (new tests), §6 M2.
> Branch: `master`.

**Design:** no — tests only; no user-facing surface.

## Goal

Pin the W32 behaviour with tests that fail if the gate regresses: the default run
writes no `.log` file, the flag writes one, the flag is honoured in standalone
mode only, and `_make_pipeline_context` resolves `PipelineContext.logs` from
`_logs_enabled()`. Offline and in-process (stub engine; capture is
`StringIO`/`_TerminalCleaner`) — no provider, key, or network.

## Requirements

Extend `tests/test_logging.py` (do not replace it; keep every existing assertion):

### R1 — `test_default_run_writes_no_log`
`_run_pipeline(..., logs=False)`; assert `list(tmp_path.glob("*.log")) == []`,
and the generated media file still exists (e.g. `0-a.png`).

### R2 — `test_logs_flag_writes_log`
`_run_pipeline(..., logs=True)`; assert the log set is `{"0-a.log", "1-b.log"}`
(the existing per-file content path).

### R3 — `TestLogsFlag::test_parse_args_default_logs_off`
Monkeypatch `sys.argv` to `["prog"]`; assert `parse_args().logs is False`.

### R4 — `TestLogsFlag::test_parse_args_l_short_and_long`
`["-l"]` and `["--logs"]` each → `args.logs is True`.

### R5 — `TestLogsFlag::test_logs_enabled_is_standalone_only`
Table over `_logs_enabled(SimpleNamespace(logs=…), run_mode)`:
`standalone`+True → True; `standalone`+False → False; `studiolot`+True →
**False**; `studiolot`+False → False.

### R6 — `test_make_pipeline_context_resolves_logs`
Call `_make_pipeline_context(...)` with `args.logs=True` and
`run_mode="standalone"` → `ctx.logs is True`; with `run_mode="studiolot"` →
`ctx.logs is False` (pins the Part 1 wiring).

Import `_logs_enabled`, `_make_pipeline_context`, and `parse_args` from
`src.main_simple` / `src.cli` as needed.

## Verification (the final gate; runs before the last-unit retire)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/python -m pytest tests/ -q      # baseline 97 passed, 1 skipped + the new tests; ZERO failures
./venv/bin/ruff check                      # All checks passed!
find src tests -name '*.py' -exec wc -l {} + | sort -n | tail -6
```

Expected: **0 failures**; every pre-existing assertion still present; ruff clean.
This part is deterministic and offline (no global logging disable needed).

## Files

- `tests/test_logging.py`

## Not in this part

- `src/` changes — Part 1 (already landed).
- Video Generator changes — separate cross-repo job.
- Owner-gated author verification + closure/bookkeeping — end-of-build.

## Carried forward / close

This is the last unit. On a clean close (`/part-close` step 7) delete
`docs/implementation/plan/` and assert `test ! -d docs/implementation/plan`. If a
`[ ]`/`[!]` item or a verifier REJECT remains, this unit is NOT done and the
pointer does not advance.
