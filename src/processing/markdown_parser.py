"""
Markdown parsing utilities for extracting image URLs and prompts.

This module provides functions to parse markdown files and extract:
- Image URLs from any line (markdown ![alt](URL) or raw https:// URL)
- Text prompt from the first non-empty line that is not a markdown image

Format:
    Line 1: Text prompt, or a ```prompt / ``` fenced block (its contents may
            be empty when the profile's prefix/suffix carries the run)
    Lines after: ![image](URL) or https://...  (multiple images supported)

A leading line that is nothing but a markdown image — e.g. the previous
generation embedded by tooling as a visual bookmark — is ignored; the prompt
is then taken from the next non-empty text line. When the file carries no
prompt at all, every image embed is a reference (nothing is a bookmark).

PRD Reference: Section 05.1, 06.2
"""

import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger

from ..datatypes import MarkdownFile

# A URL path can itself contain brackets (…_(3x4_cropped).png), so the URL body
# allows balanced "(…)" groups instead of stopping at the first ")".
_URL_BODY = r"[^\s()]*(?:\([^\s()]*\)[^\s()]*)*"
# Never encode these: % keeps already-encoded URLs stable, brackets are legal in a path.
_URL_SAFE = ":/?#[]@!$&'()*+,;=%~"
_IMG_URL_PATTERN = re.compile(rf"!\[.*?\]\((https?://{_URL_BODY})\)")
# A whole line that is nothing but a markdown image embed, scheme-agnostic:
# relative targets (../05.OUTPUT/…) count as images too. Used to ignore a
# leading generated-image bookmark when looking for the prompt.
_MD_IMAGE_LINE = re.compile(rf"!\[.*?\]\({_URL_BODY}\)")
_LINK_WITHOUT_BANG = re.compile(r"(?<!!)\[.*?\]\((https?://[^\)]+)\)")
_BANG_SPACE_PATTERN = re.compile(r"! +\[.*?\]\(.*?\)")
_PAREN_SPACE_PATTERN = re.compile(r"!\[.*?\] +\(.*?\)")
_SWAPPED_PATTERN = re.compile(r"!\[(https?://[^\]]+)\]\([^\)]+\)")
_UNCLOSED_PATTERN = re.compile(r"!\[.*?\]\([^\)]*$")
_HTML_IMG_PATTERN = re.compile(r"<img[^>]*src\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_NON_HTTP_URL = re.compile(
    r"!\[.*?\]\((?!https?://)(\.\.?/|\.\.?\\|//|/|data:|file:|ftp:|[A-Za-z]:\\|\w+://)[^\)]+\)"
)
_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
_STUDIO_FENCE = re.compile(r"^---\s*$")
_STUDIO_ROOT_KEY = re.compile(r"^studio:\s*(?:#.*)?$")
# An opening prompt fence: "```prompt" or a bare "```".
_PROMPT_FENCE = re.compile(r"^```(?:\s*prompt)?\s*$", re.IGNORECASE)


def _is_studio_root(line: str) -> bool:
    """True when a line is a column-zero `studio:` marks root key."""
    return not line[:1].isspace() and bool(_STUDIO_ROOT_KEY.match(line.strip()))


def _studio_block_start(lines: list[str]) -> int | None:
    """Index of the opening fence of a trailing `studio:` markdown block.

    The IDE appends its cull marks as a `---`-fenced YAML block whose root key
    is `studio:`. The block is metadata, not prompt or URL, so the parser skips
    it whole. A fence is only recognised when the next non-blank line is the
    root key at column zero, so a plain horizontal rule is never swallowed. No
    YAML is parsed: a malformed block is skipped without error.
    """
    for index, line in enumerate(lines):
        if not _STUDIO_FENCE.match(line.strip()):
            continue
        following = next((candidate for candidate in lines[index + 1 :] if candidate.strip()), None)
        if following is not None and _is_studio_root(following):
            return index
    return None


