# W32 — Generator run-logging — opt-in `-l` / `--logs` — plan

> **Workstream:** W32 (queue item `W32-run-logging.md`; was W94 in the pre-W103
> queue). **Lead repo:** `~/GENERATORS/image-generator` (alias
> **image-generator**); **cross-repo:** `~/GENERATORS/video-generator` (VG).
> **Closure (when built):**
> `~/PLATFORM/theia-platform/docs/handoffs/W32-run-logging-closure.md`.
> **Status of this doc:** uncommitted in the tree for the Manager to collect +
> verify; the Owner reviews before any build. **Planning only — no code.**
>
> **Read first / inputs used (paths resolved to today's names):**
> - `~/GENERATORS/image-generator/AGENTS.md` and
>   `~/GENERATORS/video-generator/AGENTS.md`.
> - `~/INFRA/loops-and-goals-mgmt/queue/items/W32-run-logging.md` (authoritative
>   brief) and `~/INFRA/loops-and-goals-mgmt/handoffs/m70q-manager-W32.md`.
> - `image-generator/run.py`, `image-generator/src/**`, `image-generator/ARCHITECTURE.md`;
>   the same for `video-generator`.
> - `~/ENGINES/engine-replicate/engine_replicate/engine.py`.
> - The tree at plan time: IG `master` @ `bf89c97` (W22 retired; tree quiet apart
>   from an untracked `.opencode/`); VG `master` @ `5d9d8fb`.
> - **W103 timing note:** the brief anticipated that W103 (the namechange) would
>   land after this work. W103 has since landed (closure dated 2026-09-30), so
>   this plan references the **current** tree names throughout —
>   `~/GENERATORS/*`, `engine-replicate` / `engine_replicate`,
>   `generator`/`Generator` vocabulary. No pre-W103 name appears.

## 0. Baseline and stop-condition checks (all cleared)

- **Baseline test gate, re-run on the clean tree at plan time (2026-10-06):**
  - IG: `./venv/bin/python -m pytest tests/ -q` → **97 passed, 1 skipped, 0 failed**.
  - VG: `./venv/bin/python -m pytest tests/ -q` → **100 passed, 0 failed**.
  - The plan gate is therefore "zero new failures", not a pre-existing count.
- **Stop condition — engine is required to remove the default log:** **does not
  trigger.** The log writing lives entirely in the two **generators**; the
  replicate engine writes none (§1). No engine change is needed at all.
- **Stop condition — a test needs logging globally disabled to be
  deterministic:** **does not trigger.** The gate is an ordinary boolean on the
  orchestration path; a stub engine and an in-memory capture make tests
  deterministic with real code (§4).
- **Stop condition — the two generators disagree in a way the Owner must
  choose:** **does not trigger.** Both generators already share the same shape
  (unconditional `write_run_logs(...)` called from one `_execute_pipeline`);
  the plan gives them the **same** flag, the **same** default, and the **same**
  standalone-only guard (§2–§3). Their implementations differ (IG threads a
  `PipelineContext`; VG threads parameters) but the behaviour does not.
- **Not in scope:** any engine (including `engine-replicate`), the TUI
  (`f-capacitor`), profiles/TOML keys, engine ids/packages, the f-capacitor
  job-level logs (`~/.config/.../jobs/<id>.log`), `USER-FILES/04.INPUT/`.

---

## 1. Where the logs come from — every site, generator vs engine

**Verdict: the log files are created 100% generator-side. `engine-replicate`
writes no log file.** Both generators call one writer from one place on every
run, with no flag gate. The writer is the only code that opens a `.log` for
writing.

### 1a. Image Generator (IG)

| Site | Function | What it does |
|---|---|---|
| `src/main_simple.py:106` | `_execute_pipeline` | **Unconditional** `write_run_logs(generated + placeholders, ctx.output_dir, ctx, payloads, results)` — runs in **both** modes (`_run_standalone` and `_run_studiolot` both funnel here). This is the defect's call site. |
| `src/main_simple.py:212` | `main` | `start_output_capture()` — unconditional. In-memory only (tees stdout/stderr into a cleaner); **writes no file by itself**, but it is the capture the writer consumes. |
| `src/utils/logging.py:154–180` | `write_run_logs` | **The file writer.** For each generated path, writes `gen_path.with_suffix(".log")` (`:172`, write at `:173`). Fallback when nothing was generated: `output_dir / f"image_generator_{ts}.log"` (`:177`, write at `:178`). |
| `src/utils/logging.py:118–138` | `setup_logging` | `logger.add(sys.stderr, ...)` (`:131`) — **console only**, no file sink. loguru's default sink is removed at `:123`. No file. |
| `run.py` (whole file) | bootstrap | venv/install + `subprocess.run([..., "-m", "src.main_simple"] + sys.argv[1:])` — **writes no log**. |

### 1b. Video Generator (VG)

| Site | Function | What it does |
|---|---|---|
| `src/main_verbose.py:182` | `_execute_pipeline` | **Unconditional** `write_run_logs(generated, output_dir)` — runs in both modes (`_run_studiolot`, `_run_standalone`). The defect's call site. |
| `src/main_verbose.py:209` | `main` | `start_output_capture()` — unconditional; in-memory only. |
| `src/main_verbose.py:165–167` | `on_progress` closure | `log_file_only(f"Payload: {payload}")` — appends to an in-memory list; **no file** unless `write_run_logs` runs. |
| `src/utils/logging.py:94–112` | `write_run_logs` | **The file writer.** `gen_path.with_suffix(".log")` (`:104`, write at `:105`); fallback `output_dir / f"video_generator_{ts}.log"` (`:110`, write at `:111`). |
| `src/utils/logging.py:62–74` | `setup_logging` | `logger.add(sys.stderr, ...)` (`:67`) — console only. No file. |
| `run.py` (whole file) | bootstrap | launches `-m src.main_verbose`; **writes no log**. |

### 1c. Engine — `engine-replicate`

`~/ENGINES/engine-replicate/engine_replicate/engine.py` contains **no log-file
write**. The only file writes are the generated **media**:
`urllib.request.urlretrieve(item, dest)` (`:460`) and `open(dest, "wb")`
(`:475`). Progress is surfaced as `ProgressEvent`s via `_emit` (`:526–545`);
the generator turns those into console output. A repo-wide scan for
`.log`/`FileHandler`/`logger.add` found only a test writing fixture content
(`tests/test_schema_sync.py:84`), not production logging.

**Therefore: engine change = none.** `engine-replicate` is not touched, and no
other engine is touched.

### 1d. Downstream consumers of the generator `.log` files (risk cleared)

- `f-capacitor` sync treats a generator artifact as "media + run log, not a
  `.md`" — the sync sidecar path only concerns `.md` sidecars and media
  (`~/MISC/f-capacitor/docs/implementation/handoffs/W99-sync-sidecar-plan.md:152–156`).
  No module globs or reads the generator's `<stem>.log`.
- f-capacitor's own `*.log` (job logs under `CONFIG/jobs/`, `studiolot.log`,
  `audit.log`) are a **separate** system and are unaffected.
