"""Tests for prose-paragraph wrapping behaviour."""

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
        assert out == src

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

    def test_double_space_with_long_hyperlink_not_lengthened(self):
        # A paragraph with a double-space (which triggers rewrap) that also
        # contains a hyperlink whose display text was split across lines.
        # Joining produces an un-splittable token >79 chars; the tool must
        # not produce an output line longer than the longest input line.
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
