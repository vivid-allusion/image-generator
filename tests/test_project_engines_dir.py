from pathlib import Path

from src.engine_helpers import find_project_engines_dir


def test_finds_new_project_layout(tmp_path: Path) -> None:
    engines = tmp_path / ".00_TOOLS" / "GENERATORS" / "ENGINES"
    engines.mkdir(parents=True)
    out = tmp_path / "09_OUTPUT"
    out.mkdir()
    assert find_project_engines_dir(out) == engines.resolve()


def test_still_finds_old_layout(tmp_path: Path) -> None:
    engines = tmp_path / "00_APPLICATIONS" / "ENGINES"
    engines.mkdir(parents=True)
    assert find_project_engines_dir(tmp_path) == engines.resolve()
