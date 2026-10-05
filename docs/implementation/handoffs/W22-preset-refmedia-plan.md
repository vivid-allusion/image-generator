# W22 — Image Generator consumes a preset's embedded reference media — plan

> **Workstream:** W22 / the Image Generator half of the W95 concat-presets work
> (the W95 plan calls the FC half "W95b"; the W95 closure names it **W209**).
> Video Generator is W98.
> **Repo:** `~/GENERATORS/image-generator` (alias `image-generator`).
> **Planning only — no code, no asset files, no preset content.**
> **Status of this doc:** uncommitted in the tree for the Manager to collect +
> verify; the Owner reviews before any build.
> **Closure (when built):**
> `~/PLATFORM/theia-platform/docs/handoffs/W22-preset-refmedia-closure.md`.
>
> **Read first / inputs used (paths resolved to today's names):**
> - `~/MISC/f-capacitor/docs/implementation/handoffs/W95-concat-presets-plan.md`
>   (studiolot renamed to **f-capacitor**). Cited below as **W95 plan §X**.
> - `~/GENERATORS/image-generator/AGENTS.md`.
> - The tree at `master` @ `998f01e` (clean). The brief's
>   `image-generator docs/architecture/**` **does not exist**: the repo has no
>   `docs/architecture/` directory, only a root `ARCHITECTURE.md` (see §7.2).
> - `~/INFRA/loops-and-goals-mgmt/loop.conf` `[image-generator]`.
> - Shipped dependency read in-repo: `~/MISC/f-capacitor/hc/profiles.py`
>   `compose_profile` (line 123 emits `profile["reference_images"]`) and
>   `~/MISC/f-capacitor/hc/presets.py::extract_reference_media` (lines 109–129).
> - Shipped closure: `~/PLATFORM/theia-platform/docs/handoffs/W95-concat-presets-closure.md`.

## 0. Baseline and stop-condition checks (all cleared)

- **Baseline gate, re-run on the clean tree at plan time:**
  `./venv/bin/python -m pytest tests/ -q` → **86 passed, 1 skipped, 0 failures**.
  `./venv/bin/ruff check` → **All checks passed!** The plan's gate is therefore
  "zero new failures", not a pre-existing failure count.
- **Stop condition — profile key shape:** the key studiolot actually emits **is**
  `reference_images` and it is a `list[str]` in authored order
  (`hc/profiles.py:123` → `extract_reference_media`). Matches the brief. **No stop.**
- **Stop condition — frozen format:** the change rides the composed profile only;
  the sidecar/Markdown-file/bullet formats are untouched (W95 plan §5.4 closing
  note; `PHILOSOPHY.md` §3/§4). **No stop.**
- **Stop condition — recipe schema fork:** provenance is recorded with an
  **additive, optional** key while `schema` stays `1`; old recipes and readers stay
  valid. **No fork needed. No stop.**
- **Not in scope:** `video-generator` (W96/W98), contract files (studiolot wording
  already landed; theia `INTERFACES-v1.md` is a separate doc task), any engine
  repo, any CLI flag, `USER-FILES/04.INPUT/` writes.

---

## 1. Edit list (line-anchored, read from the tree at plan time)

Four edits, all Python; no new CLI flag; no new file in `src/`. The helper in
E1 is the single interpretation point for the optional profile key so
`build_inputs` (merge) and `compose_payload` (provenance) can never diverge.

### E1 — `src/processing/profiles.py` — add `preset_reference_urls()` (new helper)

File is 36 lines; the addition keeps it well under the soft 250 limit.
`ConfigurationError` is already imported (line 8).

**Before (end of file, lines 32–36):**
```python
def load_profile_studiolot(profile_path: Path) -> dict[str, Any]:
    """Load profile YAML from --profile flag."""
    if not profile_path.exists():
        raise ConfigurationError(f"Profile not found: {profile_path}")
    return _parse_profile_yaml(profile_path)
```

**After:**
```python
def load_profile_studiolot(profile_path: Path) -> dict[str, Any]:
    """Load profile YAML from --profile flag."""
    if not profile_path.exists():
        raise ConfigurationError(f"Profile not found: {profile_path}")
    return _parse_profile_yaml(profile_path)


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

> **Home rationale:** `profiles.py` already owns profile loading and is imported
> by both consumers. Putting the accessor in `engine_helpers.py` and importing it
> from `payload.py` would add a `payload → engine_helpers` coupling that does not
> exist today; `payload → processing.profiles` is one-way and cycle-free.
> Alternative considered and rejected: duplicate the guard inline in both sites.

### E2 — `src/engine_helpers.py` — merge in `build_inputs()` (the single `InputFile` site)

New import (insert before the `utils.path_resolver` import, keeping ruff's
import order):
```python
from .processing.profiles import preset_reference_urls
```

**Before (signature lines 89–91, body lines 106–114):**
```python
def build_inputs(
    md_files: list[MarkdownFile], platform: str, input_root: Path | None = None
) -> list[Any]:
    """Construct InputFile objects using the Engine's datatype.
    ...
    """
    try:
        pkg = importlib.import_module(f"engine_{platform}")
        InputFile = pkg.InputFile
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Engine '{platform}' is missing or does not export InputFile: {e}"
        ) from e
    validate_input_file(InputFile, platform)
    return [
        InputFile(
            path=b["path"],
            prompt=b["prompt"],
            reference_urls=b["reference_urls"],
            metadata={"relative_dir": _relative_dir(b["path"].parent, input_root)},
        )
        for b in md_files
    ]
