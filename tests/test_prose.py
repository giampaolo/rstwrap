"""Tests for prose-paragraph wrapping behaviour."""

from rstwrap import wrap_rst

from . import BaseTest


class TestProseParagraphs(BaseTest):
    def test_long_paragraph_is_wrapped(self):
        src = (
            "This is a very long prose paragraph that clearly exceeds"
            " the default line length of seventy-nine characters and"
            " must therefore be wrapped.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_short_paragraph_unchanged(self):
        src = "Short paragraph.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_redundant_spaces_collapsed(self):
        src = "hello  world  foo.\n"
        out = self.wrap(src)
        assert "  " not in out
        self.check_all(src, out)

    def test_trailing_newline_preserved(self):
        src = "Some prose.\n"
        out = self.wrap(src)
        assert out.endswith("\n")
        self.check_all(src, out)

    def test_no_trailing_newline_preserved(self):
        src = "Some prose."
        out = self.wrap(src)
        assert not out.endswith("\n")
        self.check_all(src, out)

    def test_empty_string(self):
        assert self.wrap("") == ""

    def test_blank_lines_only(self):
        src = "\n\n\n"
        out = self.wrap(src)
        assert out == "\n"

    def test_multiple_blank_lines_collapsed(self):
        src = "Paragraph 1.\n\n\n\nParagraph 2.\n"
        out = self.wrap(src)
        assert out == "Paragraph 1.\n\nParagraph 2.\n"

    def test_multiline_paragraph_joined_and_wrapped(self):
        # Three short lines that together exceed the width must be
        # joined into one flow and re-wrapped.
        src = "word1 word2\nword3 word4\nword5 word6\n"
        out = self.wrap(src, width=10)
        for line in out.splitlines():
            assert len(line) <= 10
        self.assert_idempotent(src, width=10)

    def test_multiple_paragraphs_blank_line_preserved(self):
        src = "First paragraph.\n\nSecond paragraph.\n"
        out = self.wrap(src)
        assert "\n\n" in out
        self.check_all(src, out)

    def test_paragraph_stops_before_directive(self):
        # Prose followed by a directive: the directive line must not
        # be consumed into the paragraph.
        src = "Some prose.\n\n.. note::\n\n   A note.\n"
        out = self.wrap(src)
        assert ".. note::" in out
        self.check_all(src, out)

    def test_standalone_double_colon_not_merged(self):
        # A standalone '::' must stay on its own line.
        src = "Intro paragraph.\n\n::\n\n    literal block\n"
        out = self.wrap(src)
        assert "::\n" in out
        self.check_all(src, out)

    def test_single_letter_word_before_double_colon(self):
        # A single-letter word followed by :: near the wrap boundary.
        # The :: must not be separated from the preceding text.
        src = (
            "This paragraph has filler text to push a single-letter"
            " word near the wrap boundary, ending with x::\n"
            "\n"
            "    literal block\n"
        )
        out = self.wrap(src)
        assert "x::" in out
        assert "    literal block" in out
        self.check_all(src, out)

    def test_double_space_with_long_hyperlink_not_lengthened(self):
        # Paragraph with a double-space (triggers rewrap) + a hyperlink
        # split across lines -> unsplittable token >79 chars. Output
        # must not exceed the longest input line.
        src = (
            "See the `prebuilt versions are\n"
            "available <https://docs.python.org/dev/download.html>`_."
            "  Also see other stuff.\n"
        )
        out = self.wrap(src)
        max_src = max(len(x) for x in src.splitlines())
        max_out = max(len(x) for x in out.splitlines())
        assert max_out <= max_src
        self.check_all(src, out)

    def test_over_width_source_line_still_wrapped(self):
        # A single source line wider than WIDTH with an unsplittable
        # token in the middle: the tool wraps around the token, leaves
        # the token line over-width, and every other line fits WIDTH.
        src = (
            "This paragraph has plenty of wrappable prose around a"
            " very long inline hyperlink"
            " `label <https://example.com/"
            + ("x" * 120)
            + ">`_ and then continues with more plain words that"
            " should be wrapped normally.\n"
        )
        out = self.wrap(src)
        assert out != src  # did wrap (not verbatim passthrough)
        max_src = max(len(x) for x in src.splitlines())
        max_out = max(len(x) for x in out.splitlines())
        assert max_out <= max_src
        # Non-token lines all fit the target width.
        for line in out.splitlines():
            if "https://example.com" in line:
                continue
            assert len(line) <= self.WIDTH
        self.check_all(src, out)


class TestCollapseBlankLines(BaseTest):
    def test_simple_table_internal_blanks_preserved(self):
        # Simple-table indices are added to ``protected`` so internal
        # blank lines (between row groups) must survive collapse.
        src = (
            "======  =====\n"
            "Col A   Col B\n"
            "======  =====\n"
            "row 1   val 1\n"
            "\n"
            "\n"
            "row 2   val 2\n"
            "======  =====\n"
        )
        out = self.wrap(src)
        assert out == src

    def test_code_block_body_blanks_preserved(self):
        # Non-prose directive bodies are emitted verbatim. The outer
        # forward-lookahead heuristic preserves blanks because the
        # surrounding non-blank lines are indented.
        src = ".. code-block:: python\n\n   x = 1\n\n\n   y = 2\n"
        out = self.wrap(src)
        assert out == src

    def test_leading_blank_lines_collapsed(self):
        src = "\n\n\n\nABC\n"
        out = self.wrap(src)
        assert out == "\nABC\n"


class TestCRLF(BaseTest):
    def test_crlf_normalized_to_lf(self):
        """CRLF input is silently normalized to LF."""
        src = "Title\r\n=====\r\n\r\nHello world.\r\n"
        out = wrap_rst(src)
        assert "\r" not in out
        assert out == "Title\n=====\n\nHello world.\n"

    def test_crlf_long_paragraph(self):
        """CRLF input with a long paragraph wraps correctly."""
        src = (
            "This is a very long prose paragraph that clearly exceeds"
            " the default line length of seventy-nine characters and"
            " must therefore be wrapped.\r\n"
        )
        out = wrap_rst(src)
        assert "\r" not in out
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
