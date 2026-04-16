"""Tests for the opt-in ``join=True`` short-line merge mode."""

import rst_wrap_lines

from . import BaseTest


class TestJoin(BaseTest):
    """Exercise the opt-in ``join=True`` mode: short consecutive lines
    inside a paragraph are merged onto one (up to the target width).
    """

    JOIN = True

    def test_short_lines_joined(self):
        # Classic case: three one-word lines merge into a single line.
        src = "foo\nbar\nzoo\n"
        out = self.wrap(src)
        assert out == "foo bar zoo\n"

    def test_multiline_paragraph_merged(self):
        # Pre-wrapped prose that already fits is still merged so short
        # lines join (up to the target width).
        src = "Short line one.\nShort line two.\nShort line three.\n"
        out = self.wrap(src)
        # All three lines fit on one at width 79.
        assert out == "Short line one. Short line two. Short line three.\n"

    def test_paragraph_boundaries_preserved(self):
        # Two paragraphs separated by a blank line must not be joined.
        src = "foo\nbar\n\nbaz\nqux\n"
        out = self.wrap(src)
        assert out == "foo bar\n\nbaz qux\n"

    def test_short_section_underline_preserved(self):
        # A 2-char section underline (``io\n--``) must not merge with
        # its title in join mode.
        src = "io\n--\n\nSome text.\n"
        out = self.wrap(src)
        assert out == src

    def test_anonymous_hyperlink_targets_preserved(self):
        # Consecutive ``__ URL`` lines must not be joined into prose.
        src = (
            "`link one`__ and `link two`__.\n"
            "\n"
            "__ https://example.com/one\n"
            "__ https://example.com/two\n"
        )
        out = self.wrap(src)
        assert "__ https://example.com/one" in out
        assert "__ https://example.com/two" in out

    def test_bullet_item_multiline_merged(self):
        # A multi-line bullet item with short content merges onto one
        # line in join mode.
        src = "* foo\n  bar\n  zoo\n"
        out = self.wrap(src)
        assert out == "* foo bar zoo\n"

    def test_join_on_by_default(self):
        src = "foo\nbar\nzoo\n"
        out = rst_wrap_lines.wrap_rst(src)
        assert out == "foo bar zoo\n"
