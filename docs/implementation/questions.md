## phase_1.md

No blocking questions. E1–E3 are fully specified by plan §3a and mirror existing
repo patterns:

1. The `-l`/`--logs` spec in plan §3a's E2 snippet re-lists `save_payloads` and
   `run_mode`, which already exist in `PipelineContext`. Only `logs: bool = False`
   is genuinely new — no other context change.

**AGENT ANSWER:** Add exactly one field, `logs: bool = False` (plan §3a E2, "Add
a field to `PipelineContext`"); leave `save_payloads`/`run_mode` untouched.

**USER RESPONSE:**
```
```

2. The `_run_pipeline` fixture currently builds `run_mode="studiolot"` yet its
tests assert logs **are** written. With the new gate on `ctx.logs` (not on
`_logs_enabled`), passing `logs=True` explicitly keeps them green.

**AGENT ANSWER:** Add `logs: bool = True` to `_run_pipeline` and pass `logs=logs`
into `PipelineContext` (plan §4a fixture update); every existing assertion stays
unchanged (risk §1). The standalone-only rule is enforced only in
`_make_pipeline_context`/`main`, not in `_execute_pipeline`.

**USER RESPONSE:**
```
```

`main_simple.py` is a pre-existing soft-size breach (353 lines, under the hard
400): report, do not split (AGENTS.md twin table / Owner ruling Q3; plan §1).

No other blocking questions: the writer is gated, not rewritten; no engine,
profile/TOML, or `USER-FILES/04.INPUT/` change; commit shape is one concern
(plan §3d).

### Plan defect found during execution (phase_1)

Plan §4a scopes the test work to `tests/test_logging.py`, but the new `-l/--logs`
flag and the `ctx.logs` gate also invalidate two stale assertions in the W22 pilot
`tests/test_preset_reference_media_pilot.py`:

1. `test_no_new_cli_flag_profile_is_the_only_transport` hard-coded the exact CLI
   flag set (W22 added no flag); W32 mandates `-l`/`--logs`.
2. `test_cross_repo_pilot_stub_engine_boundary` used the unconditional
   `write_run_logs` call as a payload-capture hook; with the writer gated on
   `ctx.logs` (default `False`) the hook was never called.

**AGENT ANSWER:** Update both minimally and without weakening their intent — add
`-l`/`--logs` to the expected flag set (the "no reference/preset flag" assertion
stays), and set `logs=True` on the pilot's direct `PipelineContext` so its
existing payload capture works. No `test_logging.py` log-content assertion was
changed. `/part-exec` gate is green (`97 passed, 1 skipped`; ruff clean).

**USER RESPONSE:**
```
```