- Both repos' `.gitignore` already ignore `*.log`; log artifacts are never
  committed regardless.

---

## 2. Flag design

**The flag:** `-l` / `--logs`, `argparse` `action="store_true"`, **default off**.
The same flag, spelling, and default in both generators.

**Behaviour (chosen):**

- **Default (no flag): no log file is written, in either mode.** The file writer
  is not called; the in-memory capture is not started. The console output is
  unchanged.
- **Standalone + `-l`/`--logs`: logs are written**, with exactly today's
  semantics (one `.log` per generated file, plus the single timestamped fallback
  when nothing was generated).
- **Driven run (studiolot mode) with or without `-l`: no log file.** The flag is
  **honoured in standalone mode only**; in studiolot mode logging stays off even
  if `-l` is present.

**Why standalone-only (deliberate guard, not a limitation):** the Owner's words
are "block … making log files on run. But it should be possible when running them
**standalone** with a flag". The driven path is f-capacitor, whose
`hc/generator.py:125–137` `build_command()` passes only
`--input_dir/--output_dir/--profile/--platform` and never `-l`; the guard makes
"a driven run leaves no log" true by construction, not by the TUI happening not
to pass the flag. It also gives a single rule to test and verify. The alternative
(honour `-l` in both modes) was rejected: it would make the "driven leaves no
log" verification conditional on the caller's argv rather than on intent.