def _check_line(line: str, lineno: int, warn: Callable[[str], None] | None) -> None:
    """Inspect a line for common image-embed formatting mistakes."""
    if warn is None:
        return

    if _BANG_SPACE_PATTERN.search(line):
        warn(f"Line {lineno}: space between '!' and '[' — use ![alt](URL) not ! [alt](URL)")

    if _PAREN_SPACE_PATTERN.search(line):
        warn(f"Line {lineno}: space before '(' — use ![alt](URL) not ![alt] (URL)")

    if _SWAPPED_PATTERN.search(line):
        warn(f"Line {lineno}: URL and alt text appear swapped. Use ![alt](URL), not ![URL](alt)")

    if _UNCLOSED_PATTERN.search(line):
        warn(f"Line {lineno}: unclosed parenthesis — missing ')' after URL")

    if _LINK_WITHOUT_BANG.search(line):
        warn(f"Line {lineno}: missing '!' prefix — use ![alt](URL) not [alt](URL)")

    if _HTML_IMG_PATTERN.search(line):
        warn(f"Line {lineno}: HTML <img> tag found. Use markdown ![alt](URL) instead")

    if _NON_HTTP_URL.search(line):
        warn(
            f"Line {lineno}: image URL does not start with https:// — "
            "only remote URLs are supported"
        )


def _normalize_url(url: str) -> str:
    """Percent-encode characters that are illegal in a URL (spaces, non-ASCII).

    Idempotent: an already-encoded URL (e.g. ``%C3%A1``) is returned unchanged.
    Brackets stay literal — they are legal in a path and the image hosts serve
    them either way.
    """
    return urllib.parse.quote(url, safe=_URL_SAFE)


def _scan_prompt(lines: list[str], warn: Callable[[str], None] | None) -> tuple[int, str, bool]:
    """Locate the prompt; return (index after it, prompt text, prompt found).

    Skips blank lines and whole-line image embeds (a leading bookmark). A
    ```prompt / ``` fence opens a block: its contents are the prompt (empty
    allowed) and the scan resumes after the closing fence. A fence with no
    closing line is warned about and ignored, so a text line below it can
    still become the prompt. When nothing is found, the caller treats every
    image embed as a reference.
    """
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or _MD_IMAGE_LINE.fullmatch(stripped):
            continue
        if _PROMPT_FENCE.match(stripped):
            close = next(
                (i for i in range(index + 1, len(lines)) if lines[i].strip() == "```"),
                None,
            )
            if close is None:
                if warn is not None:
                    warn(f"Line {index + 1}: unclosed ```prompt fence — ignored")
                continue
            prompt = "\n".join(lines[index + 1 : close]).strip()
            return close + 1, prompt, True
        return index + 1, stripped, True
    return len(lines), "", False


def parse_markdown(
    markdown_content: str, warn: Callable[[str], None] | None = None
) -> tuple[str, list[str]]:
    """Parse a .md file, returning (prompt, image_urls) in one pass.

    The prompt is the first non-empty text line, or the contents of a leading
    ```prompt / ``` fenced block (which may be empty). A file with no text at
    all — only image embeds — parses as an empty prompt with those embeds as
    its references; the profile's prefix/suffix then carries the run.

    Args:
        markdown_content: Full markdown file content
        warn: Optional callback for format warnings (e.g. logger.warning)

    Returns:
        Tuple of (prompt_text, list_of_image_urls); the prompt may be empty.
    """
    markdown_content = _HTML_COMMENT_PATTERN.sub("", markdown_content)
    lines = markdown_content.split("\n")
    skip_from = _studio_block_start(lines)
    if skip_from is not None:
        lines = lines[:skip_from]

    index, prompt, seen_prompt = _scan_prompt(lines, warn)
    if not seen_prompt:
        # No prompt anywhere: nothing is a bookmark, every embed is a reference.
        index = 0

    urls: list[str] = []
    for lineno, line in enumerate(lines[index:], start=index + 1):
        stripped = line.strip()
        if not stripped:
            continue

        match = _IMG_URL_PATTERN.search(line)
        if match:
            urls.append(_normalize_url(match.group(1)))
        elif stripped.startswith("http://") or stripped.startswith("https://"):
            urls.append(_normalize_url(stripped))
        else:
            _check_line(line, lineno, warn)

    return prompt, urls


