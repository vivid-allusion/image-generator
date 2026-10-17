"""Tests for markdown_parser module."""

import io

from loguru import logger

from src.processing.markdown_parser import (
    extract_all_image_urls,
    extract_prompt_text,
    parse_markdown,
    read_markdown_files,
    validate_image_urls,
)


class TestExtractPromptText:
    def test_single_line_prompt(self):
        content = "A man carries bags.\n![image](https://example.com/img.jpg)"
        assert extract_prompt_text(content) == "A man carries bags."

    def test_first_non_empty_line(self):
        content = "\n\nHello world\n![img](https://x.com/a.jpg)"
        assert extract_prompt_text(content) == "Hello world"

    def test_empty_content_returns_empty_prompt(self):
        assert extract_prompt_text("") == ""

    def test_whitespace_only_returns_empty_prompt(self):
        assert extract_prompt_text("   \n   \n") == ""


class TestPromptFence:
    """A ```prompt / ``` block is the prompt; its contents may be empty."""

    def test_fenced_prompt_single_line(self):
        content = "```prompt\nA man carries bags.\n```\n![ref](https://host/ref.jpg)"
        assert extract_prompt_text(content) == "A man carries bags."
        assert extract_all_image_urls(content) == ["https://host/ref.jpg"]

    def test_fence_without_the_word_prompt(self):
        content = "```\nA man carries bags.\n```\n![ref](https://host/ref.jpg)"
        assert extract_prompt_text(content) == "A man carries bags."
        assert extract_all_image_urls(content) == ["https://host/ref.jpg"]

    def test_fenced_prompt_multiple_lines(self):
        content = "```prompt\nLine one\n\nLine two\n```"
        assert extract_prompt_text(content) == "Line one\n\nLine two"

    def test_empty_fence_keeps_references(self):
        content = "```prompt\n```\n\n![ref](https://host/1k.png)\n![ref2](https://host/other.png)"
        assert extract_prompt_text(content) == ""
        assert extract_all_image_urls(content) == [
            "https://host/1k.png",
            "https://host/other.png",
        ]

    def test_empty_bare_fence(self):
        content = "```\n```\n![ref](https://host/1k.png)"
        assert extract_prompt_text(content) == ""
        assert extract_all_image_urls(content) == ["https://host/1k.png"]

    def test_fence_after_a_bookmark_render(self):
        content = (
            "![render](https://host/prev.png)\n"
            "```prompt\nA prompt\n```\n"
            "![ref](https://host/ref.jpg)"
        )
        assert extract_prompt_text(content) == "A prompt"
        assert extract_all_image_urls(content) == ["https://host/ref.jpg"]

    def test_unclosed_fence_is_warned_and_ignored(self):
        content = "```prompt\nA prompt\n![ref](https://host/ref.jpg)"
        warnings: list[str] = []
        prompt, urls = parse_markdown(content, warn=warnings.append)
        assert prompt == "A prompt"
        assert urls == ["https://host/ref.jpg"]
        assert any("unclosed" in w for w in warnings)

    def test_unclosed_fence_with_only_a_reference(self):
        content = "```prompt\n![ref](https://host/ref.jpg)"
        warnings: list[str] = []
        prompt, urls = parse_markdown(content, warn=warnings.append)
        assert prompt == ""
        assert urls == ["https://host/ref.jpg"]
        assert any("unclosed" in w for w in warnings)


class TestEmptyPromptFiles:
    """No text anywhere: empty prompt, every image embed is a reference."""

    def test_empty_line_then_reference(self):
        content = "\n![ref](https://host/1k.png)"
        assert extract_prompt_text(content) == ""
        assert extract_all_image_urls(content) == ["https://host/1k.png"]

    def test_only_references(self):
        content = "![a](https://host/a.png)\n![b](https://host/b.png)"
        assert extract_prompt_text(content) == ""
        assert extract_all_image_urls(content) == ["https://host/a.png", "https://host/b.png"]

    def test_whitespace_only_file_collects_nothing(self):
        assert extract_all_image_urls("   \n   \n") == []