**One-per-run vs append:** unchanged. Keep the existing **one log per generated
file** (`<stem>.log` beside the file) and the **single timestamped fallback** for
runs that generated nothing. We are gating the call, not rewriting the writer.

**Path / name (unchanged):**

- Per generated file: sibling file beside the media, `.with_suffix(".log")` —
  e.g. `260831_110206-1_rw-0.log` (IG reference, `tests/test_logging.py:25`).
- Fallback (nothing generated): IG `output_dir / image_generator_<YYMMDD_HHMMSS>.log`
  (`src/utils/logging.py:177`); VG `output_dir / video_generator_<YYYY-MM-DD_HH-MM-SS>.log`
  (`src/utils/logging.py:110`).

**Capture gating:** `start_output_capture()` is called only when logging is
enabled. Capture exists solely to feed `write_run_logs`; with logging off the
tee is pointless overhead. `write_run_logs` is already resilient to a missing
capture (`captured_output()` returns `""`), so a direct caller that enables logs
without starting capture cannot crash.

**Console logging is untouched:** `--debug`/`--verbose`/`setup_logging` are
separate from `--logs`; `-l` changes only whether a log **file** is written.

---

## 3. Change list (per repo, exact edits)

### 3a. `~/GENERATORS/image-generator`

**E1 — `src/cli.py` (add flag).** In `_ARGUMENTS`, after the `--verbose` block
(ends `:46`):

```python
    {
        "flags": ["-l", "--logs"],
        "kwargs": {
            "action": "store_true",
            "help": "Write run logs beside generated files (standalone only; default off)",
        },
    },
```