```

**After:**
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
same contents — the Engine receives the same URLs as today (see §2, and the
"byte-identical" nuance in §4 test 2).

### E3 — `src/main_simple.py::_execute_pipeline` — pass the profile

**Before (line 95):**
```python
    inputs = build_inputs(ctx.md_files, ctx.platform, ctx.input_root)
```
**After:**
```python
    inputs = build_inputs(ctx.md_files, ctx.platform, ctx.input_root, profile=ctx.profile)
```
This is the only `build_inputs` call site; both run modes (`_run_studiolot` and
`_run_standalone`) reach it through `_execute_pipeline`, so the merge is
inherited everywhere without touching either mode.

### E4 — `src/processing/payload.py::compose_payload` — record provenance

New import (append after the `payload_containers` block, keeping ruff order):
```python
from .profiles import preset_reference_urls
```

**Before (lines 50–79):**
```python
def compose_payload(
    ctx: PipelineContext,
    md_file: MarkdownFile,
    out_path: Path,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prefix = str(ctx.profile.get("prompt_prefix", "") or "")
    suffix = str(ctx.profile.get("prompt_suffix", "") or "")
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
    if error is not None:
        payload["error"] = error
    return payload
```

**After (only the three marked changes; the dict body is otherwise unchanged):**
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

`reference_urls` keeps its present meaning (the Markdown file's own list); the
preset's contribution is recorded separately (see §3). `write_run_logs` already
serializes the payload dict verbatim, so the run log gains the key for free.

### Not edited (and why)

- `src/cli.py` — **no new flag**. The profile travels only via `--profile`
  (studiolot) or `USER-FILES/03.PROFILES/` (standalone).
- `src/processing/context.py` — `PipelineContext.profile` already exists (line 21).
- `src/datatypes.py` — `MarkdownFile` gains nothing; IG has no named
  `references` slot (contrast Motion Conductor), so everything rides the flat
  `reference_urls` list.
- `src/engine_contract.py` / engine repos — the `InputFile` contract already
  requires `reference_urls`; no signature change.
- `USER-FILES/04.INPUT/` — never mutated.

---

## 2. Merge rule and precedence (restated for Image Generator)

- **Order:** `merged = [*md_file.reference_urls, *profile["reference_images"]]`.
  The Markdown file's own refs come first; the preset's URLs are appended.
- **Precedence:** the run's bullets are the subject; the preset's refs are the
  preset's own example/style support (W95 plan §5.2 verbatim: "the run's bullet
  refs are the subject; the preset refs are the preset's own example/style
  support").
- **Shape:** IG's `MarkdownFile` has **no** named `references` slot, so unlike MC
  there is no slot routing — every URL lands in the flat `reference_urls` list the
  Engine contract already requires (`engine_contract.py`; `engine-replicate`
  `datatypes.InputFile`). If a future endpoint declares a `reference_images`
  slot, that is a separate engine-side concern, not IG's.
- **Transport:** profile only. `--profile` boundary preserved; no new CLI flag;
  `--input_dir` is never mutated; preset media is never materialized as bullets
  (W95 plan §5.2 rejected alternative (a)).
- **Both run modes:** `_run_studiolot` and `_run_standalone` both call the single
  `_execute_pipeline`, so both inherit the merge.
- **Absent / empty / `None`:** `preset_reference_urls` returns `[]` and the
  merged list equals the Markdown file's own — the pre-W22 behaviour.
- **Malformed:** a non-list `reference_images`, or a list with a non-string
  entry, raises `ConfigurationError` inside `build_inputs`, before `engine.run`.
  `main()` catches `ConfigurationError` → `logger.error` + exit code 1. Never a
  silent drop.

---

## 3. Provenance — the `preset_reference_urls` decision and the recipe schema

- **Decision:** add an **optional** payload key `preset_reference_urls` holding
  the preset's contribution, in authored order. It is present **only when
  non-empty**.
- **Why a separate key, not a merged `reference_urls`:** it records provenance —
  a recipe consumer can tell which URLs came from the preset versus the bullet —
  without changing the established meaning of `reference_urls`. Reconstructing
  the exact list sent to the Engine is `reference_urls + preset_reference_urls`.
  This mirrors W95 plan §5.3 exactly ("Add a separate `preset_reference_urls`
  key so the recipe records which URLs came from the preset versus the bullet").
- **Recipe schema stays `1`:** the key is additive and optional; `read_payload`
  returns whatever JSON is embedded and consumers tolerate extra keys; recipes
  written before W22 remain byte-identical. **No fork** (stop condition cleared).
- **Byte-identical absent case:** when no preset refs exist the key is omitted,
  so the payload has the same key set as today.
- `write_run_logs` serializes the payload verbatim; no writer change is needed.

---

## 4. Tests

**Gate (from `loop.conf` `[image-generator]`):**
`./venv/bin/python -m pytest tests/` and `./venv/bin/ruff check`.
Baseline at plan time: **86 passed, 1 skipped, 0 failures**; ruff clean. Every
milestone must keep zero new failures and never weaken an existing test.

**New file: `tests/test_preset_reference_media.py`** (mirrors the f-capacitor
regression-lock name). It uses a **stub engine module** injected into
`sys.modules` (per `AGENTS.md` "mock external dependencies") so no real provider,
key, or network is needed. The stub:

```python
# test-local stub, not committed as an Engine
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

Named tests and their **exact assertions**:

1. `test_build_inputs_appends_preset_urls_after_bullet_urls`
   - profile `{"reference_images": ["https://preset/a.png", "https://preset/b.png"]}`;
     one `MarkdownFile` with `reference_urls=["https://bullet/x.png"]`.
   - **Assert:** `inputs[0].reference_urls == ["https://bullet/x.png",
     "https://preset/a.png", "https://preset/b.png"]` (order: bullet first).
2. `test_build_inputs_absent_key_is_unchanged`
   - profile `{}` **and** profile `None`.
   - **Assert:** `inputs[0].reference_urls == ["https://bullet/x.png"]`.
3. `test_build_inputs_empty_list_is_unchanged`
   - profile `{"reference_images": []}`.
   - **Assert:** `inputs[0].reference_urls == ["https://bullet/x.png"]`.
4. `test_build_inputs_malformed_reference_images_raises`
   - parametrized `{"reference_images": "https://x.png"}` (str) and
     `{"reference_images": [1, 2]}` (non-string entries).
   - **Assert:** `pytest.raises(ConfigurationError)`.
5. `test_compose_payload_records_preset_reference_urls`
   - `ctx.profile` with `reference_images` `[a, b]`; `md_file` bullet `[x]`.
   - **Assert:** `payload["reference_urls"] == [x]`,
     `payload["preset_reference_urls"] == [a, b]`, and `payload["schema"] == 1`.
6. `test_compose_payload_omits_key_when_no_preset_refs`
   - `ctx.profile` without `reference_images` (and with `[]`).
   - **Assert:** `"preset_reference_urls" not in payload`; the payload key set
     equals the pre-W22 key set (i.e. the only change is the absent key).
7. `test_execute_pipeline_passes_profile_to_build_inputs`
   - monkeypatch `src.main_simple.build_inputs` to a recorder; stub
     `_run_with_progress`, `compose_run_payloads`, `write_placeholders`,
     `write_run_logs`, `embed_payloads`.
   - **Assert:** the recorder received `profile is ctx.profile`.

Tests 1–4 exercise the merge and the loud guard; 5–6 fix provenance and the
byte-identical absent path; 7 pins the call-site wiring (the one place the brief
names). The cross-repo engine-boundary proof is §5.

---

## 5. Cross-repo acceptance (W95 plan §5.5, steps 3–5 adapted for IG)

W95 §5.5 steps 1–2 (studiolot composes `reference_images` into the generated
profile) **already shipped** in W95 (closure commit `35a4c84`). IG owns the step-3
analog (Frame Composer's role in the W95 plan is played here by the Image
Generator):

- **Pilot (step 3, adapted):** in a throwaway project, run IG headless in
  studiolot mode:
  `--input_dir <throwaway>/in` (one `.md` whose body carries **one** bullet ref),
  `--profile <composed profile from step 1–2>`,
  `--output_dir <throwaway>/out`, `--platform stub`, with a **stub engine** that
  records the `InputFile`(s) it receives.
  - **Assert:** the received `reference_urls` **end with the two preset URLs,
    after the bullet's own ref**, i.e. `[bullet_ref, preset_one, preset_two]`.
  - **Assert:** `--input_dir` is unchanged (no new/removed files) and no new CLI
    flag exists (the profile is the only transport).
  - **Assert:** the recorded run payload carries `preset_reference_urls ==
    [preset_one, preset_two]` and `reference_urls == [bullet_ref]` (§3).
- **Step 4 (MC slot routing) is W98, not this work order.** Step 5's stub-engine
  precedent applies: follow the `theia-platform/test-fixtures/fake-vehicle`
  pattern (W95 plan §5.5 step 5 / W1 §0.5) so no real provider call or key is
  needed; the "reaches the model" link is the engine-boundary assertion.

**Exactly what Image Generator must do to make step 3 pass:**
1. Accept the composed profile via `--profile`; `_parse_profile_yaml` keeps the
   `reference_images` key (it does no key filtering and errors on nothing).
2. `build_inputs(md_files, platform, input_root, profile=ctx.profile)` must append
   the preset URLs after the bullet's own and pass them to
   `InputFile.reference_urls` (E2/E3).
3. Write nothing to `--input_dir`; add no CLI flag.
4. Record `preset_reference_urls` in the payload so the boundary assertion can
   see provenance (E4).
5. `--dry-run` composes nothing to disk (`PreflightExit`); the merge is
   engine-boundary only.

The stub engine itself is **test scaffolding**, not an Engine repo change; it
lives under the throwaway project's `00_APPLICATIONS/ENGINES/engine-stub/`
(for discovery) or IG's test fixtures for the unit-level variant.

---

## 6. Milestones (each with an acceptance test)

| M | Scope | Acceptance test |
|---|---|---|
| **M0** | Confirm baseline (no code). | `pytest tests/` = 86 passed / 1 skipped / 0 failures; `ruff check` clean. Recorded in §0. |
| **M1** | E1 helper + E2 `build_inputs` merge + E3 call site. | Tests 1–4 and 7 pass; `pytest tests/` zero new failures; `ruff check` clean. |
| **M2** | E4 payload provenance. | Tests 5–6 pass; `pytest tests/` zero new failures; `ruff check` clean; recipe `schema == 1`. |
| **M3** | Cross-repo pilot with the stub engine (§5). | Pilot asserts `[bullet_ref, preset_one, preset_two]` at the engine boundary, `--input_dir` unchanged, and `preset_reference_urls` in the run payload. |
| **M4** *(propose-only docs)* | Propose IG doc touch-points (§7.2). | `ruff check` clean; doc review. No code assertion — proposal only, Owner-gated. |

M1 and M2 are independent-ish but land in order (M2's provenance key is only
meaningful once M1 sends the URLs). M3 requires the W95 studiolot half (shipped)
and a composed profile; it does not require M2, but M2 strengthens its
assertions.

---

## 7. Risks / contract touch-points (propose, never apply)

1. **Engine contract — no change.** `engine-contract`/`EngineInputFile` already
   requires `reference_urls`; `engine-replicate` `InputFile` already has the
   field. IG sends a longer list, same type. Nothing to propose to engines.
2. **IG doc touch-points (propose only).** The brief's `docs/architecture/**`
   does not exist on the tree (only root `ARCHITECTURE.md`). Proposed,
   Owner-gated, after the build: add one sentence to `ARCHITECTURE.md`
   "Profiles and endpoints" and/or `AGENTS.md` "Configuration" describing the
   optional top-level `reference_images` profile key and the append rule. Do
   **not** edit now.
3. **`engine_contract.py` mirror.** Accepted divergence (AGENTS.md twin table);
   no signature change needed. A docstring note about the profile key would be a
   propose-only change — no code.
4. **Frozen formats untouched.** Markdown/sidecar/bullet format unchanged; preset
   media rides the composed profile (`PHILOSOPHY.md` §3/§4). Stop condition
   cleared.
5. **Recipe schema stays `1`; no fork.** `preset_reference_urls` is additive and
   omitted when empty. Stop condition cleared.
6. **Payload size.** `MAX_JPEG_PAYLOAD = 60_000`; `inject_payload` raises for an
   over-limit JPEG and `embed_payloads` logs + continues (non-fatal). A very long
   preset URL list could push a JPEG recipe over. Preset lists are small in
   practice; note as monitoring risk, no change proposed.
7. **Preset-ref reachability.** IG's `read_markdown_files` HEAD-validates the
   **bullet's** URLs but preset URLs arrive via the profile and are **not**
   re-validated by IG (parity with the studied design: reachability stays
   generation-time, rejected by the engine/provider). If the Owner wants IG to
   validate preset refs too, that is a scope change (network at read time) —
   propose, do not apply.
8. **No dedup.** A preset URL equal to a bullet URL appears twice in the merged
   list (parity with W95; engines receive both). Documented behaviour; no dedup
   proposed.
9. **Twin divergence.** IG and VG `engine_helpers.py` are accepted divergence;
   VG's merge lands in W98. Keep the merge shape identical but land per repo —
   do not co-vendor.
10. **Work-order numbering.** The W95 closure names the FC half **W209** and MC
    **W98**; this brief names the IG half **W22** (and calls it "W95b").
    Non-blocking; flagged for the Manager so closure/queue references line up.

---

## 8. Boundaries honoured

- `image-generator` only; Python; soft 250 / hard 400 lines (touched files:
  `profiles.py` 36→~52, `engine_helpers.py` 173→~180, `payload.py` 184→~188,
  `main_simple.py` 353 unchanged in length ±1 line — the last is a large
  accepted-divergence entry point, not a module to grow).
- Module-per-concern; the shared key accessor has exactly one home.
- Never `git add -A`; no `venv/` or log artifacts; plan is the only artifact and
  stays uncommitted for the Manager.
- No code, no preset content, no contract files, no `video-generator`, no
  `USER-FILES/04.INPUT/` writes.
