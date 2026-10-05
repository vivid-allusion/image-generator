# Part 2 — M2: record preset provenance in the recipe payload

> Scope: **E4** (Python) plus two payload tests. Depends on Part 1 (the
> provenance key is only meaningful once the URLs are sent).
> Input plan: `docs/implementation/handoffs/W22-preset-refmedia-plan.md`
> §1 E4, §3 provenance decision, §4 tests 5–6, §6 M2.
> Branch: `master`.

**Design:** no — recipe JSON provenance; machine-readable, no user-facing surface.

## Goal

Each generated image's embedded recipe payload records the preset's
contribution in an **optional** `preset_reference_urls` key, present only when
non-empty. `reference_urls` keeps its present meaning (the Markdown file's own
list). The recipe `schema` stays `1` (additive, optional key — no fork).

## Requirements

### R1 — `src/processing/payload.py::compose_payload`

Append the import after the `payload_containers` block (keep ruff order):

```python
from .profiles import preset_reference_urls
```

Add one line and one conditional block to `compose_payload` (lines 50–79 at
plan time); the dict body is otherwise unchanged:

```python
    prefix = str(ctx.profile.get("prompt_prefix", "") or "")
    suffix = str(ctx.profile.get("prompt_suffix", "") or "")
    preset_refs = preset_reference_urls(ctx.profile)          # ← new line
    raw = md_file["prompt"]
    payload: dict[str, Any] = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {"name": "image-generator", "version": __version__},
        "engine": {
            "platform": ctx.platform,
            "provider": getattr(ctx.engine, "PROVIDER_NAME", ctx.platform),
        },
        "endpoint": ctx.profile.get("endpoint", ""),
        "parameters": dict(ctx.profile.get("parameters", {})),
        "prompt": {"raw": raw, "wrapped": f"{prefix}{raw}{suffix}".strip()},
        "prefix": prefix,
        "suffix": suffix,
        "reference_urls": list(md_file["reference_urls"]),
        "input_file": relative_posix(md_file["path"], ctx.input_root) or md_file["path"].name,
        "media_type": str(ctx.profile.get("media_type") or "image"),
        "output_file": out_path.name,
    }
    if preset_refs:                                            # ← new block
        payload["preset_reference_urls"] = preset_refs         # ←
    if error is not None:
        payload["error"] = error
    return payload
```

`write_run_logs` serializes the payload dict verbatim, so the run log gains the
key for free (no writer change).

### R2 — Add tests 5–6 to `tests/test_preset_reference_media.py`

- `test_compose_payload_records_preset_reference_urls` — `ctx.profile` with
  `reference_images` `[a, b]`, `md_file` bullet `[x]`; assert
  `payload["reference_urls"] == [x]`, `payload["preset_reference_urls"] ==
  [a, b]`, and `payload["schema"] == 1`.
- `test_compose_payload_omits_key_when_no_preset_refs` — `ctx.profile` without
  `reference_images` (and with `[]`); assert `"preset_reference_urls" not in
  payload` and the payload key set equals the pre-W22 key set (the only change
  is the absent key).

## Verification (gate before Part 3)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/python -m pytest tests/ -q      # baseline 86 passed, 1 skipped, 0 failures; ZERO failures after
./venv/bin/ruff check
find src tests -name '*.py' -exec wc -l {} + | sort -n | tail -6   # nothing over 250
```

## Files

- `src/processing/payload.py` (E4)
- `tests/test_preset_reference_media.py` (tests 5–6)

## Not in this part

- The profile → Engine merge (Part 1 — already landed).
- Cross-repo stub-engine acceptance — Part 3.
- Doc touch-point proposals — Part 4.
- Recipe schema fork (explicitly **not** taken; schema stays `1`).
