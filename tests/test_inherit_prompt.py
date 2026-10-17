"""Tests for inherit_prompt — an edit keeps the edited image's own recipe."""

import io
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from loguru import logger
from PIL import Image

from src.exceptions import ConfigurationError
from src.processing.context import PipelineContext
from src.processing.inherit import mark_failed_inheritance, resolve_inherited_prompts
from src.processing.payload import compose_payload, read_payload
from src.processing.payload_containers import inject_jpeg
from src.processing.profiles import inherit_prompt_enabled, profile_has_prompt_text

FIRST = "https://b2/first.png"
SECOND = "https://b2/second.png"


def _recipe_text(prompt: str = "the original prompt", prefix: str = "", suffix: str = "") -> str:
    return json.dumps(
        {
            "schema": 1,
            "generated_at": "2026-10-01T10:00:00+00:00",
            "generator": {"name": "image-generator", "version": "2.1.0"},
            "endpoint": "google/nano-banana-2",
            "parameters": {"resolution": "1K"},
            "prompt": {"raw": prompt, "wrapped": f"{prefix}{prompt}{suffix}".strip()},
            "prefix": prefix,
            "suffix": suffix,
            "reference_urls": [],
            "input_file": "shot.md",
            "media_type": "image",
            "output_file": "shot.png",
        },
        indent=2,
    )


def _image_bytes(text: str) -> bytes:
    """A minimal JPEG carrying `text` as its recipe (readable via the XMP readers)."""
    return inject_jpeg(b"\xff\xd8", text)


def _error_recipe_bytes() -> bytes:
    recipe = json.loads(_recipe_text())
    recipe["error"] = {"message": "boom"}
    return _image_bytes(json.dumps(recipe))


def _md(tmp_path: Path, prompt: str = "upscale this to 4K", refs: list[str] | None = None) -> dict:
    return {
        "path": tmp_path / "up.md",
        "prompt": prompt,
        "reference_urls": list(refs if refs is not None else [FIRST, SECOND]),
    }


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, data: bytes | None) -> list[str]:
    calls: list[str] = []

    def fake_fetch(url: str, timeout: float | None = None) -> bytes | None:
        calls.append(url)
        return data

    monkeypatch.setattr("src.processing.inherit.fetch_image", fake_fetch)
    return calls


def _ctx(tmp_path: Path, md: dict, profile: dict | None = None) -> PipelineContext:
    return PipelineContext(
        md_files=[md],
        engine=None,
        platform="replicate",
        profile=profile or {},
        output_dir=tmp_path,
    )


class _StagingStubEngine:
    """Writes a real PNG per input and emits the engine's save-event protocol."""

    PROVIDER_NAME = "Stub"
    _on_progress = None

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def run(self, inputs: list) -> list[SimpleNamespace]:
        results = []
        for index, item in enumerate(inputs):
            dest = self.output_dir / f"{item.path.stem}-0{index}.png"
            temp = self.output_dir / f".{dest.name}.part"
            Image.new("RGB", (16, 16), (0, 0, 255)).save(temp, format="PNG")
            if self._on_progress:
                self._on_progress(
                    SimpleNamespace(
                        message=f"Saved: {dest.name}",
                        current=index + 1,
                        total=len(inputs),
                        saved_path=temp,
                        final_path=dest,
                    )
                )
            temp.replace(dest)
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


# ── the profile key ──────────────────────────────────────────────────────────


def test_inherit_prompt_enabled_validates_the_profile_key():
    assert inherit_prompt_enabled({}) is False
    assert inherit_prompt_enabled({"inherit_prompt": None}) is False
    assert inherit_prompt_enabled({"inherit_prompt": True}) is True
    assert inherit_prompt_enabled({"inherit_prompt": False}) is False
    with pytest.raises(ConfigurationError):
        inherit_prompt_enabled({"inherit_prompt": "yes"})
    with pytest.raises(ConfigurationError):
        inherit_prompt_enabled({"inherit_prompt": 1})


def test_profile_has_prompt_text():
    assert profile_has_prompt_text({}) is False
    assert profile_has_prompt_text({"prompt_prefix": "  "}) is False
    assert profile_has_prompt_text({"prompt_prefix": "Upscale this"}) is True
    assert profile_has_prompt_text({"prompt_suffix": "in 4K"}) is True


# ── resolution ───────────────────────────────────────────────────────────────


def test_resolve_reads_only_the_first_reference(monkeypatch, tmp_path):
    calls = _patch_fetch(monkeypatch, _image_bytes(_recipe_text(prefix="a ", suffix=" b")))
    md = _md(tmp_path)

    inherited = resolve_inherited_prompts([md])

    record = inherited[str(md["path"])]
    assert calls == [FIRST]
    assert record["prompt"]["raw"] == "the original prompt"
    assert record["prompt"]["wrapped"] == "a the original prompt b"
    assert record["prefix"] == "a "
    assert record["suffix"] == " b"
    assert record["source"] == {
        "url": FIRST,
        "generated_at": "2026-10-01T10:00:00+00:00",
        "endpoint": "google/nano-banana-2",
    }


