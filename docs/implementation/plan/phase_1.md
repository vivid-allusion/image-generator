# Part 1 — M1: preset reference-images accessor + `build_inputs` merge + call site

> Scope: **E1 + E2 + E3** (Python) and the new unit-test file. Depends on nothing.
> Lands the profile → Engine transport so a preset's embedded reference media
> reaches `InputFile.reference_urls`, appended after each Markdown file's own
> refs. Payload provenance is **not** here (Part 2).
> Input plan: `docs/implementation/handoffs/W22-preset-refmedia-plan.md`
> §1 E1–E3, §2 merge rule, §4 tests 1–4/7, §6 M1.
> Branch: `master`.

**Design:** no — internal Python transport (profile → engine boundary); no user-facing surface.

## Goal

A composed profile's optional top-level `reference_images` list flows into the
Engine's `InputFile.reference_urls`, after the Markdown file's own refs, through
the single `_execute_pipeline` call site. Absent/empty/`None` behaves exactly as
today; malformed input fails loud with `ConfigurationError`.

## Requirements

### R1 — `src/processing/profiles.py`: add `preset_reference_urls()`

Append this helper after `load_profile_studiolot` (the file grows 36 → ~52
lines). `ConfigurationError` is already imported (line 8).

```python
def preset_reference_urls(profile: dict[str, Any]) -> list[str]:
    """Return a profile's optional ``reference_images`` list, validated.

    Absent or ``None`` → ``[]`` (the byte-identical path). A non-list, or a
    list holding a non-string entry, is malformed and raises
    ``ConfigurationError`` (fail loud, never a silent drop).
    """
    value = profile.get("reference_images")
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(u, str) for u in value):
        raise ConfigurationError(
            "profile 'reference_images' must be a list of URL strings"
        )
    return list(value)
```

Home rationale: `profiles.py` already owns profile loading and is imported by
both consumers; `payload → processing.profiles` is one-way and cycle-free
(do not put it in `engine_helpers.py`).

### R2 — `src/engine_helpers.py::build_inputs`: merge the preset URLs

Add the import before the `utils.path_resolver` import (keep ruff import
order):

```python
from .processing.profiles import preset_reference_urls
```

Change the signature and body (lines 89–91 / 106–114 at plan time) to:

```python
def build_inputs(
    md_files: list[MarkdownFile],
    platform: str,
    input_root: Path | None = None,
    profile: dict[str, Any] | None = None,
) -> list[Any]:
    """Construct InputFile objects using the Engine's datatype.

    input_root enables output files to mirror the input folder structure:
    each input's directory relative to input_root is passed to the Engine
    as metadata["relative_dir"].

    ``profile`` carries the optional ``reference_images`` list composed by
    the TUI from a preset's embedded reference media. The preset's URLs are
    appended *after* each Markdown file's own ``reference_urls`` (the run's
    bullets are the subject; the preset's media is its own support).
    """
    try:
        pkg = importlib.import_module(f"engine_{platform}")
        InputFile = pkg.InputFile
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Engine '{platform}' is missing or does not export InputFile: {e}"
        ) from e
    validate_input_file(InputFile, platform)
    preset_refs = preset_reference_urls(profile) if profile else []
    return [
        InputFile(
            path=b["path"],
            prompt=b["prompt"],
            reference_urls=[*b["reference_urls"], *preset_refs],
            metadata={"relative_dir": _relative_dir(b["path"].parent, input_root)},
        )
        for b in md_files
    ]
```

When `preset_refs == []`, `[*b["reference_urls"], *[]]` is a new list with the
same contents — the Engine receives the same URLs as today.

### R3 — `src/main_simple.py::_execute_pipeline`: pass the profile

Single call site (line 95 at plan time). Change:

```python
    inputs = build_inputs(ctx.md_files, ctx.platform, ctx.input_root)
```

to:

```python
    inputs = build_inputs(ctx.md_files, ctx.platform, ctx.input_root, profile=ctx.profile)
```

Both run modes reach it through `_execute_pipeline`, so the merge is inherited
without touching either mode.

### R4 — New `tests/test_preset_reference_media.py` (tests 1–4 and 7)

Use a stub engine module injected into `sys.modules` (no provider, key, or
network). Stub shape:

```python
import sys, types
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class InputFile:
    path: Path
    prompt: str
    reference_urls: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

def _stub_engine(monkeypatch):
    mod = types.ModuleType("engine_stub")
    mod.InputFile = InputFile
    monkeypatch.setitem(sys.modules, "engine_stub", mod)
```

- `test_build_inputs_appends_preset_urls_after_bullet_urls` — profile
  `{"reference_images": ["https://preset/a.png", "https://preset/b.png"]}`,
  one `MarkdownFile` with `reference_urls=["https://bullet/x.png"]`; assert
  `inputs[0].reference_urls == ["https://bullet/x.png", "https://preset/a.png",
  "https://preset/b.png"]` (bullet first).
- `test_build_inputs_absent_key_is_unchanged` — profile `{}` **and** `None`;
  assert `inputs[0].reference_urls == ["https://bullet/x.png"]`.
- `test_build_inputs_empty_list_is_unchanged` — profile
  `{"reference_images": []}`; assert `inputs[0].reference_urls ==
  ["https://bullet/x.png"]`.
- `test_build_inputs_malformed_reference_images_raises` — parametrized
  `{"reference_images": "https://x.png"}` (str) and `{"reference_images":
  [1, 2]}` (non-string entries); assert `pytest.raises(ConfigurationError)`.
- `test_execute_pipeline_passes_profile_to_build_inputs` — monkeypatch
  `src.main_simple.build_inputs` to a recorder; stub `_run_with_progress`,
  `compose_run_payloads`, `write_placeholders`, `write_run_logs`,
  `embed_payloads`; assert the recorder received `profile is ctx.profile`.

## Verification (gate before Part 2)

```bash
cd /home/admin/GENERATORS/image-generator
git status --short
./venv/bin/python -m pytest tests/ -q      # baseline 86 passed, 1 skipped, 0 failures; ZERO failures after
./venv/bin/ruff check
find src tests -name '*.py' -exec wc -l {} + | sort -n | tail -6   # nothing over 250
```

## Files

- `src/processing/profiles.py` (E1)
- `src/engine_helpers.py` (E2)
- `src/main_simple.py` (E3)
- `tests/test_preset_reference_media.py` (new)

## Not in this part

- Payload provenance (`preset_reference_urls` key) — Part 2.
- Cross-repo stub-engine acceptance — Part 3.
- Doc touch-point proposals — Part 4.
