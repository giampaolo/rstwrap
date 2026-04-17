#!/usr/bin/env python3

"""Wrap RST prose paragraphs to a maximum line length.

Example usages:

    rstwrap docs/*.rst
    rstwrap docs/                # recurse into a directory
    rstwrap --check docs/*.rst
    rstwrap --diff docs/*.rst    # print unified diff, don't write
    rstwrap --width 80 foo.rst
    rstwrap --join docs/*.rst    # also merge short lines onto one
    rstwrap --safe docs/*.rst    # verify doctree via docutils
    cat foo.rst | rstwrap -      # read from stdin, write to stdout
"""

import argparse
import difflib
import importlib.metadata
import re
import string
import sys
import tomllib
from pathlib import Path

try:
    __version__ = importlib.metadata.version("rstwrap")
except importlib.metadata.PackageNotFoundError:
    # Running from source without install (e.g. python3 rstwrap.py).
    __version__ = "unknown"

# ---------------------------------------------------------------------------
# CLI (module-scope constants, per project guidelines)
# ---------------------------------------------------------------------------

WIDTH = 79
CHECK = False
COLOR = False
DIFF = False
JOIN = True
SAFE = False
QUIET = False
PATHS = set()

IGNORED_DIRS = frozenset([
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    "_build",
    "build",
    "dist",
])

# ---------------------------------------------------------------------------
# Colored diff output
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"


def _colorize_diff(lines):
    """Yield diff lines with ANSI color escapes."""
    for line in lines:
        if line.startswith(("---", "+++")):
            yield _BOLD + line + _RESET
        elif line.startswith("-"):
            yield _RED + line + _RESET
        elif line.startswith("+"):
            yield _GREEN + line + _RESET
        elif line.startswith("@@"):
            yield _CYAN + line + _RESET
        else:
            yield line


# ---------------------------------------------------------------------------
# Inline-token recognition
# ---------------------------------------------------------------------------

# Inline RST constructs that must never be broken across lines.
# Longer alternatives come first so the regex prefers them.
_INLINE_PATTERNS = [
    # ``inline literal`` (may contain spaces)
    r"``.+?``",
    # :role:`text` or :domain:role:`text`, optional trailing _ / __
    r":[a-zA-Z][\w:+.-]*:`[^`]+?`_{0,2}",
    # `display <target>`_ or `display <target>`__
    r"`[^`]+?<[^>]+>`_{1,2}",
    # `phrase reference`_  or anonymous `phrase`__
    r"`[^`]+?`_{1,2}",
    # `interpreted text` (default role)
    r"`[^`]+?`",
    # |substitution|_ or |substitution|__ or |substitution|
    r"\|[^|\s][^|]*\|_{0,2}",
    # [footnote_or_citation]_  (auto, numeric, named)
    r"\[[^\]\s]+\]_",
    # **strong emphasis** (may contain spaces)
    r"\*\*[^\s*](?:[^*]*[^\s*])?\*\*",
    # *emphasis* (may contain spaces; not **)
    r"(?<!\*)\*[^\s*](?:[^*]*[^\s*])?\*(?!\*)",
]
_INLINE_RE = re.compile("|".join(f"(?:{p})" for p in _INLINE_PATTERNS))

_PLACEHOLDER_RE = re.compile(r"\x00T(\d+)\x00")


def _protect_inline(text):
    """Mask inline RST constructs containing whitespace so they
    survive whitespace-based splitting. Returns (masked, placeholders).
    """
    placeholders = {}
    counter = [0]

    def repl(m):
        tok = m.group(0)
        if not any(c.isspace() for c in tok):
            return tok
        key = f"\x00T{counter[0]}\x00"
        counter[0] += 1
        placeholders[key] = tok
        return key

    return _INLINE_RE.sub(repl, text), placeholders


def _restore_inline(text, placeholders):
    def repl(m):
        return placeholders[m.group(0)]

    return _PLACEHOLDER_RE.sub(repl, text)


def _visual_len(token, placeholders):
    """Length of *token* after placeholder expansion."""
    if not placeholders:
        return len(token)
    expanded = _PLACEHOLDER_RE.sub(
        lambda m: placeholders.get(m.group(0), m.group(0)), token
    )
    return len(expanded)


# ---------------------------------------------------------------------------
# Paragraph wrapping
# ---------------------------------------------------------------------------


def _collapse_spaces(text):
    """``hello  world`` -> ``hello world``. Spaces inside inline
    constructs (``like  this``, *two  words*) are left intact.
    """
    masked, placeholders = _protect_inline(text)
    masked = re.sub(r"  +", " ", masked)
    return _restore_inline(masked, placeholders)


