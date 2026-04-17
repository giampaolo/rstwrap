"""Test utils."""

import re

from rstwrap import _DIRECTIVE_RE as _TOOL_DIRECTIVE_RE
from rstwrap import _PROSE_BODY_DIRECTIVES
from rstwrap import wrap_rst

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

# Section under/overline: 3+ repeated punctuation chars. Docutils
# requires >=3; a bare ``--`` parses as prose, so the fidelity guard
# must not demand it appear verbatim.
_UNDERLINE_RE = re.compile(r"^([=\-~^#*+\']{3,})\s*$")


def has_bare_double_space(line):
    """True if *line* contains '  ' outside inline RST constructs."""
    return "  " in _INLINE_MASK_RE.sub("X", line)


def collect_indented_body(lines, i, n, min_indent):
    """Collect indented lines starting at *i*.

    Returns (block_lines_rstripped, next_i). Stops when a non-blank
    line has indent < *min_indent*.
    """
    buf = []
    while i < n:
        ln = lines[i]
        if ln.strip() and (len(ln) - len(ln.lstrip())) < min_indent:
            break
        buf.append(ln.rstrip())
        i += 1
    while buf and not buf[-1]:
        buf.pop()
    return buf, i


def extract_code_blocks(text):
    """Return code-block contents from *text* (rstripped lines):
    ``::`` literal blocks, non-prose directive bodies
    (``.. code-block::``, ``.. highlight::``, ...), and doctest
    blocks (``>>>`` / ``...``).
    """
    lines = text.splitlines()
    n = len(lines)
    blocks = []
    i = 0
    while i < n:
        raw = lines[i]
        stripped = raw.rstrip()
        lstripped = raw.lstrip()

        # --- Non-prose directive body ---
        m = _TOOL_DIRECTIVE_RE.match(raw)
        if m and m.group(1) not in _PROSE_BODY_DIRECTIVES:
            i += 1
            # Directive body: all indented/blank lines after marker.
            body_start = i
            while i < n and (not lines[i] or lines[i][:1] in {" ", "\t"}):
                i += 1
            body = [ln.rstrip() for ln in lines[body_start:i]]
            while body and not body[-1]:
                body.pop()
            if body:
                blocks.append("\n".join(body))
            continue

        # --- ``::`` literal block ---
        if stripped.endswith("::") and not re.match(r"^\s*\.\. ", stripped):
            introducer_indent = len(raw) - len(lstripped)
            blank_start = i + 1
            i = blank_start
            while i < n and not lines[i].strip():
                i += 1
            # RST requires at least one blank line after ::.
            if i == blank_start or i >= n:
                continue
            first = lines[i]
            content_indent = len(first) - len(first.lstrip())
            if content_indent <= introducer_indent:
                continue
            buf, i = collect_indented_body(lines, i, n, content_indent)
            if buf:
                blocks.append("\n".join(buf))
            continue

        # --- Doctest block ---
        if lstripped.startswith(">>> ") or lstripped == ">>>":
            buf = [raw.rstrip()]
            i += 1
            while i < n:
                ln = lines[i]
                ls = ln.lstrip()
                is_doctest = ls.startswith((">>> ", "... ")) or ls in {
                    ">>>",
                    "...",
                }
                is_output = ln.strip() and not ls.startswith(">>>")
                if is_doctest or is_output:
                    buf.append(ln.rstrip())
                    i += 1
                else:
                    break
            while buf and not buf[-1]:
                buf.pop()
            if buf:
                blocks.append("\n".join(buf))
            continue

        i += 1
    return blocks


class BaseTest:
    WIDTH = 79
    JOIN = True

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
        self.assert_hyperlink_targets_unchanged(src, out)
        self.assert_directive_markers_preserved(src, out)
        self.assert_section_underlines_preserved(src, out)
        self.assert_code_blocks_unchanged(src, out)

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
        """Assert no tool-produced list item has a bare double space."""
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

    def assert_hyperlink_targets_unchanged(self, src, out):
        """Assert every hyperlink target in src appears in out.
        Compared after rstrip so ``.. _name: url `` (trailing space)
        matches ``.. _name: url``.
        """
        out_lines = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            if _HYPERLINK_TARGET_RE.match(line):
                assert (
                    line.rstrip() in out_lines
                ), f"hyperlink target line missing from output: {line!r}"

    def assert_directive_markers_preserved(self, src, out):
        """Assert every directive marker in src appears in out.
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
        """Assert every section under/overline in src appears in out.
        See :meth:`assert_hyperlink_targets_unchanged` for the rstrip
        rationale.
        """
        out_lines = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            if _UNDERLINE_RE.match(line):
                assert (
                    line.rstrip() in out_lines
                ), f"section underline line missing from output: {line!r}"

    def assert_code_blocks_unchanged(self, src, out):
        """Assert code block content is unchanged (``::`` literal
        blocks, non-prose directive bodies, doctest blocks).
        """
        src_blocks = extract_code_blocks(src)
        out_blocks = extract_code_blocks(out)
        out_set = set(out_blocks)
        for i, s in enumerate(src_blocks):
            assert (
                s in out_set
            ), f"source code block {i} missing or changed in output:\n{s}"
