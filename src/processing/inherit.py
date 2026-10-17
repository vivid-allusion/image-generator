"""Payload inheritance — an edit keeps the edited image's own recipe.

With a profile's ``inherit_prompt`` enabled, each Markdown file's *first*
reference image is fetched and its embedded recipe (if any) read back; the
source's prompt text, prefix and suffix then become the new file's prompt of
record. The run's own facts stay truthful — endpoint, parameters, timestamps
and file names still describe *this* run — the run's own wording is kept as
``instruction``, and the source image (URL, generation date, endpoint) is
recorded under ``inherited_from``.

Best effort by design: an unreachable reference, a foreign image, an error
placeholder, or a recipe without prompt text only logs a warning — that file
keeps its own prompt and the batch continues.
"""

import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from ..datatypes import MarkdownFile
from .payload import parse_payload_bytes

FETCH_TIMEOUT = 30.0
FETCH_WORKERS = 8
MAX_DOWNLOAD = 128 * 1024 * 1024
_USER_AGENT = "ImageGenerator/1.0"
INHERIT_FAILED_SUFFIX = "_PROMPT_INHERITANCE_FAILED"


def fetch_image(url: str, timeout: float = FETCH_TIMEOUT) -> bytes | None:
    """Best-effort GET of one reference image; None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(MAX_DOWNLOAD)
    except Exception as e:
        logger.debug(f"Inherit fetch failed for {url}: {type(e).__name__}: {e}")
        return None


def resolve_inherited_prompts(md_files: list[MarkdownFile]) -> dict[str, dict[str, Any]]:
    """Fetch each file's first reference and read its recipe, keyed by md path.

    Files without references are skipped (debug): there is nothing to inherit
    from, and their own prompt is already correct. A first reference that
    fails to fetch, carries no recipe, is an error placeholder, or has no
    prompt text warns once and is absent from the result, so that file keeps
    its own prompt. Fetches run in a bounded pool (mirrors
    ``validate_image_urls``).
    """
    targets = []
    for md in md_files:
        if md["reference_urls"]:
            targets.append(md)
        else:
            logger.debug(f"Inherit skipped for {md['path'].name}: no reference images")
    if not targets:
        logger.warning("inherit_prompt is on but no Markdown file has reference images")
        return {}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        records = list(pool.map(_inherit_one, targets))
    inherited: dict[str, dict[str, Any]] = {}
    for md, record in zip(targets, records):
        if record is not None:
            inherited[str(md["path"])] = record
            logger.debug(f"Inherited prompt from {record['source']['url']} for {md['path'].name}")
    return inherited


def _inherit_one(md_file: MarkdownFile) -> dict[str, Any] | None:
    """Resolve one file's inherited-prompt record, or None (with a warning)."""
    url = md_file["reference_urls"][0]
    name = md_file["path"].name
    data = fetch_image(url)
    if data is None:
        logger.warning(f"Inherit prompt skipped for {name}: could not fetch {url}")
        return None
    recipe = parse_payload_bytes(data)
    if not recipe:
        logger.warning(f"Inherit prompt skipped for {name}: {url} carries no recipe")
        return None
    if recipe.get("error"):
        logger.warning(f"Inherit prompt skipped for {name}: {url} is an error placeholder")
        return None
    record = _record(url, recipe)
    if record is None:
        logger.warning(f"Inherit prompt skipped for {name}: {url} recipe has no prompt text")
    return record


def _record(url: str, recipe: dict[str, Any]) -> dict[str, Any] | None:
    """Build the inherited-prompt record, or None when the recipe has no text."""
    prompt = recipe.get("prompt")
    raw = prompt.get("raw") if isinstance(prompt, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    prefix = str(recipe.get("prefix", "") or "")
    suffix = str(recipe.get("suffix", "") or "")
    wrapped = str(prompt.get("wrapped") or f"{prefix}{raw}{suffix}".strip())
    source: dict[str, Any] = {"url": url}
    for key in ("generated_at", "endpoint"):
        value = recipe.get(key)
        if value:
            source[key] = value
    return {
        "prompt": {"raw": raw, "wrapped": wrapped},
        "prefix": prefix,
        "suffix": suffix,
        "source": source,
    }


def mark_failed_inheritance(results: list[Any], failed: set[str], stamped: set[str]) -> None:
    """Suffix each generated file whose prompt inheritance did not resolve.

    Renames the file in place *before* payload composition, so the recipe's
    ``output_file`` records the final (suffixed) name; a path stamped during
    its save event is un-skipped so the end-of-run pass re-stamps it under the
    new name (the inject merge preserves cull marks). Best effort: a rename
    that cannot happen only warns — except a file that is already gone (moved
    out of the output folder), which stays silent like the payload pass.
    """
    if not failed:
        return
    for result in results:
        if getattr(result, "status", "") != "ok" or getattr(result, "path", None) is None:
            continue
        if str(getattr(result, "source_path", "")) not in failed:
            continue
        old = result.path
        new = old.with_name(old.stem + INHERIT_FAILED_SUFFIX + old.suffix)
        if not old.exists():
            logger.debug(f"Inheritance marker skipped for {old.name}: file no longer present")
            continue
        if new.exists():
            logger.warning(f"Inheritance marker skipped for {old.name}: {new.name} exists")
            continue
        try:
            old.rename(new)
        except OSError as exc:
            logger.warning(f"Inheritance marker failed for {old.name}: {exc}")
            continue
        result.path = new
        stamped.discard(str(old))