def _wrap_paragraph(text, width, initial_indent="", subsequent_indent=""):
    """Wrap a single-paragraph *text* to *width* chars.

    Inline RST constructs that contain whitespace are masked first so
    they survive the whitespace-based split intact.
    """
    masked, placeholders = _protect_inline(text)
    words = masked.split()
    if not words:
        return initial_indent.rstrip()

    lines = []
    indent = initial_indent
    cur = indent + words[0]
    cur_len = len(indent) + _visual_len(words[0], placeholders)
    for w in words[1:]:
        w_vlen = _visual_len(w, placeholders)
        if cur_len + 1 + w_vlen <= width:
            cur += " " + w
            cur_len += 1 + w_vlen
        else:
            lines.append(cur)
            cur = subsequent_indent + w
            cur_len = len(subsequent_indent) + w_vlen
    lines.append(cur)
    return _restore_inline("\n".join(lines), placeholders)


# ---------------------------------------------------------------------------
# Block segmentation
# ---------------------------------------------------------------------------

# Docutils accepts any non-alphanumeric printable 7-bit ASCII
# punctuation as a section adornment character. Matches the
# ``nonalphanum7bit`` character class in docutils' rst parser.
_UNDERLINE_CHARS = frozenset(string.punctuation)

# Directive with ``::`` terminator. Optional domain prefix (``py:``,
# ``c:``). Group 1 is the bare name. The trailing ``(?=\s|$)`` matters:
# ``.. note::hello`` is parsed as a comment by docutils, not a directive
# (see docs/internal/rst_rules.md).
_DIRECTIVE_RE = re.compile(r"^\.\.\s+(?:[\w-]+:)?([\w-]+)::(?=\s|$)")

# Directives whose body is prose (and therefore wrappable). Anything
# not in this set is treated as opaque -- we don't know its content
# model, so we pass the body through verbatim.
_PROSE_BODY_DIRECTIVES = frozenset({
    # Python/Sphinx domain object descriptions
    "class",
    "method",
    "function",
    "attribute",
    "data",
    "exception",
    "classmethod",
    "staticmethod",
    "decorator",
    "decoratormethod",
    "module",
    "currentmodule",
    "describe",
    "object",
    # Admonitions
    "note",
    "warning",
    "admonition",
    "attention",
    "caution",
    "danger",
    "error",
    "hint",
    "important",
    "tip",
    "seealso",
    # Versioning
    "versionadded",
    "versionchanged",
    "deprecated",
    "versionremoved",
    # Generic prose containers
    "topic",
    "sidebar",
    "rubric",
    "container",
})

# Simple-table border: two or more runs of '=' (or '-') separated by
# spaces, nothing else. E.g. "===  ====  =====" or "--- --- ---".
_SIMPLE_TABLE_BORDER_RE = re.compile(r"^\s*[=\-]+(?:\s+[=\-]+)+\s*$")


def _is_simple_table_border(line):
    return bool(_SIMPLE_TABLE_BORDER_RE.match(line))


# Bullet list: -, *, + followed by space
_BULLET_RE = re.compile(r"^(?P<indent>\s*)(?P<bullet>[-*+])\s+(?P<rest>.*)$")
# Enumerated list: 1. / 1) / (1) / a. / #.  -- keep conservative
_ENUM_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<bullet>"
    r"(?:\d+|[a-zA-Z]|#)[.)]"  # 1. 1) a. #.
    r"|\((?:\d+|[a-zA-Z])\)"  # (1) (a) (A)
    r")\s+(?P<rest>.*)$"
)


def _is_underline(line):
    """True if the line is a section under/overline (one char repeated).

    Minimum length 3 avoids false positives on ``::`` and ``..``.
    """
    s = line.rstrip()
    if not s or len(s) < 3:
        return False
    c = s[0]
    return c in _UNDERLINE_CHARS and all(ch == c for ch in s)


def _is_short_underline(line):
    """True for 1-2 char underlines (``--`` under ``io``, ``-``
    under ``R``). Excludes ``::``, ``..``, ``:``, ``.``.
    """
    s = line.rstrip()
    if len(s) not in {1, 2} or s in {"::", "..", ":", "."}:
        return False
    c = s[0]
    return c in _UNDERLINE_CHARS and all(ch == c for ch in s)


# Field list item: ``:field name: value``. Names may contain spaces
# and inline markup (``:type exc_info:``, ``:``p_vaddr``: ...``). The
# trailing ``(?:\s|$)`` disambiguates from ``:role:`text``` (a role
# is followed by a backtick, not whitespace/EOL).
_FIELD_LIST_RE = re.compile(r"^:[^:\n]+:(?:\s|$)")

