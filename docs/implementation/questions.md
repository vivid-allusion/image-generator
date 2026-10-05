## phase_1.md

1. `src/main_simple.py` is 353 lines — over the soft 250 limit (`guard=` and
   AGENTS.md rule 6), under the hard 400. Split it while we are here?
2. Should all W22 tests live in one new file
   `tests/test_preset_reference_media.py`, or be split per concern?

**AGENT ANSWER:** No split — `main_simple.py` is a named accepted-divergence
entry point (AGENTS.md twin table: "kept by Owner ruling Q3"), and this unit's
change is a one-line call-site argument (E3) that leaves the length unchanged
(plan §1: "unchanged in length ±1 line"). Splitting is out of scope.

**USER RESPONSE:**
```
```

**AGENT ANSWER:** One file. Plan §4 names exactly one new file,
`tests/test_preset_reference_media.py`, holding tests 1–6; Part 3 appends the
pilot test to the same file. Fewer files, matches the plan verbatim.

**USER RESPONSE:**
```
```

No other blocking questions: the merge order (bullet first, preset appended),
the accessor's single home (`src/processing/profiles.py`), the loud
`ConfigurationError` on malformed input, and the `profile=None` default are all
fixed by the plan and consistent with AGENTS.md.

## phase_2.md

No blocking questions. E4 is fully specified: import `preset_reference_urls`
from `.profiles`, compute `preset_refs` once, and add the payload key only when
non-empty; `schema` stays `1` and `write_run_logs` serializes the payload verbatim
(no writer change). No conflict with AGENTS.md or Part 1's landed behaviour.

## phase_3.md

1. Drive the pilot through the real `main()` CLI in a subprocess (studiolot
   mode, `--platform stub`), or through a deterministic in-repo integration test
   via `_execute_pipeline` with a stub engine in `sys.modules`?

**AGENT ANSWER:** In-repo integration test through `_execute_pipeline` with the
stub engine. Plan §5 explicitly allows "IG's test fixtures for the unit-level
variant"; it is offline and deterministic and proves the same three
engine-boundary facts (order, `--input_dir` unchanged, payload provenance). The
headless CLI pilot is recorded for the Manager/Owner as the manual confirmation.

**USER RESPONSE:**
```
```

No other blocking questions: phase_3 adds no `src/` change (self-contained test
scaffolding), and the W95 studiolot half that composes `reference_images` is
already shipped.

## phase_4.md

Deliverable (propose-only; Owner-gated — do **not** apply): document the optional
top-level `reference_images` profile key and the append rule. Both proposed homes
exist (`ARCHITECTURE.md` "Profiles and endpoints" line 72; `AGENTS.md`
"Configuration" line 146); the brief's `docs/architecture/**` does not exist on
this tree.

Proposed `ARCHITECTURE.md` → "Profiles and endpoints" (after the existing first
paragraph):

> A composed profile may also carry an optional top-level `reference_images`
> list — a preset's embedded reference media — whose URLs are appended after
> each Markdown file's own reference bullets before they reach the Engine.

Proposed `AGENTS.md` → "Configuration" (new bullet):

> - Profile format may include an optional top-level `reference_images` list
>   (URLs); they are appended after each Markdown file's own `reference_urls`.

Optional (no code): a one-line docstring note on `src/engine_contract.py`'s
`reference_urls` field — not proposed for edit now.

No blocking questions. Neither doc is edited in this part; the recipe `schema`
stays `1`, the frozen formats are untouched, and no engine or `video-generator`
change is needed.
