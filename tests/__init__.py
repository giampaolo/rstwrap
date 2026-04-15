"""Test utils."""

import re

from rst_wrap_lines import wrap_rst

# Matches inline RST constructs that may legitimately contain multiple
# spaces (inline literals, roles, hyperlinks, emphasis, bold). Used to
# exclude protected content when checking for bare double-spaces.
_INLINE_MASK_RE = re.compile(
    r"``[^`]+``"  # ``inline literal``
    r"|:[a-zA-Z][\w:+.-]*:`[^`]+?`_{0,2}"  # :role:`text`
    r"|`[^`]+?<[^>]+>`_{1,2}"  # `display <url>`_
    r"|`[^`]+?`_{0,2}"  # `phrase ref`_
    r"|\*\*[^*]+\*\*"  # **bold**
    r"|\*[^*]+\*"  # *emphasis*
)

# Matches hyperlink target lines: .. _name: url
_HYPERLINK_TARGET_RE = re.compile(r"^\.\. _[^:]+: \S")

# Matches list item first lines (bullet or enumerated).
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)]|#\.)\s+")

# Matches directive marker lines: .. foo:: or .. domain:foo::
_DIRECTIVE_RE = re.compile(r"^\s*\.\. \w[\w:+.-]*::")

# Matches section underline/overline lines (2+ repeated punctuation chars).
# Minimum 3 chars: docutils requires >=3 for a section underline. A bare
# ``--`` on its own line is parsed as plain prose text, not as an
# underline, so the fidelity guard must not demand it appear verbatim.
_UNDERLINE_RE = re.compile(r"^([=\-~^#*+\']{3,})\s*$")


def has_bare_double_space(line):
    """True if *line* contains '  ' outside inline RST constructs."""
    return "  " in _INLINE_MASK_RE.sub("X", line)


class BaseTest:
    WIDTH = 79
    JOIN = False

    def wrap(self, source, width=None):
        if width is None:
            width = self.WIDTH
        return wrap_rst(source, width, join=self.JOIN)

    def assert_idempotent(self, source, width=None):
        """Assert that wrapping twice yields the same output as once."""
        if width is None:
            width = self.WIDTH
        first = wrap_rst(source, width, join=self.JOIN)
        second = wrap_rst(first, width, join=self.JOIN)
        assert first == second

    def check_all(self, src, out):
        """Run all universal sanity checks on a (src, out) pair."""
        self.assert_idempotent(src)
        self.assert_trailing_newline_consistent(src, out)
        self.assert_no_trailing_whitespace_introduced(src, out)
        self.assert_no_double_space_in_list_items(src, out)
        self.assert_blank_line_count_preserved(src, out)
        self.assert_hyperlink_targets_unchanged(src, out)
        self.assert_directive_markers_preserved(src, out)
        self.assert_section_underlines_preserved(src, out)

    def assert_trailing_newline_consistent(self, src, out):
        """Assert output ends with newline iff source does."""
        assert src.endswith("\n") == out.endswith(
            "\n"
        ), "trailing newline presence changed between source and output"

    def assert_no_trailing_whitespace_introduced(self, src, out):
        """Assert no tool-produced line ends with whitespace."""
        src_line_set = set(src.splitlines())
        for line in out.splitlines():
            if line in src_line_set:
                continue
            assert (
                line == line.rstrip()
            ), f"tool-produced line has trailing whitespace: {line!r}"

    def assert_no_double_space_in_list_items(self, src, out):
        """Assert no tool-produced list-item line contains bare double
        spaces.
        """
        # The tool strips trailing whitespace, so verbatim-passthrough
        # matches must be done against rstrip'd source lines.
        src_line_set = {ln.rstrip() for ln in src.splitlines()}
        for line in out.splitlines():
            if line in src_line_set:
                continue
            m = _LIST_ITEM_RE.match(line)
            if not m:
                continue
            # Check only the text portion after the bullet marker to avoid
            # false positives from leading indentation spaces.
            text = line[m.end() :]
            assert not has_bare_double_space(
                text
            ), f"tool-produced list-item line has bare double-space: {line!r}"

    def assert_blank_line_count_preserved(self, src, out):
        r"""Assert the number of blank lines is unchanged.

        Count lines that are empty after ``strip()``. The older proxy
        of ``count("\n\n")`` misreports when the source contains
        whitespace-only lines (e.g. ``"  "``) or form-feed characters
        on their own line, neither of which is a tool bug.
        """
        # ``rstrip`` before ``splitlines`` drops trailing whitespace and
        # trailing blank lines from both sides, so a whitespace-only
        # final "line" without a terminating newline (which the tool
        # strips away) doesn't throw off the count.
        src_blanks = sum(
            1 for ln in src.rstrip().splitlines() if not ln.strip()
        )
        out_blanks = sum(
            1 for ln in out.rstrip().splitlines() if not ln.strip()
        )
        assert (
            src_blanks == out_blanks
        ), f"blank line count changed: {src_blanks} -> {out_blanks}"

    def assert_hyperlink_targets_unchanged(self, src, out):
        """Assert every hyperlink target line in src appears in out.

        Compared after rstrip: the tool strips trailing whitespace, so
        ``.. _name: url `` (with trailing space) matches ``.. _name: url``
        in the output.
        """
        out_lines = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            if _HYPERLINK_TARGET_RE.match(line):
                assert (
                    line.rstrip() in out_lines
                ), f"hyperlink target line missing from output: {line!r}"

    def assert_directive_markers_preserved(self, src, out):
        """Assert every directive marker line in src appears in out.

        See :meth:`assert_hyperlink_targets_unchanged` for the rstrip
        rationale.
        """
        out_lines = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            if _DIRECTIVE_RE.match(line):
                assert (
                    line.rstrip() in out_lines
                ), f"directive marker line missing from output: {line!r}"

    def assert_section_underlines_preserved(self, src, out):
        """Assert every section underline/overline line in src appears
        in out.

        See :meth:`assert_hyperlink_targets_unchanged` for the rstrip
        rationale.
        """
        out_lines = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            if _UNDERLINE_RE.match(line):
                assert (
                    line.rstrip() in out_lines
                ), f"section underline line missing from output: {line!r}"