# RST option list item: short option (-x, -x ARG) or long option
# (--foo, --foo=ARG, --foo ARG).  Two or more spaces separate the
# option(s) from the description on the same line.
_OPTION_LIST_RE = re.compile(
    r"^(-[a-zA-Z0-9]|--[a-zA-Z0-9][-a-zA-Z0-9]*)(\s|$)"
)


def _match_list_item(line):
    """Return (indent_str, bullet_str, rest) or None."""
    m = _BULLET_RE.match(line)
    if m:
        return m.group("indent"), m.group("bullet"), m.group("rest")
    m = _ENUM_RE.match(line)
    if m:
        return m.group("indent"), m.group("bullet"), m.group("rest")
    return None


def _leading_ws(line):
    return line[: len(line) - len(line.lstrip(" "))]


# ---------------------------------------------------------------------------
# Block handlers — each takes (lines, i, n, width) and returns
# (emitted_lines, new_i). They never mutate their inputs.
# ---------------------------------------------------------------------------


def _handle_directive(lines, i, n, width, join):
    """Emit directive marker + body.

    Prose-body directives (class, method, note, ...) have their body
    recursively wrapped at the body's own indent. Everything else is
    passed through verbatim.
    """
    raw = lines[i]
    m = _DIRECTIVE_RE.match(raw)
    is_prose = bool(m) and m.group(1) in _PROSE_BODY_DIRECTIVES
    emitted = [raw]
    i += 1
    body_start = i
    while i < n and (not lines[i] or lines[i][:1] in {" ", "\t"}):
        i += 1
    body = lines[body_start:i]
    if is_prose and body:
        indent = None
        for ln in body:
            if ln.strip():
                indent = _leading_ws(ln)
                break
        if indent and all(
            not ln.strip() or ln.startswith(indent) for ln in body
        ):
            dedented = "\n".join(
                ln[len(indent) :] if ln.strip() else "" for ln in body
            )
            sub_width = max(1, width - len(indent))
            wrapped = wrap_rst(dedented, sub_width, join=join)
            emitted.extend(
                indent + ln if ln else "" for ln in wrapped.split("\n")
            )
        else:
            emitted.extend(body)
    else:
        emitted.extend(body)
    return emitted, i


def _handle_simple_table(lines, i, n):
    """Collect a simple table verbatim (border to closing border).
    Only a same-indent border followed by a blank line closes the
    outer table; deeper-indented borders belong to a nested table.
    """
    open_indent = len(lines[i]) - len(lines[i].lstrip(" \t"))
    emitted = [lines[i]]
    i += 1
    while i < n:
        emitted.append(lines[i])
        if _is_simple_table_border(lines[i]):
            this_indent = len(lines[i]) - len(lines[i].lstrip(" \t"))
            if this_indent == open_indent and (
                i + 1 >= n or not lines[i + 1].strip()
            ):
                i += 1
                break
        i += 1
    return emitted, i


def _handle_quoted_literal_block(lines, i, n):
    """Collect a quoted literal block verbatim. Unindented body after
    ``::``, every line starting with the same non-alnum quote char.
    Docutils treats the run as literal.
    """
    quote_char = lines[i][0]
    emitted = []
    while i < n and lines[i][:1] == quote_char:
        emitted.append(lines[i])
        i += 1
    return emitted, i


def _handle_doctest(lines, i, n):
    """Collect a doctest block verbatim (``>>>`` / ``...`` / output
    lines, ending at the first blank line).
    """
    emitted = []
    while i < n and lines[i].strip():
        emitted.append(lines[i])
        i += 1
    return emitted, i


def _prev_nonblank_ends_with_colons(out):
    """True if the last non-blank line in *out* ends with ``::``."""
    for ln in reversed(out):
        if ln.strip():
            return ln.rstrip().endswith("::")
    return False


def _prev_block_is_opaque(out, current_indent):
    """True if the current indented block is the body of a ``::``
    literal or ``..`` explicit-markup introducer (never reshape).
    Walks backward with a decreasing indent watermark so an introducer
    at col 0 is still found under intermediate-indent lines.
    """
    min_indent = current_indent
    for ln in reversed(out):
        if not ln.strip():
            continue
        this_indent = len(ln) - len(ln.lstrip(" \t"))
        if this_indent >= min_indent:
            continue
        s = ln.rstrip()
        if s.endswith("::"):
            return True
        if s.lstrip().startswith(".."):
            return True
        min_indent = this_indent
    return False