def test_no_references_means_no_fetch(monkeypatch, tmp_path):
    def boom(url: str, timeout: float | None = None) -> bytes:
        raise AssertionError("must not fetch without references")

    monkeypatch.setattr("src.processing.inherit.fetch_image", boom)

    assert resolve_inherited_prompts([_md(tmp_path, refs=[])]) == {}


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (None, "could not fetch"),
        (b"\xff\xd8\xff\xd9", "carries no recipe"),
        (_error_recipe_bytes(), "error placeholder"),
    ],
)
def test_unusable_first_reference_warns_and_skips(monkeypatch, tmp_path, data, reason):
    _patch_fetch(monkeypatch, data)
    sink = io.StringIO()
    sink_id = logger.add(sink, level="WARNING")
    try:
        assert resolve_inherited_prompts([_md(tmp_path)]) == {}
    finally:
        logger.remove(sink_id)
    assert reason in sink.getvalue()


def test_chain_from_an_already_inherited_file_keeps_the_original(monkeypatch, tmp_path):
    """An upres of an upres still records the original prompt (TLDR's chain)."""
    recipe = json.loads(_recipe_text())
    recipe["instruction"] = "upscale 1K to 4K"
    recipe["inherited_from"] = {"url": "https://b2/the-1k.png"}
    _patch_fetch(monkeypatch, _image_bytes(json.dumps(recipe)))
    md = _md(tmp_path)

    record = resolve_inherited_prompts([md])[str(md["path"])]

    assert record["prompt"]["raw"] == "the original prompt"


# ── composition ──────────────────────────────────────────────────────────────


def test_compose_payload_inherits_the_prompt_and_records_the_run(tmp_path):
    md = _md(tmp_path)
    ctx = _ctx(
        tmp_path,
        md,
        {"endpoint": "google/nano-banana-2", "parameters": {"resolution": "4K"}},
    )
    ctx.inherited = {
        str(md["path"]): {
            "prompt": {"raw": "the original prompt", "wrapped": "the original prompt"},
            "prefix": "",
            "suffix": "",
            "source": {"url": FIRST, "generated_at": "2026-10-01T10:00:00+00:00"},
        }
    }

    payload = compose_payload(ctx, md, tmp_path / "out.png")

    assert payload["schema"] == 1
    assert payload["prompt"]["raw"] == "the original prompt"
    assert payload["instruction"] == "upscale this to 4K"
    assert payload["inherited_from"] == {
        "url": FIRST,
        "generated_at": "2026-10-01T10:00:00+00:00",
    }
    assert payload["endpoint"] == "google/nano-banana-2"
    assert payload["parameters"] == {"resolution": "4K"}
    assert payload["reference_urls"] == [FIRST, SECOND]
    assert payload["output_file"] == "out.png"


def test_compose_without_inheritance_records_the_run_prompt(tmp_path):
    md = _md(tmp_path)
    ctx = _ctx(tmp_path, md, {"prompt_prefix": "P: "})

    payload = compose_payload(ctx, md, tmp_path / "out.png")

    assert payload["prompt"] == {"raw": "upscale this to 4K", "wrapped": "P: upscale this to 4K"}
    assert "instruction" not in payload
    assert "inherited_from" not in payload


# ── CLI surface ──────────────────────────────────────────────────────────────


def test_cli_flags_parse(monkeypatch):
    from src.cli import parse_args

    monkeypatch.setattr(sys, "argv", ["prog"])
    assert parse_args().inherit_prompt is None
    monkeypatch.setattr(sys, "argv", ["prog", "--inherit-prompt"])
    assert parse_args().inherit_prompt is True
    monkeypatch.setattr(sys, "argv", ["prog", "--no-inherit-prompt"])
    assert parse_args().inherit_prompt is False


def test_prepare_profile_cli_override_wins():
    import src.main_simple as main_simple

    args = SimpleNamespace(platform=None, force_png=False, inherit_prompt=None)
    assert main_simple._prepare_profile({"inherit_prompt": True}, args)["inherit_prompt"] is True
    assert "inherit_prompt" not in main_simple._prepare_profile({}, args)
    args.inherit_prompt = False
    assert main_simple._prepare_profile({"inherit_prompt": True}, args)["inherit_prompt"] is False
    args.inherit_prompt = True
    assert main_simple._prepare_profile({}, args)["inherit_prompt"] is True


# ── the pipeline ─────────────────────────────────────────────────────────────


