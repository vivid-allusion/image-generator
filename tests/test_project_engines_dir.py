from pathlib import Path

import src.main_simple as main_simple
from src.engine_helpers import find_generator_engines_dir, find_project_engines_dir


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


def test_falls_back_to_generator_engines(tmp_path: Path, monkeypatch) -> None:
    seen: list[list[Path]] = []
    monkeypatch.setattr(
        main_simple, "_load_engine_with_ctx", lambda _p, paths, *_a: seen.append(paths)
    )
    main_simple._resolve_engine_for_studiolot(tmp_path, "fal", {}, None)
    assert seen == [[find_generator_engines_dir()]]