def _handle_list_run(lines, i, n, width, join):
    """Wrap a run of sibling list items at the same indent level.
    Continuation lines indented to the text column are joined into
    the item's paragraph and re-wrapped. Items stay verbatim when they
    fit, or when a deeper-indent line follows with no blank between
    (wrapping would cause "Unexpected indentation" in docutils).
    """
    list_indent = _match_list_item(lines[i])[0]
    emitted = []
    while i < n:
        li = _match_list_item(lines[i])
        if not li or li[0] != list_indent:
            break
        _, bullet, rest = li
        # Preserve the bullet-to-text column. ``*  foo`` (col 3) must
        # stay col 3 so nested content at col 2 keeps parsing as a
        # separate block instead of a nested list item.
        text_col = len(lines[i]) - len(rest)
        buf = [rest]
        j = i + 1
        while j < n:
            nxt = lines[j]
            if not nxt.strip():
                break
            nxt_indent = len(nxt) - len(nxt.lstrip(" "))
            # Continuation must be at *exactly* the text column.
            # Deeper indent starts a nested block docutils parses
            # separately.
            if nxt_indent != text_col:
                break
            # A list-item-shaped continuation at text_col is either a
            # malformed nested list or bullet-prefixed prose. Joining
            # would destroy the visible bullet structure; break and let
            # the outer dispatch pass it through verbatim.
            nxt_li = _match_list_item(nxt)
            if nxt_li:
                break
            buf.append(nxt.strip())
            j += 1
        original = [lines[i], *lines[i + 1 : j]]
        # Keep verbatim if a deeper-indented line follows with no blank
        # (splitting would trigger "Unexpected indentation" in docutils).
        next_raw = lines[j] if j < n else ""
        next_indent = len(next_raw) - len(next_raw.lstrip(" "))
        visually_attached = bool(next_raw.strip()) and next_indent > text_col
        # Prose-ambiguity (enum only): ``N.`` followed by a non-sibling
        # line at the list's own indent parses as a paragraph starting
        # with ``N.``, not an enum list. Wrapping would turn it into a
        # real enum and change the doctree. Bullets have no such
        # ambiguity. Keep verbatim.
        nxt_li = _match_list_item(next_raw)
        prose_ambiguity = (
            bullet not in {"-", "*", "+"}
            and bool(next_raw.strip())
            and next_indent == len(list_indent)
            and not (nxt_li and nxt_li[0] == list_indent)
        )
        fits_verbatim = all(len(ln) <= width for ln in original) and not (
            join and len(original) > 1
        )
        # Line-block body (``|`` prefix on each line): merging would
        # destroy the ``<line_block>`` structure. Always verbatim.
        line_block_body = rest.startswith("| ") or rest == "|"
        if (
            fits_verbatim
            or visually_attached
            or prose_ambiguity
            or line_block_body
        ):
            emitted.extend(original)
        else:
            # Keep the source prefix verbatim to preserve the text
            # column. For the subsequent indent, replace bullet chars
            # with spaces but keep whitespace (notably tabs): a source
            # like ``-<TAB>text`` has text column 8, and two spaces
            # would make docutils parse continuations as block_quote.
            initial = lines[i][:text_col]
            subsequent = re.sub(r"\S", " ", initial)
            joined = " ".join(buf)
            wrapped = _wrap_paragraph(joined, width, initial, subsequent)
            candidate = wrapped.split("\n")
            # No-lengthen: if wrapping still produces an over-width
            # line (unsplittable token like a long hyperlink), verbatim.
            if any(len(ln) > width for ln in candidate):
                emitted.extend(original)
            else:
                emitted.extend(candidate)
        i = j
    return emitted, i


def _handle_prose(lines, i, n, width, join):
    """Accumulate and wrap a plain prose paragraph.

    Stops at blank lines, indented lines, explicit markup, table rows,
    underlines, field lists, and standalone '::' markers.
    """
    buf = [lines[i]]
    j = i + 1
    while j < n:
        nxt = lines[j]
        if not nxt.strip():
            break
        if nxt[:1] in {" ", "\t"}:
            break
        if nxt.strip().startswith(".."):
            break
        if nxt.strip()[0] in "+|":
            break
        if _is_underline(nxt):
            break
        if _is_short_underline(nxt):
            break
        if _FIELD_LIST_RE.match(nxt):
            break
        if _OPTION_LIST_RE.match(nxt):
            break
        # A standalone '::' introduces a literal block and must stay on
        # its own line -- merging it turns '::' into ':' in the output.
        if nxt.strip() == "::":
            break
        # A bullet-shaped line inside a paragraph (no preceding
        # blank) is prose continuation, not a new list item.
        buf.append(nxt)
        j += 1
    # Indented-follow guard: an indented non-blank line with no blank
    # between parses as ``paragraph + block_quote`` when multi-line,
    # ``definition_list`` when single-line. Changing the line count
    # would flip that; keep verbatim.
    indented_follow = (
        j < n and lines[j][:1] in {" ", "\t"} and lines[j].strip()
    )
    if indented_follow and len(buf) > 1:
        return buf, j
    joined = " ".join(s.strip() for s in buf)
    normalized = _collapse_spaces(joined)
    # Verbatim only when the paragraph fits and has no double-spaces
    # to collapse. In join mode a multi-line paragraph always re-wraps.
    fits_verbatim = (
        normalized == joined
        and all(len(ln) <= width for ln in buf)
        and not (join and len(buf) > 1)
    )
    if fits_verbatim:
        return buf, j
    wrapped = _wrap_paragraph(normalized, width, "", "")
    candidate = wrapped.split("\n")
    # No-lengthen: if an unsplittable token leaves an over-width line,
    # keep the original verbatim.
    if any(len(ln) > width for ln in candidate):
        return buf, j
    return candidate, j


