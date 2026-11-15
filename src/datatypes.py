"""Shared type definitions for the application."""

from pathlib import Path
from typing import Any, NotRequired, TypedDict


class MarkdownFile(TypedDict):
    """A parsed .md file with its extracted data."""

    path: Path
    prompt: str
    reference_urls: list[str]
    settings: NotRequired[dict[str, Any]]  # accepted ```<setting> blocks, this file only
