"""Tests for rst_wrap_lines.wrap_rst()."""

import pytest

import rst_wrap_lines

from . import BaseTest


class TestCLI:
    @pytest.fixture(autouse=True)
    def tmp_rst(self, tmp_path):
        """Write a sample .rst file into tmp_path and expose both."""
        self.dir = tmp_path
        self.rst = tmp_path / "sample.rst"
        self.rst.write_text("Hello world.\n", encoding="utf-8")

    # --- parse_cli ---

    def test_parse_cli_single_file(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert [self.rst] == rst_wrap_lines.PATHS

    def test_parse_cli_directory_collects_rst(self):
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert self.rst in rst_wrap_lines.PATHS

    def test_parse_cli_width(self):
        rst_wrap_lines.parse_cli(["--width", "60", str(self.rst)])
        assert rst_wrap_lines.WIDTH == 60

    def test_parse_cli_check_flag(self):
        rst_wrap_lines.parse_cli(["--check", str(self.rst)])
        assert rst_wrap_lines.CHECK is True

    def test_parse_cli_diff_flag(self):
        rst_wrap_lines.parse_cli(["--diff", str(self.rst)])
        assert rst_wrap_lines.DIFF is True

    def test_parse_cli_ignores_dotgit_dir(self):
        git_dir = self.dir / ".git"
        git_dir.mkdir()
        (git_dir / "hidden.rst").write_text("ignored\n", encoding="utf-8")
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert not any(".git" in str(p) for p in rst_wrap_lines.PATHS)

    def test_parse_cli_paths_reset_between_calls(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.PATHS.count(self.rst) == 1

    # --- main ---

    def test_main_rewrites_file(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main([str(self.rst)])
        result = self.rst.read_text(encoding="utf-8")
        assert result != long_line
        for line in result.splitlines():
            assert len(line) <= 79

    def test_main_check_exits_1_when_changed(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert exc_info.value.code == 1

    def test_main_check_does_not_write(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit):
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert self.rst.read_text(encoding="utf-8") == long_line

    def test_main_no_change_exits_0(self):
        # File already fits within 79 chars; no SystemExit expected.
        rst_wrap_lines.main(["--check", str(self.rst)])


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


class TestDirectives(BaseTest):
    def test_opaque_directive_body_verbatim(self):
        # code-block is not in _PROSE_BODY_DIRECTIVES; body must pass
        # through byte-identical even if lines are long.
        long_line = "    " + "x" * 100
        src = f".. code-block:: python\n\n{long_line}\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_image_directive_unchanged(self):
        src = ".. image:: foo.png\n   :width: 100\n   :alt: some alt text\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_prose_directive_body_wrapped(self):
        # .. note:: is in _PROSE_BODY_DIRECTIVES; its long body must
        # be wrapped.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. note::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. note::")
        for line in out.splitlines()[1:]:
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_warning_directive_body_wrapped(self):
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. warning::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. warning::")
        self.check_all(src, out)

    def test_domain_prefixed_prose_directive_body_wrapped(self):
        # e.g. .. py:function:: is treated as "function" after
        # stripping the domain prefix.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. py:function:: foo(x)\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. py:function::")
        self.check_all(src, out)

    def test_prose_directive_short_body_unchanged(self):
        src = ".. note::\n\n   Short note.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)


class TestInlineMarkup(BaseTest):
    def test_inline_literal_not_broken(self):
        src = "Prose with ``an inline literal that has spaces inside`` here.\n"
        out = self.wrap(src)
        assert "``an inline literal that has spaces inside``" in out
        self.check_all(src, out)

    def test_inline_literal_spaces_not_collapsed(self):
        # Spaces inside ``...`` must survive space-collapsing.
        src = "See ``hello  world`` for details.\n"
        out = self.wrap(src)
        assert "``hello  world``" in out
        self.check_all(src, out)

    def test_emphasis_not_broken(self):
        src = "Prose with *emphasized words across tokens* here.\n"
        out = self.wrap(src)
        assert "*emphasized words across tokens*" in out
        self.check_all(src, out)

    def test_strong_not_broken(self):
        src = "This is **very important words** in a sentence.\n"
        out = self.wrap(src)
        assert "**very important words**" in out
        self.check_all(src, out)

    def test_role_not_broken(self):
        src = "See :func:`some function name` for details.\n"
        out = self.wrap(src)
        assert ":func:`some function name`" in out
        self.check_all(src, out)

    def test_hyperlink_ref_not_broken(self):
        src = "See `the full documentation <https://example.com>`_ for more.\n"
        out = self.wrap(src)
        assert "`the full documentation <https://example.com>`_" in out
        self.check_all(src, out)

    def test_anonymous_hyperlink_ref_not_broken(self):
        src = "See `anonymous link <https://example.com>`__ here.\n"
        out = self.wrap(src)
        assert "`anonymous link <https://example.com>`__" in out
        self.check_all(src, out)

    def test_substitution_ref_not_broken(self):
        src = "Use |my substitution ref| in the text here.\n"
        out = self.wrap(src)
        assert "|my substitution ref|" in out
        self.check_all(src, out)

    def test_footnote_ref_unchanged(self):
        src = "As noted [1]_ previously.\n"
        out = self.wrap(src)
        assert "[1]_" in out
        self.check_all(src, out)


class TestListItems(BaseTest):
    def test_long_bullet_item_wrapped(self):
        src = (
            "- This bullet item is quite long and should be wrapped"
            " by the tool because it exceeds the maximum line length.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_short_bullet_item_unchanged(self):
        src = "- Short item.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_star_bullet(self):
        src = "* Short item.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_plus_bullet(self):
        src = "+ Short item.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_enumerated_list_wrapped(self):
        src = (
            "1. This enumerated item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_enumerated_paren_style(self):
        src = "(1) Short item.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

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
        self.check_all(src, out)

    def test_multiple_bullets_in_run(self):
        src = "- First item.\n- Second item.\n- Third item.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_bullet_continuation_indent_guard(self):
        # A line indented deeper than the text column immediately after
        # a bullet must not cause wrapping (visually attached).
        src = "- Short.\n    Deeper indented line.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_bullet_mid_paragraph_is_prose(self):
        # A bullet-like line that appears mid-paragraph (no preceding
        # blank line) must be treated as prose continuation.
        src = "Some prose that continues\n- and this is not a list item.\n"
        out = self.wrap(src)
        # The output must be a single wrapped paragraph, not a list.
        assert out.strip().startswith("Some prose")
        self.check_all(src, out)

    def test_bullet_with_long_hyperlink_continuation_not_lengthened(self):
        # A bullet whose continuation contains a long hyperlink that was
        # manually split across lines. Joining produces an un-splittable
        # token; the tool must not produce a line longer than the longest
        # original line.
        src = (
            "- See the `prebuilt versions are\n"
            "  available <https://docs.python.org/dev/download.html>`_."
            "  Also other stuff.\n"
        )
        out = self.wrap(src)
        max_src = max(len(x) for x in src.splitlines())
        max_out = max(len(x) for x in out.splitlines())
        assert max_out <= max_src
        self.check_all(src, out)