# ---------------------------------------------------------------------------
# Main rewriter
# ---------------------------------------------------------------------------


def _prepare_lines(source):
    """Split *source* into lines and rstrip each (trailing whitespace
    is never meaningful in RST).
    """
    lines = [ln.rstrip() for ln in source.splitlines()]
    # If the source has no terminating newline but a trailing
    # whitespace-only line, rstripping it to "" would reintroduce a
    # trailing newline on rejoin. Drop empty tails in that case.
    if not source.endswith("\n"):
        while lines and not lines[-1]:
            lines.pop()
    return lines


def _try_verbatim(raw, stripped, lines, i, n):
    """Return ``(emitted, new_i)`` if line *i* passes through
    unchanged (one line, or two for section title+underline), else
    ``None`` and let the caller dispatch.
    """
    # Blank line.
    if not stripped:
        return [raw], i + 1

    # Indented line: literal block, directive body, block quote,
    # nested content. (Indented list items: see _handle_list_run.)
    if raw[:1] in {" ", "\t"}:
        return [raw], i + 1

    # Anonymous hyperlink target ``__ URL`` -- joining into prose
    # would garble the target definition.
    if stripped.startswith("__ "):
        return [raw], i + 1

    # Section title + underline (standard >=3 chars, or 2-char like
    # ``--`` under a 2-letter title).
    if i + 1 < n and (
        _is_underline(lines[i + 1]) or _is_short_underline(lines[i + 1])
    ):
        ul = lines[i + 1].rstrip()
        if len(ul) >= len(stripped):
            return [raw, lines[i + 1]], i + 2

    # Bare underline.
    if _is_underline(raw):
        return [raw], i + 1

    # Bare 2-char underline alone on its line (e.g. ``==`` overline
    # preceding ``rv``). Without this it would merge into prose.
    if _is_short_underline(raw):
        return [raw], i + 1

    # Field list item (e.g. ':Author: Giampaolo', ':type foo:').
    if _FIELD_LIST_RE.match(raw):
        return [raw], i + 1

    # Option list item (e.g. '-f FILE', '--output FILE').
    if _OPTION_LIST_RE.match(raw):
        return [raw], i + 1

    # Grid table row or line-block.
    if stripped[0] in "+|":
        return [raw], i + 1

    return None