def test_pipeline_stamps_the_inherited_prompt_but_sends_the_run_prompt(monkeypatch, tmp_path):
    """The engine still receives this run's own wording; only the stamped
    recipe inherits (the edit instruction is what the model must act on)."""
    import src.main_simple as main_simple

    class InputFile:
        def __init__(self, *, path, prompt, reference_urls, metadata):
            self.path = path
            self.prompt = prompt
            self.reference_urls = reference_urls
            self.metadata = metadata

    module = ModuleType("engine_replicate")
    module.InputFile = InputFile
    monkeypatch.setitem(sys.modules, "engine_replicate", module)

    input_dir = tmp_path / "in"
    input_dir.mkdir()
    md_path = input_dir / "up.md"
    md_path.write_text("upscale this to 4K\n![src](https://b2/first.png)\n", encoding="utf-8")
    md = {"path": md_path, "prompt": "upscale this to 4K", "reference_urls": [FIRST]}
    out_path = tmp_path / "out" / "up.png"

    _patch_fetch(monkeypatch, _image_bytes(_recipe_text()))

    recorded: dict = {}

    class RecordingEngine:
        PROVIDER_NAME = "stub-provider"

        def run(self, inputs):
            recorded["inputs"] = list(inputs)
            return [SimpleNamespace(status="ok", path=out_path, source_path=md_path)]

    ctx = PipelineContext(
        md_files=[md],
        engine=RecordingEngine(),
        platform="replicate",
        profile={
            "inherit_prompt": True,
            "endpoint": "google/nano-banana-2",
            "parameters": {"resolution": "4K"},
        },
        output_dir=tmp_path / "out",
        input_root=input_dir,
        save_payloads=True,
        logs=True,
        run_mode="studiolot",
    )

    captured: dict = {}
    monkeypatch.setattr(
        main_simple,
        "_run_with_progress",
        lambda ctx, inputs: (ctx.engine.run(inputs), set()),
    )
    monkeypatch.setattr(
        main_simple,
        "write_run_logs",
        lambda paths, out_dir, ctx, payloads, results: captured.update(payloads),
    )
    monkeypatch.setattr(main_simple, "write_placeholders", lambda *a, **k: [])
    monkeypatch.setattr(main_simple, "embed_payloads", lambda *a, **k: None)

    assert main_simple._execute_pipeline(ctx) == 0

    assert recorded["inputs"][0].prompt == "upscale this to 4K"
    payload = json.loads(next(iter(captured.values())))
    assert payload["prompt"]["raw"] == "the original prompt"
    assert payload["instruction"] == "upscale this to 4K"
    assert payload["inherited_from"]["url"] == FIRST
    assert payload["schema"] == 1


def test_failed_inheritance_marks_the_output_and_restamps(monkeypatch, tmp_path):
    """Outputs whose inheritance did not resolve gain the marker suffix, and a
    file stamped on its save event is re-stamped under the new name."""
    import src.main_simple as main_simple

    class InputFile:
        def __init__(self, *, path, prompt, reference_urls, metadata):
            self.path = path
            self.prompt = prompt
            self.reference_urls = reference_urls
            self.metadata = metadata

    module = ModuleType("engine_replicate")
    module.InputFile = InputFile
    monkeypatch.setitem(sys.modules, "engine_replicate", module)

    def fake_fetch(url: str, timeout: float | None = None) -> bytes | None:
        return _image_bytes(_recipe_text()) if url == FIRST else None

    monkeypatch.setattr("src.processing.inherit.fetch_image", fake_fetch)

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    md_ok = {"path": in_dir / "ok.md", "prompt": "upscale this", "reference_urls": [FIRST]}
    md_bad = {"path": in_dir / "bad.md", "prompt": "upscale this too", "reference_urls": [SECOND]}
    md_plain = {"path": in_dir / "plain.md", "prompt": "a castle", "reference_urls": []}

    ctx = PipelineContext(
        md_files=[md_ok, md_bad, md_plain],
        engine=_StagingStubEngine(tmp_path),
        platform="replicate",
        profile={"inherit_prompt": True, "endpoint": "x", "parameters": {}},
        output_dir=tmp_path,
        input_root=in_dir,
        save_payloads=True,
        logs=False,
        run_mode="studiolot",
    )

    assert main_simple._execute_pipeline(ctx) == 0

    ok_path = tmp_path / "ok-00.png"
    bad_path = tmp_path / "bad-01_PROMPT_INHERITANCE_FAILED.png"
    plain_path = tmp_path / "plain-02_PROMPT_INHERITANCE_FAILED.png"
    assert ok_path.exists()
    assert not (tmp_path / "bad-01.png").exists()
    assert bad_path.exists()
    assert plain_path.exists()

    inherited_payload = read_payload(ok_path)
    assert inherited_payload["instruction"] == "upscale this"
    assert inherited_payload["inherited_from"]["url"] == FIRST

    marked = read_payload(bad_path)
    assert marked["output_file"] == bad_path.name
    assert marked["prompt"]["raw"] == "upscale this too"
    assert "inherited_from" not in marked


def test_mark_failed_inheritance_is_best_effort(tmp_path):
    result = SimpleNamespace(
        status="ok", source_path=tmp_path / "gone.md", path=tmp_path / "gone-00.png"
    )

    mark_failed_inheritance([result], {str(tmp_path / "gone.md")}, set())

    assert result.path == tmp_path / "gone-00.png"
