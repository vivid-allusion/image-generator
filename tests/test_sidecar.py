"""A non-picture output keeps its recipe in a stem-matched .md sidecar."""

import json
from pathlib import Path
from types import SimpleNamespace

from src.processing.markdown_parser import parse_markdown
from src.processing.payload import embed_payloads, stamp_file

TEXT = json.dumps(
    {
        "endpoint": "tripo3d/tripo/v2.5/image-to-3d",
        "parameters": {"texture": "HD"},
        "prompt": {"raw": "A hamburger"},
        "reference_urls": ["http://x/b.png"],
    }
)


def test_glb_gets_sidecar_readable_by_parser(tmp_path: Path) -> None:
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glTF....")
    stamp_file(glb, glb, TEXT)
    side = tmp_path / "m.md"
    body = side.read_text()
    assert "tripo3d/tripo/v2.5/image-to-3d" in body and "texture" in body
    assert parse_markdown(body) == ("A hamburger", ["http://x/b.png"])
    assert glb.read_bytes() == b"glTF...."


def test_staged_file_writes_sidecar_beside_final(tmp_path: Path) -> None:
    staged, final = tmp_path / ".m.glb.part", tmp_path / "m.glb"
    staged.write_bytes(b"glTF....")
    stamp_file(staged, final, TEXT)
    assert (tmp_path / "m.md").is_file() and not (tmp_path / ".m.md").exists()


def test_embed_payloads_writes_sidecar_without_error(tmp_path: Path) -> None:
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glTF....")
    embed_payloads([SimpleNamespace(status="ok", path=glb)], {str(glb): TEXT})
    assert (tmp_path / "m.md").is_file()


def test_sidecar_failure_does_not_abort(tmp_path: Path) -> None:
    a, b = tmp_path / "a.glb", tmp_path / "b.glb"
    a.write_bytes(b"glTF")
    b.write_bytes(b"glTF")
    (tmp_path / "a.md").mkdir()
    embed_payloads(
        [SimpleNamespace(status="ok", path=p) for p in (a, b)], {str(a): TEXT, str(b): TEXT}
    )
    assert (tmp_path / "b.md").is_file()