def _rewrite_blocks(lines, width, join):
    """Core dispatch loop. Walk *lines*, classify each block, and
    either pass it through verbatim or delegate to a ``_handle_*``
    function. Returns ``(out, protected)`` where *protected* is the
    set of ``out`` indices in simple-table blocks (never mutated by
    later passes).
    """
    out = []
    protected = set()
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # Block-boundary predicate, shared by the indented- and
        # unindented-list dispatches below.
        at_block_start = (
            not out
            or not out[-1].strip()
            or _is_underline(out[-1])
            or _is_short_underline(out[-1])
            or out[-1][:1] in {" ", "\t"}
        )

        # Indented bullet at a block boundary = nested list. Dispatch
        # before _try_verbatim swallows it. Guards: blank-or-start prev
        # line (at_block_start is too broad and mis-fires on bullet-
        # shaped continuations inside literals / prose / ASCII tables);
        # space indent only (tab hits a visually_attached bug that
        # flips the doctree on multi-line parents); not in an opaque
        # block (see _prev_block_is_opaque).
        nested_at_block_start = not out or not out[-1].strip()
        current_indent = len(raw) - len(raw.lstrip(" \t"))
        if (
            raw[:1] == " "
            and stripped
            and nested_at_block_start
            and _match_list_item(raw)
            and not _prev_block_is_opaque(out, current_indent)
        ):
            emitted, i = _handle_list_run(lines, i, n, width, join)
            out.extend(emitted)
            continue

        # Lines that pass through unchanged.
        result = _try_verbatim(raw, stripped, lines, i, n)
        if result is not None:
            emitted, i = result
            out.extend(emitted)
            continue

        # Explicit markup: directive, comment, target, footnote/citation
        # def, substitution def.
        if stripped.startswith(".."):
            emitted, i = _handle_directive(lines, i, n, width, join)
            out.extend(emitted)
            continue

        # Simple table (border of '===' / '---' groups).
        if _is_simple_table_border(raw):
            start = len(out)
            emitted, i = _handle_simple_table(lines, i, n)
            out.extend(emitted)
            protected.update(range(start, len(out)))
            continue

        # Quoted literal block: unindented body after a ``::`` line,
        # every line starting with the same non-alnum quote char. Must
        # come before the list dispatch -- ``*``/``-``/``+`` after
        # ``::`` are quoted literal, not a bullet list.
        first = stripped[0]
        if (
            first.isprintable()
            and not first.isalnum()
            and not first.isspace()
            and _prev_nonblank_ends_with_colons(out)
        ):
            emitted, i = _handle_quoted_literal_block(lines, i, n)
            out.extend(emitted)
            continue

        # List item run (bullet or enumerated) at a block boundary.
        # A bullet directly after unindented prose is a line-wrap
        # continuation, not a new list -- hence at_block_start.
        if at_block_start and _match_list_item(raw):
            emitted, i = _handle_list_run(lines, i, n, width, join)
            out.extend(emitted)
            continue

        # Definition-list term: unindented line with an indented line
        # right after (no blank). Wrapping would split it into two
        # separate terms. The indented body is handled verbatim above.
        if (
            i + 1 < n
            and lines[i + 1][:1] in {" ", "\t"}
            and lines[i + 1].strip()
        ):
            out.append(raw)
            i += 1
            continue

        # Doctest block: consecutive ``>>>`` / ``...`` / output lines.
        if stripped.startswith(">>> ") or stripped == ">>>":
            emitted, i = _handle_doctest(lines, i, n)
            out.extend(emitted)
            continue

        # Plain prose paragraph.
        emitted, i = _handle_prose(lines, i, n, width, join)
        out.extend(emitted)

    return out, protected


def _collapse_blank_lines(out, protected):
    """Collapse consecutive blank lines into one. Blanks are kept
    inside indented blocks and protected blocks (simple tables).
    Rule: on a duplicate blank, peek ahead -- collapse unless the
    next non-blank line is indented.
    """
    collapsed = []
    for idx, ln in enumerate(out):
        if ln.strip():
            collapsed.append(ln)
        else:
            # Never collapse inside protected blocks (simple tables).
            if idx in protected:
                collapsed.append(ln)
                continue
            if collapsed and not collapsed[-1].strip():
                # Previous output line is also blank — collapse
                # unless the next non-blank line is indented.
                next_indented = False
                for k in range(idx + 1, len(out)):
                    if out[k].strip():
                        next_indented = out[k][:1] in {" ", "\t"}
                        break
                if next_indented:
                    collapsed.append(ln)
                continue
            collapsed.append(ln)
    return collapsed


def _finalize(out, source):
    """Join output lines, restoring the trailing newline if the
    source had one (splitlines/join is asymmetric by one separator).
    """
    result = "\n".join(out)
    if source.endswith("\n"):
        result += "\n"
    return result


def wrap_rst(source, width=WIDTH, join=True):
    """Wrap prose paragraphs to *width* and collapse double spaces.
    With *join* True, short consecutive lines in a paragraph / list
    item merge onto one (up to the target width).
    """
    lines = _prepare_lines(source)
    out, protected = _rewrite_blocks(lines, width, join)
    out = _collapse_blank_lines(out, protected)
    return _finalize(out, source)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


class DoctreeParseError(Exception):
    """Raised when docutils fails to parse the RST. Callers treat it
    as "cannot verify": ``--safe`` refuses to write; tests skip.
    """


