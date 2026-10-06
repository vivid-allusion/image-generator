"""W22 Part 3 (M3) — the cross-repo pilot's engine-boundary proof.

Companion to ``test_preset_reference_media.py`` (the plan's M3 allows "or a
companion test module"): it drives the real pipeline with a stub engine injected
into ``sys.modules`` so no provider, key, or network is needed.

Manual throwaway pilot (studiolot mode, ``--platform stub``; no provider key):

    ./venv/bin/python -m src.main_simple \
        --input_dir <throwaway>/in \
        --profile <composed.yaml with reference_images: [preset_one, preset_two]> \
        --output_dir <throwaway>/out \
        --platform stub

The stub engine records its ``InputFile``(s): ``reference_urls`` ==
``[bullet_ref, preset_one, preset_two]``; ``<throwaway>/in`` is unchanged (no
new/removed files); the run payload carries ``preset_reference_urls`` ==
``[preset_one, preset_two]`` and ``reference_urls`` == ``[bullet_ref]``.
"""

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from src.exceptions import PreflightExit
from src.processing.context import PipelineContext


@dataclass
class InputFile:
    """Test-local stand-in for an Engine ``InputFile`` (not a committed Engine)."""

    path: Path
    prompt: str
    reference_urls: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@pytest.fixture
def stub_engine(monkeypatch):
    mod = types.ModuleType("engine_stub")
    mod.InputFile = InputFile
    monkeypatch.setitem(sys.modules, "engine_stub", mod)
    return mod


BULLET = "https://bullet/x.png"


def _md(reference_urls, tmp_path, name="a.md"):
    return {
        "path": tmp_path / name,
        "prompt": "a prompt",
        "reference_urls": list(reference_urls),
    }


def test_cross_repo_pilot_stub_engine_boundary(stub_engine, monkeypatch, tmp_path):
    """The W95 pilot, adapted: a composed profile's preset refs reach the Engine
    after the bullet's own, the input dir is untouched, and the run payload
    records provenance."""
    import src.main_simple as main_simple

    input_dir = tmp_path / "in"
    input_dir.mkdir()
    md_path = input_dir / "shot.md"
    md_path.write_text("a prompt\n![x](https://bullet/x.png)\n", encoding="utf-8")
    before = sorted(p.name for p in input_dir.iterdir())

    preset_one, preset_two = "https://preset/one.png", "https://preset/two.png"
    md = {"path": md_path, "prompt": "a prompt", "reference_urls": [BULLET]}
    out_path = tmp_path / "out" / "shot.png"

    recorded: dict = {}

    class RecordingEngine:
        PROVIDER_NAME = "stub-provider"

        def run(self, inputs):
            recorded["inputs"] = list(inputs)
            return [
                types.SimpleNamespace(status="ok", path=out_path, source_path=md_path)
            ]

    ctx = PipelineContext(
        md_files=[md],
        engine=RecordingEngine(),
        platform="stub",
        profile={"reference_images": [preset_one, preset_two]},
        output_dir=tmp_path / "out",
        input_root=input_dir,
        save_payloads=False,
        logs=True,
        run_mode="studiolot",
    )

    captured: dict = {}
    monkeypatch.setattr(
        main_simple, "_run_with_progress", lambda engine, inputs: engine.run(inputs)
    )
    monkeypatch.setattr(
        main_simple,
        "write_run_logs",
        lambda paths, out_dir, ctx, payloads, results: captured.update(payloads),
    )
    monkeypatch.setattr(main_simple, "write_placeholders", lambda *a, **k: [])
    monkeypatch.setattr(main_simple, "embed_payloads", lambda *a, **k: None)

    exit_code = main_simple._execute_pipeline(ctx)

    # 1. Engine boundary: bullet first, then the preset's two URLs.
    assert exit_code == 0
    assert recorded["inputs"][0].reference_urls == [BULLET, preset_one, preset_two]

    # 2. The input directory is untouched (no bullet materialised).
    assert sorted(p.name for p in input_dir.iterdir()) == before

    # 3. Provenance in the run payload; schema stays 1.
    payload = json.loads(next(iter(captured.values())))
    assert payload["reference_urls"] == [BULLET]
    assert payload["preset_reference_urls"] == [preset_one, preset_two]
    assert payload["schema"] == 1


def test_dry_run_preflight_exits_without_composing(tmp_path):
    """--dry-run must compose nothing: the pre-flight check raises PreflightExit
    before any engine call (plan §5 step 5)."""
    import src.main_simple as main_simple

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    args = types.SimpleNamespace(cost_estimation=False, dry_run=True)

    with pytest.raises(PreflightExit):
        main_simple._handle_preflight_checks(args, [_md([BULLET], tmp_path)], {})

    assert list(out_dir.iterdir()) == []


def test_no_new_cli_flag_profile_is_the_only_transport():
    """W22 adds no CLI flag; the composed profile is the only transport (plan §2)."""
    from src.cli import _ARGUMENTS

    flags = {flag for spec in _ARGUMENTS for flag in spec["flags"]}

    assert flags == {
        "--input_dir",
        "--output_dir",
        "--profile",
        "--platform",
        "--dry-run",
        "--debug",
        "--verbose",
        "-l",
        "--logs",
        "--cost-estimation",
        "--force-png",
        "--no-save-payloads",
        "--install-default-engine",
    }
    assert not any("reference" in flag or "preset" in flag for flag in flags)