**E2 — `src/processing/context.py` (add the resolved gate to the shared context).**
Add a field to `PipelineContext` (this dataclass already documents the "log
stage", `:12–16`):

```python
    save_payloads: bool = True
    logs: bool = False
    run_mode: str = "standalone"
```

The field is a **resolved** boolean ("write logs this run"), not the raw flag —
the single interpretation point is `_logs_enabled()` (E3).

**E3 — `src/main_simple.py`.**
Add one small helper (mirrors the "single interpretation point" pattern used
elsewhere in these repos):

```python
def _logs_enabled(args: Any, run_mode: str) -> bool:
    """Run logs are opt-in (-l/--logs) and standalone-only."""
    return bool(getattr(args, "logs", False)) and run_mode == "standalone"
```

- In `_make_pipeline_context` (`:112–133`), add to the constructor call:
  `logs=_logs_enabled(args, run_mode),`.
- In `_execute_pipeline` (`:93–109`), gate the writer at `:106`:
  ```python
      if ctx.logs:
          write_run_logs(generated + placeholders, ctx.output_dir, ctx, payloads, results)
  ```
- In `main` (`:209–213`), gate capture (replace `:212`):
  ```python
      run_mode = "studiolot" if is_studiolot else "standalone"
      if _logs_enabled(args, run_mode):
          start_output_capture()
  ```
  (`is_studiolot` is already computed at `:211`.)

No change to `run.py`, `src/utils/logging.py`, profiles, or any engine.

### 3b. `~/GENERATORS/video-generator`

**E1 — `src/cli.py` (add flag).** Same argument spec as IG, added after the
`--verbose` block (ends `:37`).

**E2 — `src/main_verbose.py`.**
Add the same helper (VG has no `PipelineContext`; it threads parameters):

```python
def _logs_enabled(args: Any, run_mode: str) -> bool:
    """Run logs are opt-in (-l/--logs) and standalone-only."""
    return bool(getattr(args, "logs", False)) and run_mode == "standalone"
```

- `_execute_pipeline` (`:127–134`): add `logs: bool = False` to the signature
  (after `input_root`).
- `on_progress` (`:165–167`): guard the file-only record —
  ```python
              if logs and payload is not None:
                  log_file_only(f"Payload: {payload}")
  ```
- `:182`: gate the writer —
  ```python
      if logs:
          write_run_logs(generated, output_dir)
  ```
- `main` (`:206–210`): gate capture (replace `:209`):
  ```python
      run_mode = "studiolot" if is_studiolot else "standalone"
      if _logs_enabled(args, run_mode):
          start_output_capture()
  ```
- `_run_studiolot` call site (`:275`): `_execute_pipeline(..., input_dir, logs=False)`.
- `_run_standalone` call site (`:345`): `_execute_pipeline(..., input_path, logs=_logs_enabled(args, "standalone"))`.

No change to `run.py`, `src/utils/logging.py`, profiles, or any engine.

### 3c. `~/ENGINES/engine-replicate`

**No change.** (Evidence §1c.) The boundary "do not touch any engine other than
`engine-replicate`" is satisfied vacuously: no engine is touched.

### 3d. Commit shape

One concern per commit, per repo; **never `git add -A`**; never stage `venv/`,
`__pycache__/`, or `*.log` (both `.gitignore`s already exclude them). Suggested
split: `feat(cli): add opt-in -l/--logs run-log flag (W32)` then
`test(logging): pin default-off and standalone-only logging (W32)` — per repo.

---

## 4. Tests — one per repo: default writes no log, flag does

### 4a. Image Generator — extend `tests/test_logging.py`

The existing file already builds a stub engine and calls `_execute_pipeline`
directly; extend rather than replace.

- **Update the fixture:** add a `logs: bool = True` parameter to `_run_pipeline`
  (`:169–194`) and pass `logs=logs` into the `PipelineContext` (`:181–191`).
  Existing `TestPerFileLogs` / `TestFallbackWriter` assertions stay **unchanged**
  (they keep proving log *content*); they now exercise the enabled path
  explicitly. `TestFallbackWriter.test_write_run_logs_with_empty_paths`
  (`:283–310`) calls `write_run_logs` directly and is unaffected.
- **New tests, named + assertions:**
  1. `test_default_run_writes_no_log` — `_run_pipeline(..., logs=False)`; assert
     `list(tmp_path.glob("*.log")) == []` (and the media file still exists).
  2. `test_logs_flag_writes_log` — `_run_pipeline(..., logs=True)`; assert
     `{"0-a.log", "1-b.log"}` were written (the existing content path).
  3. `TestLogsFlag::test_parse_args_default_logs_off` — monkeypatch `sys.argv`
     to `["prog"]`; `parse_args().logs is False`.
  4. `TestLogsFlag::test_parse_args_l_short_and_long` — `["-l"]` and `["--logs"]`
     each → `args.logs is True`.
  5. `TestLogsFlag::test_logs_enabled_is_standalone_only` — table over
     `_logs_enabled(SimpleNamespace(logs=…), run_mode)`: standalone+True→True;
     standalone+False→False; studiolot+True→**False**; studiolot+False→False.
  6. `test_make_pipeline_context_resolves_logs` — `_make_pipeline_context(...)`
     with `args.logs=True` → `ctx.logs is True` when `run_mode="standalone"`,
     `False` when `run_mode="studiolot"` (pins the §3a wiring).

### 4b. Video Generator — add `tests/test_logging.py`

VG currently has **no** logging test file, so add one. Use a stub engine so no
provider, key, or network is needed (per `AGENTS.md` "mock external
dependencies"):

- Stub engine class with `_on_progress = None` and `run(inputs)` that writes a
  small file per input and returns `SimpleNamespace(status="ok", path=..., ...)`
  (IG's `StubEngine`, `tests/test_logging.py:118–153`, is the template).
- **Tests, named + assertions:**
  1. `test_execute_pipeline_default_writes_no_log` —
     `_execute_pipeline(markdown_files, engine, "replicate", profile, tmp_path,
     input_root, logs=False)`; assert `list(tmp_path.glob("*.log")) == []`.
  2. `test_execute_pipeline_logs_flag_writes_log` — same with `logs=True` after
     `start_output_capture()`; assert `<stem>.log` exists beside the media.
  3. `TestLogsFlag::test_parse_args_default_logs_off` / `…_l_short_and_long`.
  4. `TestLogsFlag::test_logs_enabled_is_standalone_only` — the same table as
     IG (`_logs_enabled`).
  5. `TestLogsFlag::test_run_studiolot_passes_logs_false` — monkeypatch
     `main_verbose._execute_pipeline` to a recorder, plus
     `load_profile_studiolot`, `read_markdown`, `get_api_key`,
     `_resolve_engine_for_studiolot`; call `_run_studiolot(args)` with
     `args.logs=True`; assert the recorder saw `logs is False` (pins the driven
     guard end-to-end).

**Determinism:** every test above is offline (stub engine) and in-process
(capture is `StringIO`/`_TerminalCleaner`). No test needs logging globally
disabled, so the second stop condition stays clear.

**Gate per repo:** `./venv/bin/python -m pytest tests/ -q` (baseline 97/1 IG,
100 VG — zero new failures) and `./venv/bin/ruff check` clean.

---

## 5. Owner verification (Owner-gated; paste commands + observed files back)

Real runs; run each from the repo root with the repo's venv. Pick a tiny input
so the spend is minimal, and note the output directory each run creates.

### Image Generator

```bash
cd ~/GENERATORS/image-generator

# (A) default — expect NO log file
python3 run.py
find USER-FILES/05.OUTPUT -name '*.log' -newermt '-10 minutes' | wc -l   # expect 0

# (B) opt in — expect a .log beside every generated file
python3 run.py -l
find USER-FILES/05.OUTPUT -name '*.log' -newermt '-10 minutes'          # expect >= 1
```

### Video Generator

```bash
cd ~/GENERATORS/video-generator

# (A) default — expect NO log file
python3 run.py
find USER-FILES/05.OUTPUT -name '*.log' -newermt '-10 minutes' | wc -l   # expect 0

# (B) opt in — expect a .log beside every generated video
python3 run.py -l
find USER-FILES/05.OUTPUT -name '*.log' -newermt '-10 minutes'          # expect >= 1
```

### Driven run (studiolot mode) — must leave no log

```bash
# IG — direct driven invocation (same argv f-capacitor's build_command emits)
cd ~/GENERATORS/image-generator
./venv/bin/python -m src.main_simple \
  --profile <profile.yaml> --input_dir <in_dir> --output_dir <out_dir>
find <out_dir> -name '*.log' | wc -l                                     # expect 0

# same run but with --logs: still expect 0 (flag ignored in driven mode)
./venv/bin/python -m src.main_simple \
  --profile <profile.yaml> --input_dir <in_dir> --output_dir <out_dir> --logs
find <out_dir> -name '*.log' | wc -l                                     # expect 0

# VG — identical shape, module src.main_verbose
cd ~/GENERATORS/video-generator
./venv/bin/python -m src.main_verbose \
  --profile <profile.yaml> --input_dir <in_dir> --output_dir <out_dir> --logs
find <out_dir> -name '*.log' | wc -l                                     # expect 0
```

Optionally confirm the real driven path: run one generation from the f-capacitor
TUI and check the target output folder has no `.log` (`build_command` never
passes `-l`, `hc/generator.py:125–137`).

**Record:** the exact commands, the output directory path, and the `find`
counts, so the run is reproducible in the closure.

---

## 6. Milestones (with acceptance tests) and Risks

### Milestones

| # | Milestone | Acceptance |
|---|---|---|
| **M1** | IG: add `-l/--logs` (E1), `PipelineContext.logs` (E2), `_logs_enabled` + gate + capture gate (E3) | `pytest tests/ -q` IG → same 97/1 (0 new failures); `ruff check` clean; `_logs_enabled` + `parse_args` unit tests green |
| **M2** | IG tests: default-off, flag-on, standalone-only, context resolution; existing logging tests updated not weakened | §4a tests all green; every pre-existing log-content assertion still present |
| **M3** | VG: mirror E1–E2 plus `logs` param, gate, capture gate, both call sites | `pytest tests/ -q` VG → 100 + new (0 new failures); `ruff check` clean |
| **M4** | VG tests: default-off, flag-on, standalone-only, driven wiring pin | §4b tests all green |
| **M5** | Owner-gated author verification | §5 commands run; observed counts recorded (no-flag 0; `-l` ≥1; driven 0) |
| **M6** | Docs/bookkeeping: append a one-line note to each repo's `docs/HISTORY.md`; closure doc at the W32 closure path; queue `done` | closure cites §5 results and the commit shas; one concern per commit; no `-A` |

### Risks

1. **Existing tests assume default-on logging.** IG `tests/test_logging.py`
   (`_run_pipeline`, `TestPerFileLogs`, `TestFallbackWriter`) asserts logs are
   written. Mitigation: update the **enable path** (`logs=True` / explicit
   `write_run_logs` call), keep every content assertion — proving the writer
   still works, only the default changed. Never delete an assertion to go green.
2. **A silent consumer of `<stem>.log`.** Investigated: none. f-capacitor only
   reads `.md` sidecars for sync (W99 plan `:152–156`); its job logs are a
   separate system. Both `.gitignore`s exclude `*.log`. Residual risk low.
3. **Over-broad capture change.** Gating `start_output_capture()` touches a
   process-global tee. Mitigation: only `write_run_logs` consumes the capture
   (verified by grep in both repos); `captured_output()` tolerates a missing
   capture; tests that need capture call `start_output_capture()` explicitly as
   they do today.
4. **Twin divergence.** IG and VG implement the gate differently (context field
   vs parameter) because their orchestration already differs (accepted
   divergence). Mitigation: identical flag, default, guard, log naming, and the
   same `_logs_enabled` rule in both; the §4 test names mirror across repos.
5. **Standalone-only surprise.** A caller wanting logs from a driven run cannot
   get them. Mitigation: explicit in `--help`, documented here, and the Owner
   reviews before build. If the Owner prefers driven-mode opt-in later, the
   change is a one-line relaxation of `_logs_enabled`.
6. **Log artifacts committed.** Mitigation: outputs live under
   `USER-FILES/05.OUTPUT/` (gitignored) and `*.log` is ignored in both repos; the
   commit guard forbids `git add -A`.
7. **W103 name drift.** The brief expected a later rename; W103 already landed.
   The plan uses only current names, but an execution pass must re-derive line
   anchors from the tree at build time (as the W22 plan did), since W22 has
   shifted several of them.

---

### Appendix — evidence index (file:line at plan time)

- IG writer + call: `src/main_simple.py:106`, `:212`; `src/utils/logging.py:131,154,172–178`.
- VG writer + call: `src/main_verbose.py:167,182,209`; `src/utils/logging.py:67,94,104–111`.
- Engine: `engine_replicate/engine.py:460,475,526–545` (media + progress only; no log).
- Driven argv: `~/MISC/f-capacitor/hc/generator.py:116–137` (never passes `-l`).
- Downstream: `~/MISC/f-capacitor/docs/implementation/handoffs/W99-sync-sidecar-plan.md:152–156`.
- Ignores: `image-generator/.gitignore`, `video-generator/.gitignore` (`*.log`).
