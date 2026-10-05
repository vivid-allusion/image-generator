"""W22 — the Image Generator consumes a preset's embedded reference media.

Part 1 (M1): the profile → Engine merge. A stub engine module is injected into
``sys.modules`` so no real provider, key, or network is needed
(``AGENTS.md``: mock external dependencies).
"""

import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from src.engine_helpers import build_inputs
from src.exceptions import ConfigurationError
from src.processing.context import PipelineContext
from src.processing.payload import compose_payload


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


def _md(reference_urls, tmp_path, name="a.md"):
    return {
        "path": tmp_path / name,
        "prompt": "a prompt",
        "reference_urls": list(reference_urls),
    }


BULLET = "https://bullet/x.png"
PRESET = ["https://preset/a.png", "https://preset/b.png"]


def test_build_inputs_appends_preset_urls_after_bullet_urls(stub_engine, tmp_path):
    inputs = build_inputs(
        [_md([BULLET], tmp_path)],
        "stub",
        tmp_path,
        profile={"reference_images": PRESET},
    )

    assert inputs[0].reference_urls == [BULLET, *PRESET]


def test_build_inputs_absent_key_is_unchanged(stub_engine, tmp_path):
    for profile in ({}, None):
        inputs = build_inputs(
            [_md([BULLET], tmp_path)], "stub", tmp_path, profile=profile
        )

        assert inputs[0].reference_urls == [BULLET]


def test_build_inputs_empty_list_is_unchanged(stub_engine, tmp_path):
    inputs = build_inputs(
        [_md([BULLET], tmp_path)],
        "stub",
        tmp_path,
        profile={"reference_images": []},
    )

    assert inputs[0].reference_urls == [BULLET]


@pytest.mark.parametrize("value", ["https://x.png", [1, 2]])
def test_build_inputs_malformed_reference_images_raises(stub_engine, tmp_path, value):
    with pytest.raises(ConfigurationError):
        build_inputs(
            [_md([BULLET], tmp_path)],
            "stub",
            tmp_path,
            profile={"reference_images": value},
        )


def test_execute_pipeline_passes_profile_to_build_inputs(monkeypatch, tmp_path):
    import src.main_simple as main_simple

    ctx = PipelineContext(
        md_files=[_md([BULLET], tmp_path)],
        engine=object(),
        platform="stub",
        profile={"reference_images": PRESET},
        output_dir=tmp_path,
        input_root=tmp_path,
        save_payloads=False,
        run_mode="studiolot",
    )

    seen: dict = {}

    def recorder(md_files, platform, input_root=None, profile=None):
        seen["profile"] = profile
        return []

    monkeypatch.setattr(main_simple, "build_inputs", recorder)
    monkeypatch.setattr(main_simple, "_run_with_progress", lambda engine, inputs: [])
    monkeypatch.setattr(main_simple, "compose_run_payloads", lambda ctx, results: {})
    monkeypatch.setattr(
        main_simple, "write_placeholders", lambda ctx, results, payloads=None: []
    )
    monkeypatch.setattr(main_simple, "write_run_logs", lambda *a, **k: None)
    monkeypatch.setattr(main_simple, "embed_payloads", lambda *a, **k: None)

    exit_code = main_simple._execute_pipeline(ctx)

    assert exit_code == 0
    assert seen["profile"] is ctx.profile


def _context(profile, tmp_path):
    return PipelineContext(
        md_files=[],
        engine=object(),
        platform="stub",
        profile=profile,
        output_dir=tmp_path,
        input_root=tmp_path,
    )


PRE_W22_KEYS = {
    "schema",
    "generated_at",
    "generator",
    "engine",
    "endpoint",
    "parameters",
    "prompt",
    "prefix",
    "suffix",
    "reference_urls",
    "input_file",
    "media_type",
    "output_file",
}


def test_compose_payload_records_preset_reference_urls(tmp_path):
    ctx = _context({"reference_images": PRESET}, tmp_path)

    payload = compose_payload(ctx, _md([BULLET], tmp_path), tmp_path / "out.png")

    assert payload["reference_urls"] == [BULLET]
    assert payload["preset_reference_urls"] == PRESET
    assert payload["schema"] == 1


def test_compose_payload_omits_key_when_no_preset_refs(tmp_path):
    for profile in ({}, {"reference_images": []}):
        ctx = _context(profile, tmp_path)

        payload = compose_payload(ctx, _md([BULLET], tmp_path), tmp_path / "out.png")

        assert "preset_reference_urls" not in payload
        assert set(payload) == PRE_W22_KEYS
