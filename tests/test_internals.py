"""Tests for rst_wrap_lines.wrap_rst()."""

from . import InternalBaseTest


class TestProseParagraphs(InternalBaseTest):
    def test_long_paragraph_is_wrapped(self):
        src = (
            "This is a very long prose paragraph that clearly exceeds"
            " the default line length of seventy-nine characters and"
            " must therefore be wrapped.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.assert_idempotent(src)

    def test_short_paragraph_unchanged(self):
        src = "Short paragraph.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_redundant_spaces_collapsed(self):
        src = "hello  world  foo.\n"
        out = self.wrap(src)
        assert "  " not in out
        self.assert_idempotent(src)

    def test_trailing_newline_preserved(self):
        src = "Some prose.\n"
        assert self.wrap(src).endswith("\n")
        self.assert_idempotent(src)

    def test_no_trailing_newline_preserved(self):
        src = "Some prose."
        assert not self.wrap(src).endswith("\n")
        self.assert_idempotent(src)

    def test_empty_string(self):
        assert self.wrap("") == ""

    def test_blank_lines_only(self):
        src = "\n\n\n"
        assert self.wrap(src) == src

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
        self.assert_idempotent(src)

    def test_paragraph_stops_before_directive(self):
        # Prose followed by a directive: the directive line must not
        # be consumed into the paragraph.
        src = "Some prose.\n\n.. note::\n\n   A note.\n"
        out = self.wrap(src)
        assert ".. note::" in out
        self.assert_idempotent(src)

    def test_standalone_double_colon_not_merged(self):
        # A standalone '::' must stay on its own line.
        src = "Intro paragraph.\n\n::\n\n    literal block\n"
        out = self.wrap(src)
        assert "::\n" in out
        self.assert_idempotent(src)


class TestPassthrough(InternalBaseTest):
    def test_section_title_unchanged(self):
        src = "My Section\n==========\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_section_with_overline_unchanged(self):
        src = "========\nOverline\n========\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_literal_block_unchanged(self):
        src = "Example::\n\n    some code here    with spaces\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_block_quote_unchanged(self):
        # An indented block not introduced by '::' is a block quote.
        src = "Paragraph.\n\n    Indented block quote.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_grid_table_unchanged(self):
        src = "+-------+-------+\n| a     | b     |\n+-------+-------+\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_simple_table_unchanged(self):
        src = "===  ===\na    b\n===  ===\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_comment_unchanged(self):
        src = ".. this is a comment\n   that spans two lines\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_field_list_unchanged(self):
        src = ":Author: Giampaolo\n:Version: 1.0\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_field_list_with_spaces_in_name_unchanged(self):
        src = ":type exc_info: bool\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_definition_list_term_unchanged(self):
        # The term line must not be wrapped into the definition body.
        src = "term\n    Definition text.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_hyperlink_target_unchanged(self):
        src = ".. _some target: https://example.com\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)


class TestDirectives(InternalBaseTest):
    def test_opaque_directive_body_verbatim(self):
        # code-block is not in _PROSE_BODY_DIRECTIVES; body must pass
        # through byte-identical even if lines are long.
        long_line = "    " + "x" * 100
        src = f".. code-block:: python\n\n{long_line}\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_image_directive_unchanged(self):
        src = ".. image:: foo.png\n   :width: 100\n   :alt: some alt text\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_prose_directive_body_wrapped(self):
        # .. note:: is in _PROSE_BODY_DIRECTIVES; its long body must
        # be wrapped.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. note::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. note::")
        for line in out.splitlines()[1:]:
            assert len(line) <= self.WIDTH
        self.assert_idempotent(src)

    def test_warning_directive_body_wrapped(self):
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. warning::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. warning::")
        self.assert_idempotent(src)

    def test_domain_prefixed_prose_directive_body_wrapped(self):
        # e.g. .. py:function:: is treated as "function" after
        # stripping the domain prefix.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. py:function:: foo(x)\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. py:function::")
        self.assert_idempotent(src)

    def test_prose_directive_short_body_unchanged(self):
        src = ".. note::\n\n   Short note.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)


class TestInlineMarkup(InternalBaseTest):
    def test_inline_literal_not_broken(self):
        src = "Prose with ``an inline literal that has spaces inside`` here.\n"
        out = self.wrap(src)
        assert "``an inline literal that has spaces inside``" in out
        self.assert_idempotent(src)

    def test_inline_literal_spaces_not_collapsed(self):
        # Spaces inside ``...`` must survive space-collapsing.
        src = "See ``hello  world`` for details.\n"
        out = self.wrap(src)
        assert "``hello  world``" in out

    def test_emphasis_not_broken(self):
        src = "Prose with *emphasized words across tokens* here.\n"
        out = self.wrap(src)
        assert "*emphasized words across tokens*" in out
        self.assert_idempotent(src)

    def test_strong_not_broken(self):
        src = "This is **very important words** in a sentence.\n"
        out = self.wrap(src)
        assert "**very important words**" in out
        self.assert_idempotent(src)

    def test_role_not_broken(self):
        src = "See :func:`some function name` for details.\n"
        out = self.wrap(src)
        assert ":func:`some function name`" in out
        self.assert_idempotent(src)

    def test_hyperlink_ref_not_broken(self):
        src = "See `the full documentation <https://example.com>`_ for more.\n"
        out = self.wrap(src)
        assert "`the full documentation <https://example.com>`_" in out
        self.assert_idempotent(src)

    def test_anonymous_hyperlink_ref_not_broken(self):
        src = "See `anonymous link <https://example.com>`__ here.\n"
        out = self.wrap(src)
        assert "`anonymous link <https://example.com>`__" in out
        self.assert_idempotent(src)

    def test_substitution_ref_not_broken(self):
        src = "Use |my substitution ref| in the text here.\n"
        out = self.wrap(src)
        assert "|my substitution ref|" in out
        self.assert_idempotent(src)

    def test_footnote_ref_unchanged(self):
        src = "As noted [1]_ previously.\n"
        out = self.wrap(src)
        assert "[1]_" in out
        self.assert_idempotent(src)


class TestListItems(InternalBaseTest):
    def test_long_bullet_item_wrapped(self):
        src = (
            "- This bullet item is quite long and should be wrapped"
            " by the tool because it exceeds the maximum line length.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.assert_idempotent(src)

    def test_short_bullet_item_unchanged(self):
        src = "- Short item.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_star_bullet(self):
        src = "* Short item.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_plus_bullet(self):
        src = "+ Short item.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_enumerated_list_wrapped(self):
        src = (
            "1. This enumerated item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.assert_idempotent(src)

    def test_enumerated_paren_style(self):
        src = "(1) Short item.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_multiline_bullet_continuation_wrapped(self):
        # A bullet with a continuation line indented to the text column.
        src = (
            "- First line of a bullet item that is quite long indeed,"
            " really quite long.\n"
            "  Continuation line that is also rather long and verbose.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.assert_idempotent(src)

    def test_multiple_bullets_in_run(self):
        src = "- First item.\n- Second item.\n- Third item.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_bullet_continuation_indent_guard(self):
        # A line indented deeper than the text column immediately after
        # a bullet must not cause wrapping (visually attached).
        src = "- Short.\n    Deeper indented line.\n"
        assert self.wrap(src) == src
        self.assert_idempotent(src)

    def test_bullet_mid_paragraph_is_prose(self):
        # A bullet-like line that appears mid-paragraph (no preceding
        # blank line) must be treated as prose continuation.
        src = "Some prose that continues\n- and this is not a list item.\n"
        out = self.wrap(src)
        # The output must be a single wrapped paragraph, not a list.
        assert out.strip().startswith("Some prose")
        self.assert_idempotent(src)
