# Part 3 — M3: cross-repo pilot — the stub-engine engine-boundary proof

> Scope: **acceptance** (test scaffolding only; no `src/` change). Depends on
> Part 1 (the merge) and strengthens with Part 2 (provenance). The W95
> studiolot half that composes `reference_images` into the profile is already
> shipped (closure commit `35a4c84`).
> Input plan: `docs/implementation/handoffs/W22-preset-refmedia-plan.md`
> §5 cross-repo acceptance, §6 M3.
> Branch: `master`.

**Design:** no — test scaffolding and an engine-boundary assertion; no user-facing surface.

## Goal

Prove the W22 claim at the Engine boundary: a composed profile carrying two
preset URLs reaches the Engine's `InputFile(s)` **after** the Markdown file's
own bullet ref, the `--input_dir` is untouched, no new CLI flag exists, and the
recorded run payload separates `reference_urls` (bullet) from
`preset_reference_urls` (preset).

## Requirements

### R1 — Deterministic repo-local pilot test

Add `test_cross_repo_pilot_stub_engine_boundary` to
`tests/test_preset_reference_media.py` (or a companion test module). Drive the
real pipeline headless in studiolot mode with a **stub engine** that records the
`InputFile` objects it receives (reuse the Part 1 stub-engine pattern; the stub
is test scaffolding, never committed as an Engine):

- `--input_dir <tmp>/in` with **one** `.md` whose body carries one bullet ref;
- `--profile <composed profile>` carrying
  `reference_images: [preset_one, preset_two]`;
- `--output_dir <tmp>/out`, `--platform stub`, payloads on.

Assert:
- the received `reference_urls` **end with the two preset URLs, after the
  bullet's own ref** — `[bullet_ref, preset_one, preset_two]`;
- `<tmp>/in` is unchanged (no new/removed files) and no new CLI flag exists
  (the profile is the only transport);
- the recorded run payload carries `preset_reference_urls ==
  [preset_one, preset_two]` and `reference_urls == [bullet_ref]`;
- `--dry-run` composes nothing to disk (`PreflightExit`) — the merge is
  engine-boundary only.

### R2 — Manual throwaway pilot (Manager/Owner confirmation, non-blocking)

Record the exact headless command and the same three assertions in the
`## Verification` run so the Manager can repeat it against a throwaway project;
the W95 step-5 stub-engine precedent (`theia-platform/test-fixtures/fake-vehicle`)
means no real provider call or key is needed. Step 4 (MC slot routing) is W98,
not this work order.

### R3 — No production-code change

Part 3 must not edit `src/`. If the pilot exposes a defect in Parts 1–2, the fix
is a repair of that part, not a rewrite here.

## Verification (gate before Part 4)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/python -m pytest tests/ -q      # baseline 86 passed, 1 skipped, 0 failures; ZERO failures after
./venv/bin/ruff check
find src tests -name '*.py' -exec wc -l {} + | sort -n | tail -6   # nothing over 250
```

Engine-boundary assertion (the pilot's core): the stub engine records
`reference_urls == [bullet_ref, preset_one, preset_two]`, `--input_dir`
unchanged, and the run payload's `preset_reference_urls == [preset_one,
preset_two]` / `reference_urls == [bullet_ref]`.

## Files

- `tests/test_preset_reference_media.py` (pilot test; test-local stub engine)
- No `src/` change.

## Not in this part

- Doc touch-point proposals — Part 4.
- Video Generator slot routing — W98.
- Contract/engine repo changes (none needed; the `InputFile` contract already
  requires `reference_urls`).