def extract_prompt_text(markdown_content: str) -> str:
    """Extract the prompt text from the first text line or fenced block.

    Returns an empty string when the file carries no prompt text, so the
    profile's prefix/suffix can carry the run.
    """
    prompt, _ = parse_markdown(markdown_content)
    return prompt


def extract_all_image_urls(
    markdown_content: str, warn: Callable[[str], None] | None = None
) -> list[str]:
    """Extract all image URLs from markdown content, preserving order."""
    _, urls = parse_markdown(markdown_content, warn=warn)
    return urls


def validate_image_urls(
    urls: list[str], timeout: float = 5.0, workers: int = 8
) -> tuple[list[str], list[str]]:
    """Validate image URLs are reachable via HEAD request.

    Checks run concurrently (bounded pool); result order is preserved.

    Args:
        urls: List of image URLs to check.
        timeout: Seconds per request.
        workers: Max concurrent HEAD requests.

    Returns:
        Tuple of (valid_urls, invalid_urls). Invalid URLs are stripped.
    """
    headers = {"User-Agent": "ImageGenerator/1.0"}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        checks = list(pool.map(lambda url: _check_url(url, headers, timeout), urls))
    valid = [url for url, ok in zip(urls, checks) if ok]
    invalid = [url for url, ok in zip(urls, checks) if not ok]
    return valid, invalid


def _check_url(url: str, headers: dict[str, str], timeout: float) -> bool:
    """Return True when url answers a HEAD request below 400."""
    try:
        req = urllib.request.Request(
            _normalize_url(url), method="HEAD", headers=headers
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception as e:
        logger.debug(f"URL check failed for {url}: {type(e).__name__}: {e}")
        return False


def _natural_sort_key(path: Path) -> list[str | int]:
    """Split a filename into digit/non-digit chunks for natural sorting."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.name)]


def read_markdown_files(input_dir: Path, allow_empty_prompt: bool = False) -> list[MarkdownFile]:
    """Read .md files from input_dir, extract prompt + reference URLs.

    ``allow_empty_prompt`` admits files with no prompt text (an empty fence,
    or image embeds only): the profile's prefix/suffix then carries the run.
    Without it, such a file is rejected — loud, never a silent empty request.
    """
    md_files = sorted(input_dir.rglob("*.md"), key=_natural_sort_key)
    result: list[MarkdownFile] = []
    rejected = 0
    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")
        prompt, urls = parse_markdown(content, warn=logger.warning)
        if not prompt:
            if not allow_empty_prompt:
                logger.error(
                    f"Rejected {md_path.name}: no prompt text and the profile has no "
                    "prompt prefix/suffix to carry the run"
                )
                rejected += 1
                continue
            logger.debug(
                f"{md_path.name}: empty prompt — the profile's prefix/suffix carries the run"
            )
        if urls:
            valid, invalid = validate_image_urls(urls)
            if invalid:
                # Fail loud: a Markdown file that declared media references with
                # unreachable URLs is rejected, never silently downgraded to
                # text-to-image (that changed the author's intent). Parity
                # with video-generator's markdown_parser, which rejects too.
                logger.error(
                    f"Rejected {md_path.name}: {len(invalid)} of {len(urls)} "
                    "media URL(s) unreachable"
                )
                rejected += 1
                continue
        result.append({"path": md_path, "prompt": prompt, "reference_urls": urls})
    if rejected and not result:
        logger.error(f"All {rejected} Markdown file(s) rejected — nothing to generate")
    if not result:
        logger.warning(f"No .md files found in {input_dir}")
        return result
    sys.stderr.write(f"Discovered {len(result)} markdown file(s) in {input_dir}\n")
    return result


def index_md_files(md_files: list[MarkdownFile]) -> dict[str, MarkdownFile]:
    """Map absolute markdown path strings to their parsed files."""
    return {str(md["path"]): md for md in md_files}
