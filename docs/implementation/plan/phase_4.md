# Part 4 — M4: propose IG doc touch-points (propose-only, Owner-gated)

> Scope: **proposal only — no code, no doc edit applied.** Depends on Parts 1–3
> (proposes documenting what shipped). Owner-gated: the Owner decides whether
> to apply.
> Input plan: `docs/implementation/handoffs/W22-preset-refmedia-plan.md`
> §7.2 / §7.3, §6 M4.
> Branch: `master`.

**Design:** no — documentation proposal; no user-facing surface.

## Goal

Record (do not apply) the IG documentation touch-points for the optional
top-level `reference_images` profile key and the append rule, so the Owner can
rule on them after the build.

## Requirements

### R1 — Draft the proposed text (do not apply)

The brief's `docs/architecture/**` does **not** exist on this tree (only the
root `ARCHITECTURE.md`). Draft one sentence for each named home:

- `ARCHITECTURE.md` "Profiles and endpoints" — the optional top-level
  `reference_images` profile key (a `list[str]`, authored order) and the rule
  that its URLs are appended after each Markdown file's own `reference_urls`.
- `AGENTS.md` "Configuration" — the same optional key, in one line.

Optionally note a docstring sentence for `src/engine_contract.py` mirroring the
key (its "accepted divergence" status is unchanged; no signature change).

### R2 — Record the proposal, never edit

Write the drafted text to `docs/implementation/questions.md` (or the phase
report) as a proposal for the Owner. **Do not edit `ARCHITECTURE.md`,
`AGENTS.md`, or any doc in this part.** No code assertion — proposal only.

### R3 — Re-affirm the cleared stop conditions

Recipe `schema` stays `1`; sidecar / Markdown-file / bullet formats are
untouched; no engine repo, no `video-generator`, no `USER-FILES/04.INPUT/`
writes.

## Verification (gate before plan close)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/ruff check                      # clean; Part 4 changes no source
./venv/bin/python -m pytest tests/ -q      # baseline 86 passed, 1 skipped, 0 failures; ZERO failures after
```

Doc review: the proposal is present in `questions.md`; no doc file was edited.

## Files

- `docs/implementation/questions.md` (proposal text)
- No source or doc edit applied.

## Not in this part

- Applying the doc changes (Owner-gated, separate follow-up).
- Any engine/contract change (none needed).
