"""Tests for per-file payload stamping on engine save events."""

import io
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from loguru import logger
from PIL import Image

from src.main_simple import _execute_pipeline
from src.processing.context import PipelineContext
from src.processing.payload import compose_payload, inject_payload, read_payload


class _StagingStubEngine:
    """Mimics engine-fal's stage → announce → reveal save protocol."""

    PROVIDER_NAME = "Stub"
    _on_progress = None

    def __init__(self, output_dir: Path, move_to: Path | None = None) -> None:
        self.output_dir = output_dir
        self.move_to = move_to

    def run(self, inputs: list) -> list[SimpleNamespace]:
        results = []
        for index, item in enumerate(inputs):
            dest = self.output_dir / f"{index}-{item.path.stem}.png"
            temp = self.output_dir / f".{dest.name}.part"
            Image.new("RGB", (32, 32), (0, 0, 255)).save(temp, format="PNG")
            if self._on_progress:
                self._on_progress(
                    SimpleNamespace(
                        message=f"💾 Saved: {dest.name}",
                        current=index + 1,
                        total=len(inputs),
                        saved_path=temp,
                        final_path=dest,
                    )
                )
            temp.replace(dest)
            if self.move_to is not None:
                self.move_to.mkdir(parents=True, exist_ok=True)
                dest.replace(self.move_to / dest.name)
            results.append(
                SimpleNamespace(
                    status="ok",
                    source_path=item.path,
                    path=dest,
                    error_msg="",
                    expected_path=None,
                )
            )
        return results


def _md(path: str, prompt: str) -> dict:
    return {"path": Path(path), "prompt": prompt, "reference_urls": []}


def _install_stub_engine_module(monkeypatch: pytest.MonkeyPatch) -> None:
    class InputFile:
        def __init__(
            self, *, path: Path, prompt: str, reference_urls: list, metadata: dict
        ) -> None:
            self.path = path
            self.prompt = prompt
            self.reference_urls = reference_urls
            self.metadata = metadata

    module = ModuleType("engine_replicate")
    module.InputFile = InputFile
    monkeypatch.setitem(sys.modules, "engine_replicate", module)


def _profile() -> dict:
    return {
        "profile_name": "test",
        "profile_path": "/profiles/test.yaml",
        "endpoint": "test/model",
        "parameters": {"aspect_ratio": "16:9"},
        "media_type": "image",
        "pricing": {"base_cost": 0.05},
        "prompt_prefix": "",
        "prompt_suffix": "",
    }


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, move_to: Path | None = None) -> None:
    _install_stub_engine_module(monkeypatch)
    md_files = [_md("in/a.md", "a castle"), _md("in/b.md", "a lighthouse")]
    ctx = PipelineContext(
        md_files=md_files,
        engine=_StagingStubEngine(tmp_path, move_to),
        platform="replicate",
        profile=_profile(),
        output_dir=tmp_path,
        input_root=Path("in"),
        save_payloads=True,
        run_mode="standalone",
        cli_args={"dry_run": False},
    )
    assert _execute_pipeline(ctx) == 0


def test_stamp_lands_on_the_save_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _run(monkeypatch, tmp_path)

    payload = read_payload(tmp_path / "0-a.png")
    assert payload is not None
    assert payload["output_file"] == "0-a.png"
    assert payload["prompt"]["raw"] == "a castle"
    assert payload["media_type"] == "image"
    assert payload["video_duration"] == ""


@pytest.mark.parametrize(
    ("fmt", "suffix"),
    [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")],
)
def test_video_duration_round_trips_in_every_container(
    tmp_path: Path, fmt: str, suffix: str
):
    """The empty key survives the PNG/iTXt, JPEG/APP1 and WebP/XMP writers."""
    ctx = PipelineContext(
        md_files=[],
        engine=SimpleNamespace(PROVIDER_NAME="Stub"),
        platform="replicate",
        profile=_profile(),
        output_dir=tmp_path,
        input_root=Path("in"),
    )
    target = tmp_path / f"recipe{suffix}"
    Image.new("RGB", (32, 32), (0, 0, 255)).save(target, format=fmt)
    text = json.dumps(compose_payload(ctx, _md("in/a.md", "a castle"), target), indent=2)

    inject_payload(target, text=text)

    payload = read_payload(target)
    assert payload is not None
    assert payload["media_type"] == "image"
    assert payload["video_duration"] == ""


def test_moved_file_is_already_stamped_and_stays_silent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    done = tmp_path / "done"
    sink = io.StringIO()
    sink_id = logger.add(sink, level="ERROR")
    try:
        _run(monkeypatch, tmp_path, move_to=done)
    finally:
        logger.remove(sink_id)

    moved = done / "0-a.png"
    assert moved.exists()
    assert read_payload(moved) is not None
    assert "Failed to embed" not in sink.getvalue()
