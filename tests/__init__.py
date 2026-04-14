"""Test utils."""

import pathlib
import re

from rst_wrap_lines import wrap_rst

TESTS_DIR = pathlib.Path(__file__).parent

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
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)]) ")


def _has_bare_double_space(line):
    """True if *line* contains '  ' outside inline RST constructs."""
    return "  " in _INLINE_MASK_RE.sub("X", line)


class InternalBaseTest:
    WIDTH = 79

    def wrap(self, source, width=None):
        if width is None:
            width = self.WIDTH
        return wrap_rst(source, width)

    def assert_idempotent(self, source, width=None):
        """Assert that wrapping twice yields the same output as once."""
        if width is None:
            width = self.WIDTH
        first = wrap_rst(source, width)
        second = wrap_rst(first, width)
        assert first == second

    def check_all(self, src, out):
        """Run all universal sanity checks on a (src, out) pair."""
        self.assert_idempotent(src)
        self.assert_no_trailing_whitespace_introduced(src, out)
        self.assert_no_double_space_in_list_items(src, out)
        self.assert_blank_line_count_preserved(src, out)
        self.assert_hyperlink_targets_unchanged(src, out)

    def assert_no_double_space_in_list_items(self, src, out):
        """Assert no tool-produced list-item line contains bare double spaces."""
        src_line_set = set(src.splitlines())
        for line in out.splitlines():
            if line in src_line_set:
                continue
            m = _LIST_ITEM_RE.match(line)
            if not m:
                continue
            # Check only the text portion after the bullet marker to avoid
            # false positives from leading indentation spaces.
            text = line[m.end() :]
            assert not _has_bare_double_space(text), (
                f"tool-produced list-item line has bare double-space: {line!r}"
            )

    def assert_blank_line_count_preserved(self, src, out):
        """Assert the number of blank lines is unchanged."""
        src_blanks = src.count("\n\n")
        out_blanks = out.count("\n\n")
        assert src_blanks == out_blanks, (
            f"blank line count changed: {src_blanks} -> {out_blanks}"
        )

    def assert_hyperlink_targets_unchanged(self, src, out):
        """Assert every hyperlink target line in src appears in out."""
        out_lines = set(out.splitlines())
        for line in src.splitlines():
            if _HYPERLINK_TARGET_RE.match(line):
                assert line in out_lines, (
                    f"hyperlink target line missing from output: {line!r}"
                )

    def assert_no_trailing_whitespace_introduced(self, src, out):
        """Assert no tool-produced line ends with whitespace."""
        src_line_set = set(src.splitlines())
        for line in out.splitlines():
            if line in src_line_set:
                continue
            assert line == line.rstrip(), (
                f"tool-produced line has trailing whitespace: {line!r}"
            )