def _parse_rst(text):
    """Parse *text* with docutils and return the document tree.

    Raises `DoctreeParseError` if docutils fails.
    """
    try:
        import docutils  # noqa: F401
        from docutils.core import publish_doctree
        from docutils.utils import Reporter
    except ImportError:
        print(
            "--safe requires docutils; install with:"
            "  pip install rstwrap[safe]",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return publish_doctree(
            text,
            settings_overrides={
                "report_level": Reporter.SEVERE_LEVEL + 1,
                "halt_level": Reporter.SEVERE_LEVEL + 1,
            },
        )
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        raise DoctreeParseError(msg) from e


def _doctree_diff(src, dst, src_tree=None, dst_tree=None):
    """Return a short unified diff if the doctrees differ, else
    ``None``. Pre-parsed trees can be passed in to skip reparsing;
    trees are deep-copied before normalization. Raises
    `DoctreeParseError` on parse failure.
    """
    import copy

    import docutils.nodes

    if src_tree is None:
        src_tree = _parse_rst(src)
    if dst_tree is None:
        dst_tree = _parse_rst(dst)

    def _norm(tree):
        tree = copy.deepcopy(tree)
        # Materialize before mutating -- removing nodes during
        # ``findall`` iteration skips siblings.
        for node in list(tree.findall(docutils.nodes.system_message)):
            node.parent.remove(node)
        for node in tree.findall(docutils.nodes.Element):
            node.attributes.pop("source", None)
            node.attributes.pop("line", None)
            node.line = None
        for node in list(tree.findall(docutils.nodes.Text)):
            normalized = " ".join(str(node).split())
            node.parent.replace(node, docutils.nodes.Text(normalized))
        return tree.pformat()

    s1 = _norm(src_tree)
    s2 = _norm(dst_tree)
    if s1 == s2:
        return None
    return "\n".join(
        difflib.unified_diff(
            s1.splitlines(),
            s2.splitlines(),
            fromfile="source doctree",
            tofile="output doctree",
            lineterm="",
            n=2,
        )
    )


def _collect_rst_files(path):
    """Yield .rst files under *path*. A file is returned as-is; a
    directory is walked recursively, skipping IGNORED_DIRS.
    """
    if path.is_file():
        yield path
        return
    dirs = [path]
    while dirs:
        current = dirs.pop()
        for entry in sorted(current.iterdir()):
            if entry.is_dir():
                if entry.name not in IGNORED_DIRS:
                    dirs.append(entry)
            elif entry.suffix == ".rst":
                yield entry


def _safety_check_failed(src, dst, label):
    """Run the ``--safe`` post-check. On mismatch or parse error,
    print diagnostics and return True (caller should skip writing).
    """
    if not SAFE or src == dst:
        return False
    try:
        tree_diff = _doctree_diff(src, dst)
    except DoctreeParseError as e:
        print(
            f"{label}: --safe check failed; docutils could not parse"
            f" the RST ({e}); nothing written",
            file=sys.stderr,
        )
        return True
    if tree_diff is None:
        return False
    print(
        f"{label}: --safe check failed; output doctree differs from"
        " source; nothing written",
        file=sys.stderr,
    )
    print(tree_diff, file=sys.stderr)
    return True


def _process(src, *, label, diff_dst_label, write_fn, log_changes):
    """Shared core for file and stdin processing.
    Returns (changed, safety_failed).
    """
    dst = wrap_rst(src, WIDTH, join=JOIN)
    changed = dst != src
    if _safety_check_failed(src, dst, label):
        return changed, True
    if DIFF:
        if changed:
            diff_lines = difflib.unified_diff(
                src.splitlines(keepends=True),
                dst.splitlines(keepends=True),
                fromfile=label,
                tofile=diff_dst_label,
            )
            if COLOR:
                diff_lines = _colorize_diff(diff_lines)
            sys.stdout.writelines(diff_lines)
        return changed, False
    if CHECK:
        if changed and log_changes and not QUIET:
            print(f"would reformat {label}")
        return changed, False
    if changed:
        write_fn(dst)
        if log_changes and not QUIET:
            print(f"reformatted {label}")
    return changed, False


def _process_file(path):
    src = path.read_text(encoding="utf-8")
    return _process(
        src,
        label=str(path),
        diff_dst_label=str(path),
        write_fn=lambda dst: path.write_text(dst, encoding="utf-8"),
        log_changes=True,
    )


def _process_stdin():
    src = sys.stdin.read()
    dst = wrap_rst(src, WIDTH, join=JOIN)
    changed = dst != src
    if _safety_check_failed(src, dst, "<stdin>"):
        return changed, True
    if DIFF:
        if changed:
            diff_lines = difflib.unified_diff(
                src.splitlines(keepends=True),
                dst.splitlines(keepends=True),
                fromfile="<stdin>",
                tofile="<stdout>",
            )
            if COLOR:
                diff_lines = _colorize_diff(diff_lines)
            sys.stdout.writelines(diff_lines)
        return changed, False
    if CHECK:
        return changed, False
    # Always write to stdout: editor integrations replace the buffer
    # with it and would blank the view for an already-clean file.
    sys.stdout.write(dst)
    return changed, False


# ``[tool.rstwrap]`` keys and their expected types. ``check`` /
# ``diff`` are CLI-only (per-invocation flags, not project policy).
_VALID_PYPROJECT_KEYS = {
    "width": int,
    "join": bool,
    "safe": bool,
}


def _find_pyproject_toml():
    """Walk up from CWD looking for pyproject.toml; return Path or None."""
    cwd = Path.cwd().resolve()
    for d in (cwd, *cwd.parents):
        candidate = d / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def _config_error(msg):
    """Print *msg* to stderr and exit with code 2 (config error)."""
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def _load_pyproject_config():
    """Return validated options from ``[tool.rstwrap]`` in the
    nearest pyproject.toml, or ``{}``. Unknown keys or wrong types
    exit with code 2.
    """
    path = _find_pyproject_toml()
    if path is None:
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        return _config_error(f"cannot read {path}: {e}")
    section = data.get("tool", {}).get("rstwrap", {})
    valid = {}
    for k, v in section.items():
        expected = _VALID_PYPROJECT_KEYS.get(k)
        if expected is None:
            valid_keys = ", ".join(sorted(_VALID_PYPROJECT_KEYS))
            return _config_error(
                f"unknown key in [tool.rstwrap] in {path}: {k!r}"
                f" (valid keys: {valid_keys})"
            )
        # bool is a subclass of int -- reject True/False for width.
        if expected is int and (isinstance(v, bool) or not isinstance(v, int)):
            return _config_error(
                f"[tool.rstwrap].{k} in {path} must be an integer,"
                f" got {type(v).__name__}"
            )
        if expected is bool and not isinstance(v, bool):
            return _config_error(
                f"[tool.rstwrap].{k} in {path} must be a boolean,"
                f" got {type(v).__name__}"
            )
        valid[k] = v
    return valid


def parse_cli(args=None):
    global WIDTH, CHECK, COLOR, DIFF, JOIN, SAFE, QUIET, PATHS

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=79,
        help="maximum line length (default: 79)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any file would be changed; do not write",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="print a unified diff instead of writing files",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="colorize diff output (default: auto)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help=(
            "suppress per-file 'reformatted FILE' / 'would reformat FILE'"
            " messages; errors and diffs are still printed"
        ),
    )
    parser.add_argument(
        "--join",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "merge short consecutive lines inside a paragraph onto one"
            " line, up to the target width (default: on)"
        ),
    )
    parser.add_argument(
        "--safe",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "after wrapping, verify with docutils that the output has"
            " the same document tree as the input; refuse to write"
            " files whose tree would change (requires docutils)"
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help=(
            "one or more .rst files or directories to format;"
            " use '-' to read from stdin and write to stdout"
        ),
    )
    # Apply [tool.rstwrap] from pyproject.toml as defaults; the
    # CLI then overrides anything explicitly passed.
    config = _load_pyproject_config()
    if config:
        parser.set_defaults(**config)
    args = parser.parse_args(args)
    WIDTH = args.width
    CHECK = args.check
    DIFF = args.diff
    JOIN = args.join
    SAFE = args.safe
    QUIET = args.quiet
    if args.color == "always":
        COLOR = True
    elif args.color == "never":
        COLOR = False
    else:
        COLOR = sys.stdout.isatty()

    stdin_requested = any(str(p) == "-" for p in args.paths)
    if stdin_requested and len(args.paths) > 1:
        parser.error("'-' (stdin) cannot be combined with other paths")

    collected = set()
    for path in args.paths:
        if str(path) == "-":
            collected.add(path)
        else:
            collected.update(_collect_rst_files(path))
    PATHS = sorted(collected, key=str)


def main(args=None):
    parse_cli(args)

    if len(PATHS) == 1 and str(PATHS[0]) == "-":
        changed, safety_failed = _process_stdin()
        if safety_failed or (CHECK and changed):
            sys.exit(1)
        return

    n_changed = 0
    n_unchanged = 0
    n_safety_failed = 0
    for path in PATHS:
        changed, safety_failed = _process_file(path)
        if safety_failed:
            n_safety_failed += 1
        elif changed:
            n_changed += 1
        else:
            n_unchanged += 1

    # Multi-file summary (skipped under --quiet, --diff, single-file).
    if len(PATHS) > 1 and not QUIET and not DIFF:
        verb = "would be reformatted" if CHECK else "reformatted"
        parts = [f"{n_changed} {verb}", f"{n_unchanged} unchanged"]
        if n_safety_failed:
            parts.append(f"{n_safety_failed} skipped (--safe)")
        print(", ".join(parts) + ".")

    if n_safety_failed or (CHECK and n_changed):
        sys.exit(1)


if __name__ == "__main__":
    main()