class TestExtractAllImageUrls:
    def test_markdown_image_syntax(self):
        content = "Prompt\n![a](https://example.com/1.jpg)\n![b](https://example.com/2.jpg)"
        urls = extract_all_image_urls(content)
        assert urls == ["https://example.com/1.jpg", "https://example.com/2.jpg"]

    def test_raw_urls(self):
        content = "Prompt\nhttps://example.com/img.png\nhttps://other.com/photo.jpg"
        urls = extract_all_image_urls(content)
        assert urls == ["https://example.com/img.png", "https://other.com/photo.jpg"]

    def test_mixed_markdown_and_raw(self):
        content = "P\n![x](https://a.com/1.jpg)\nhttps://b.com/2.png"
        urls = extract_all_image_urls(content)
        assert urls == ["https://a.com/1.jpg", "https://b.com/2.png"]

    def test_no_urls_returns_empty_list(self):
        urls = extract_all_image_urls("Just a prompt\nNothing else")
        assert urls == []

    def test_html_commented_image_ignored(self):
        content = (
            "Prompt\n"
            "![a](https://example.com/1.jpg)\n"
            "<!-- ![b](https://example.com/2.jpg) -->\n"
        )
        urls = extract_all_image_urls(content)
        assert urls == ["https://example.com/1.jpg"]

    def test_html_comment_multiline_ignored(self):
        content = (
            "Prompt\n"
            "<!--\n![a](https://example.com/1.jpg)\n![b](https://example.com/2.jpg)\n-->\n"
            "![c](https://example.com/3.jpg)\n"
        )
        urls = extract_all_image_urls(content)
        assert urls == ["https://example.com/3.jpg"]

    def test_html_commented_raw_url_ignored(self):
        content = "Prompt\n<!-- https://example.com/1.jpg -->\nhttps://example.com/2.jpg"
        urls = extract_all_image_urls(content)
        assert urls == ["https://example.com/2.jpg"]

    def test_url_with_brackets_in_path(self):
        content = (
            "Prompt\n"
            "![img](https://host/FS_Ferenc_Sz%C3%A1lasi/Ferenc_Sz%C3%A1lasi_(3x4_cropped).png)\n"
            "![img](https://host/FS_Ferenc_Sz%C3%A1lasi/images_(1).png)\n"
        )
        assert extract_all_image_urls(content) == [
            "https://host/FS_Ferenc_Sz%C3%A1lasi/Ferenc_Sz%C3%A1lasi_(3x4_cropped).png",
            "https://host/FS_Ferenc_Sz%C3%A1lasi/images_(1).png",
        ]

    def test_non_ascii_url_is_percent_encoded(self):
        content = "Prompt\n![img](https://host/FS_Ferenc_Szálasi/i.png)"
        assert extract_all_image_urls(content) == [
            "https://host/FS_Ferenc_Sz%C3%A1lasi/i.png"
        ]

    def test_already_encoded_url_is_unchanged(self):
        url = "https://host/FS_Ferenc_Sz%C3%A1lasi/images_(3).png"
        assert extract_all_image_urls(f"Prompt\n![img]({url})") == [url]


class TestExtractPromptTextWithComments:
    def test_commented_first_line_becomes_empty(self):
        content = "<!-- Old prompt -->\nNew prompt\n![x](https://a.com/1.jpg)"
        assert extract_prompt_text(content) == "New prompt"


class TestLeadingImageBookmarkIgnored:
    """A leading markdown image (previous generation) is not the prompt."""

    def test_relative_image_on_line_1_ignored(self):
        content = (
            "![generated](../05.OUTPUT/261010_203922_IMG/261010_203949-0077-1.png)\n"
            "\n"
            "1944, a snowless winter plain on the Eastern Front in Hungary."
        )
        assert (
            extract_prompt_text(content)
            == "1944, a snowless winter plain on the Eastern Front in Hungary."
        )

    def test_remote_image_on_line_1_ignored(self):
        content = "![img](https://host/a.png)\nThe actual prompt"
        assert extract_prompt_text(content) == "The actual prompt"
        assert extract_all_image_urls(content) == []

    def test_reference_below_prompt_still_collected(self):
        content = "![generated](../out/prev.png)\nThe actual prompt\n![ref](https://host/ref.jpg)"
        assert extract_all_image_urls(content) == ["https://host/ref.jpg"]

    def test_multiple_leading_images_skipped(self):
        content = "![a](../a.png)\n![b](https://host/b.png)\nPrompt"
        assert extract_prompt_text(content) == "Prompt"

    def test_text_line_with_inline_image_still_prompt(self):
        content = (
            "Make a poster with ![logo](https://host/logo.png) in the corner\n"
            "![ref](https://host/x.jpg)"
        )
        assert (
            extract_prompt_text(content)
            == "Make a poster with ![logo](https://host/logo.png) in the corner"
        )

    def test_only_an_image_returns_empty_prompt_and_is_a_reference(self):
        content = "![generated](https://host/img.png)"
        assert extract_prompt_text(content) == ""
        assert extract_all_image_urls(content) == ["https://host/img.png"]


