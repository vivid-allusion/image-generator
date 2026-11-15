"""Per-file ```<setting> blocks: parsed out of the prompt, checked against the model's endpoint file."""

from pathlib import Path

import pytest

from src.processing.markdown_parser import parse_markdown, read_markdown_files
from src.processing.settings_blocks import resolve_settings

PARAMS = {
    "aspect_ratio": {"type": "select", "options": [{"value": "16:9"}, {"value": "9:16"}]},
    "resolution": {"type": "select", "options": [{"value": "2K"}, {"value": "4K"}]},
}
TOML = """endpoint = "acme/model"
[params.aspect_ratio]
type = "select"
options = [{ value = "16:9" }, { value = "9:16" }]
"""


def _engines(tmp_path: Path) -> Path:
    d = tmp_path / "ENGINES" / "engine-acme" / "engine_acme" / "endpoints" / "IMG-Models"
    d.mkdir(parents=True)
    (d / "model.toml").write_text(TOML)
    return tmp_path / "ENGINES"


def test_blocks_leave_the_prompt_alone() -> None:
    found: dict[str, str] = {}
    prompt, urls = parse_markdown(
        "A heron.\n\n```aspect_ratio\n\n9:16\n```\n\n```resolution\n4K\n```\n", settings=found
    )
    assert prompt == "A heron."
    assert urls == []
    assert found == {"aspect_ratio": "9:16", "resolution": "4K"}


def test_block_inside_a_prompt_fence_stays_prompt() -> None:
    found: dict[str, str] = {}
    prompt, _ = parse_markdown("```prompt\nhi\n```size\n1\n```\n", settings=found)
    assert found == {}
    assert "hi" in prompt


def test_resolve_accepts_option_and_refuses_others() -> None:
    assert resolve_settings({"resolution": "4K"}, PARAMS) == {"resolution": "4K"}
    with pytest.raises(ValueError, match="aspect_ratio.*5:2"):
        resolve_settings({"aspect_ratio": "5:2"}, PARAMS)
    with pytest.raises(ValueError, match="size"):
        resolve_settings({"size": "1024x1024"}, PARAMS)
    with pytest.raises(ValueError, match="endpoint file"):
        resolve_settings({"size": "1"}, None)


def test_read_rejects_bad_files_and_keeps_good_ones(tmp_path: Path) -> None:
    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "a_ok.md").write_text("Fox.\n\n```aspect_ratio\n9:16\n```\n")
    (tmp_path / "in" / "b_bad.md").write_text("Owl.\n\n```aspect_ratio\n5:2\n```\n")
    (tmp_path / "in" / "c_plain.md").write_text("Boat.\n")
    profile = {"platform": "acme", "endpoint": "acme/model"}
    files = read_markdown_files(tmp_path / "in", profile=profile, search_paths=[_engines(tmp_path)])
    assert [(f["path"].name, f["settings"]) for f in files] == [
        ("a_ok.md", {"aspect_ratio": "9:16"}),
        ("c_plain.md", {}),
    ]
