"""Tests for bullet and enumerated list handling."""

from . import BaseTest


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

    def test_dash_bullet_wrapped(self):
        # Dash is a valid bullet marker and must wrap like * and +.
        src = (
            "- This dash bullet item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        # Continuation must be indented to the text column (2 chars).
        assert "\n  " in out
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

    def test_enumerated_close_paren_wrapped(self):
        # "1)" form must be recognised as enumerated and wrap correctly.
        src = (
            "1) This enumerated item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_enumerated_alpha_wrapped(self):
        # "a." form must be recognised as enumerated and wrap correctly.
        src = (
            "a. This enumerated item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_enumerated_auto_wrapped(self):
        # "#." auto-enumerated form must be recognised and wrap.
        src = (
            "#. This enumerated item is quite long and should be"
            " wrapped by the tool because it exceeds the max width.\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
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

    def test_bullet_extra_spacing_preserved(self):
        # Extra spaces between bullet marker and text (3+ spaces)
        # must be preserved -- the tool should not normalize them
        # to a single space, and the continuation must stay aligned
        # to the text column.
        src = (
            "-   This is a bullet with extra spaces after the"
            " marker.\n"
            "    Continuation line aligned to the text column.\n"
        )
        out = self.wrap(src)
        assert out.startswith("-   ")
        assert "\n    " in out
        self.check_all(src, out)

    def test_nested_constructs_in_list_item(self):
        # A list item containing emphasis, inline code, and a role.
        # All inline constructs must survive wrapping as atomic
        # tokens.
        src = (
            "- This list item has *emphasis*, ``inline code``,"
            " and a :ref:`long_reference_name` that must not"
            " break.\n"
        )
        out = self.wrap(src)
        assert "*emphasis*" in out
        assert "``inline code``" in out
        assert ":ref:`long_reference_name`" in out
        self.check_all(src, out)

    def test_nested_bullet_not_merged_into_parent(self):
        # Regression: a nested bullet with no blank line above was
        # slurped into the parent, producing ``- Parent. - Nested.``
        # on one line under ``join=True``. See the paired fixture
        # ``examples/nested_bullet_not_merged_into_parent.rst``.
        src = "- Parent line short.\n  - Nested item.\n"
        out = self.wrap(src)
        assert out == src

    def test_nested_list_after_blank_wrapped(self):
        # Regression: over-width children of a nested bullet list
        # (parent + blank + indented children) were passed verbatim
        # because the indented-line passthrough caught them before
        # the list-item branch.
        src = (
            "- Split docs into multiple sections:\n"
            "\n"
            "  - :doc:`/alternatives <alternatives>`: list of"
            " alternative Python libraries and tools that overlap"
            " with psutil.\n"
            "  - :doc:`/credits <credits>`: list contributors and"
            " donors (was old ``CREDITS`` in root dir).\n"
        )
        out = self.wrap(src)
        for line in out.splitlines():
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_bullet_with_long_hyperlink_continuation_not_lengthened(self):
        # Bullet continuation with a manually-split long hyperlink
        # -> unsplittable token after join. Output must not exceed
        # the longest original line.
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