class TestValidateImageUrls:
    def test_non_ascii_url_is_encoded_before_request(self, monkeypatch):
        seen = {}

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(req, timeout=None):
            seen["url"] = req.full_url
            return FakeResponse()

        monkeypatch.setattr(
            "src.processing.markdown_parser.urllib.request.urlopen", fake_urlopen
        )
        raw = "https://host/FS_Ferenc_Szálasi/i.png"
        valid, invalid = validate_image_urls([raw])

        assert valid == [raw]
        assert invalid == []
        assert seen["url"] == "https://host/FS_Ferenc_Sz%C3%A1lasi/i.png"


class TestReadMarkdownFiles:
    def test_natural_sort_order(self, tmp_path):
        for name in ["2_rw.md", "10_rw.md", "1_rw.md", "100_rw.md"]:
            (tmp_path / name).write_text("prompt\n", encoding="utf-8")

        files = read_markdown_files(tmp_path)
        assert [f["path"].name for f in files] == [
            "1_rw.md",
            "2_rw.md",
            "10_rw.md",
            "100_rw.md",
        ]


class TestReadMarkdownFilesValidation:
    """Fail-loud contract: Markdown files with unreachable media URLs are rejected."""

    def test_pure_text_markdown_needs_no_validation(self, tmp_path, monkeypatch):
        (tmp_path / "t2i.md").write_text("a sunset over the bay\n", encoding="utf-8")
        called = []
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: called.append(urls) or ([], []),
        )
        files = read_markdown_files(tmp_path)
        assert len(files) == 1
        assert files[0]["reference_urls"] == []
        assert called == []  # no URLs -> no reachability checks

    def test_all_urls_unreachable_rejects_markdown(self, tmp_path, monkeypatch):
        (tmp_path / "dead.md").write_text(
            "prompt\n![x](https://dead.example/1.jpg)\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: ([], list(urls)),
        )
        assert read_markdown_files(tmp_path) == []

    def test_partial_unreachable_rejects_markdown(self, tmp_path, monkeypatch):
        (tmp_path / "half.md").write_text(
            "prompt\n![a](https://ok.example/1.jpg)\n![b](https://dead.example/2.jpg)\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: ([urls[0]], [urls[1]]),
        )
        assert read_markdown_files(tmp_path) == []

    def test_all_urls_reachable_keeps_markdown(self, tmp_path, monkeypatch):
        (tmp_path / "ok.md").write_text(
            "prompt\n![a](https://ok.example/1.jpg)\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: (list(urls), []),
        )
        files = read_markdown_files(tmp_path)
        assert len(files) == 1
        assert files[0]["reference_urls"] == ["https://ok.example/1.jpg"]


class TestReadMarkdownFilesEmptyPrompt:
    """Empty prompts: rejected by default, admitted when the profile carries text."""

    def test_empty_prompt_rejected_without_a_profile_prefix(self, tmp_path):
        (tmp_path / "up.md").write_text(
            "```prompt\n```\n![ref](https://ok.example/1.jpg)\n", encoding="utf-8"
        )
        sink = io.StringIO()
        sink_id = logger.add(sink, level="ERROR")
        try:
            assert read_markdown_files(tmp_path) == []
        finally:
            logger.remove(sink_id)
        assert "Rejected up.md" in sink.getvalue()

    def test_empty_prompt_admitted_with_the_flag_and_refs_kept(self, tmp_path, monkeypatch):
        (tmp_path / "up.md").write_text(
            "```prompt\n```\n![ref](https://ok.example/1.jpg)\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: (list(urls), []),
        )
        files = read_markdown_files(tmp_path, allow_empty_prompt=True)
        assert len(files) == 1
        assert files[0]["prompt"] == ""
        assert files[0]["reference_urls"] == ["https://ok.example/1.jpg"]

    def test_ref_only_file_keeps_its_reference(self, tmp_path, monkeypatch):
        (tmp_path / "only-ref.md").write_text(
            "![ref](https://ok.example/1.jpg)\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            "src.processing.markdown_parser.validate_image_urls",
            lambda urls, timeout=5.0, workers=8: (list(urls), []),
        )
        files = read_markdown_files(tmp_path, allow_empty_prompt=True)
        assert len(files) == 1
        assert files[0]["prompt"] == ""
        assert files[0]["reference_urls"] == ["https://ok.example/1.jpg"]

    def test_ref_only_file_rejected_without_the_flag(self, tmp_path):
        (tmp_path / "only-ref.md").write_text(
            "![ref](https://ok.example/1.jpg)\n", encoding="utf-8"
        )
        assert read_markdown_files(tmp_path) == []
