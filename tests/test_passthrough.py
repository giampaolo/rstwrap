"""Tests for RST constructs that must pass through verbatim."""

from . import BaseTest


class TestPassthrough(BaseTest):
    def test_section_title_unchanged(self):
        src = "My Section\n==========\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_section_with_overline_unchanged(self):
        src = "========\nOverline\n========\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_short_underline_not_treated_as_title(self):
        # An underline shorter than the preceding text is not a title
        # (docutils treats it as prose). The tool must not merge the
        # text line with the underline as if it were a title, and must
        # not merge the underline into following prose either.
        src = "Long line of text that is not a title\n---\nMore prose.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_literal_block_unchanged(self):
        src = "Example::\n\n    some code here    with spaces\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_block_quote_unchanged(self):
        # An indented block not introduced by '::' is a block quote.
        src = "Paragraph.\n\n    Indented block quote.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_grid_table_unchanged(self):
        src = "+-------+-------+\n| a     | b     |\n+-------+-------+\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_simple_table_unchanged(self):
        src = "===  ===\na    b\n===  ===\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_comment_unchanged(self):
        src = ".. this is a comment\n   that spans two lines\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_field_list_unchanged(self):
        src = ":Author: Giampaolo\n:Version: 1.0\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_field_list_with_spaces_in_name_unchanged(self):
        src = ":type exc_info: bool\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_definition_list_term_unchanged(self):
        # The term line must not be wrapped into the definition body.
        src = "term\n    Definition text.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_hyperlink_target_unchanged(self):
        src = ".. _some target: https://example.com\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_transition_unchanged(self):
        src = "Paragraph.\n\n----------\n\nAnother paragraph.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_field_list_long_value_unchanged(self):
        # A field list entry whose value exceeds WIDTH must not be
        # wrapped -- the tool should not treat it as prose.
        src = (
            ":Author: A very long author name that goes on"
            " and on and exceeds the target width of seventy-nine"
            " characters easily\n"
        )
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_option_list_unchanged(self):
        # Option list items must not be merged into a prose paragraph.
        src = "-f FILE  Input file.\n-o FILE  Output file.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_option_list_long_option_unchanged(self):
        src = (
            "--output FILE  The output file.\n--verbose      Enable verbose"
            " mode.\n"
        )
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)
