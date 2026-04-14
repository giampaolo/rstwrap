#!/usr/bin/env python3

"""Wrap RST prose paragraphs to a maximum line length.

Only prose paragraphs and list items are re-wrapped. Everything else
(directives, literal blocks, tables, section underlines, comments,
indented blocks) is passed through byte-identical. Inline RST
constructs that contain internal whitespace (``like this``,
:role:`display <target>`, `text <url>`_, *emphasis*, **bold**, ...)
are treated as atomic tokens and never broken across lines.

Redundant internal spaces in prose paragraphs are collapsed to a
single space (e.g. ``hello  world`` → ``hello world``). Inline RST
constructs that intentionally contain spaces (`` ``like  this`` ``,
``*two  words*``) are protected and left intact.

If a paragraph already fits within the target width and contains no
redundant spaces, it is emitted unchanged -- so clean files produce a
zero-byte diff.

Limitations
-----------
Prose-body directives (``.. class::``, ``.. method::``, ``.. note::``,
``.. warning::``, ``.. versionadded::``, ...) have their body
recursively wrapped at the body's own indent. Other directives are
treated as opaque -- the marker line plus all following indented lines
are passed through verbatim. This keeps us safe on literal-body
directives (``.. code-block::``, ``.. literalinclude::``, ``.. raw::``,
``.. image::``, ...) without hand-maintaining their content models.
The whitelist lives in ``_PROSE_BODY_DIRECTIVES`` below.

Other indented content at column 0 is passed through verbatim:

- Literal blocks (indented block introduced by ``::``).
- Block quotes.
- Bare nested list items (a bullet that's not inside a prose-body
  directive cannot be told apart from a directive-body item without
  parser-level context).

Additionally:

- Definition-list terms are passed through verbatim -- wrapping would
  split one term across two unindented lines, producing two terms in
  the parsed document.
- Tables (both grid and simple) are passed through verbatim.

This tool is a minimal-diff wrapper for prose paragraphs, not a
general-purpose RST formatter.

Usage::

    python3 scripts/internal/rst_wrap_lines.py docs/*.rst
    python3 scripts/internal/rst_wrap_lines.py --check docs/*.rst
    python3 scripts/internal/rst_wrap_lines.py --width 80 foo.rst
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# CLI (module-scope constants, per project guidelines)
# ---------------------------------------------------------------------------

WIDTH = 79
CHECK = False
DIFF = False
PATHS = []


# ---------------------------------------------------------------------------
# Inline-token recognition
# ---------------------------------------------------------------------------

# Inline RST constructs that must NEVER be broken across lines. Order
# matters: longer / more specific alternatives come first so the regex
# engine matches them in preference to shorter ones at the same
# position. Each alternative is anchored at a non-space position.
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
    """Mask inline RST constructs that contain internal whitespace.

    Returns (masked_text, placeholders). Constructs without any
    internal whitespace are left alone -- they are already atomic
    under whitespace-based splitting.
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
    """Collapse redundant internal spaces in prose text.

    Spaces inside inline RST constructs (``like  this``, *two  words*)
    are intentional and left intact. Spaces between words in plain prose
    are normalized to a single space.
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

_UNDERLINE_CHARS = frozenset("=-~^\"'`#+<>_*:.!?")

# Directive with ``::`` terminator. Optional domain prefix (``py:``,
# ``c:``, ...). Group 1 is the bare directive name (used for the
# prose-body whitelist below).
_DIRECTIVE_RE = re.compile(r"^\.\.\s+(?:[\w-]+:)?([\w-]+)::")

# Directives whose body is prose (and therefore wrappable). Anything
# not in this set is treated as opaque -- we don't know its content
# model, so we pass the body through verbatim.
_PROSE_BODY_DIRECTIVES = frozenset(
    {
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
    }
)

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
    r"|\(\d+\)"  # (1)
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


# Field list item: ':field name: value'. Field names may contain spaces
# (e.g. ':type exc_info:') but never backticks, which distinguishes
# them from ':role:`text`' inline markup (a role is always followed by
# a backtick, not a space).
_FIELD_LIST_RE = re.compile(r"^:[^`:\n]+:(?:\s|$)")


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


def _handle_directive(lines, i, n, width):
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
        if indent and all(not ln.strip() or ln.startswith(indent) for ln in body):
            dedented = "\n".join(ln[len(indent) :] if ln.strip() else "" for ln in body)
            sub_width = max(1, width - len(indent))
            wrapped = wrap_rst(dedented, sub_width)
            emitted.extend(indent + ln if ln else "" for ln in wrapped.split("\n"))
        else:
            emitted.extend(body)
    else:
        emitted.extend(body)
    return emitted, i


def _handle_simple_table(lines, i, n):
    """Collect a simple-table block verbatim (border to closing border)."""
    emitted = [lines[i]]
    i += 1
    while i < n:
        emitted.append(lines[i])
        if _is_simple_table_border(lines[i]) and (
            i + 1 >= n or not lines[i + 1].strip()
        ):
            i += 1
            break
        i += 1
    return emitted, i


def _handle_list_run(lines, i, n, width):
    """Wrap a run of sibling list items at the same indent level.

    A "run" is a sequence of consecutive bullets with no blank line
    between them. Each item's continuation lines (indented exactly to
    the text column) are joined into the item's paragraph and
    re-wrapped. Items are kept verbatim when they already fit or when a
    visually-aligned continuation follows immediately (deeper indent
    with no blank line -- wrapping would cause "Unexpected indentation"
    in docutils).
    """
    list_indent = _match_list_item(lines[i])[0]
    emitted = []
    while i < n:
        li = _match_list_item(lines[i])
        if not li or li[0] != list_indent:
            break
        indent, bullet, rest = li
        text_col = len(indent) + len(bullet) + 1
        buf = [rest]
        j = i + 1
        while j < n:
            nxt = lines[j]
            if not nxt.strip():
                break
            nxt_indent = len(nxt) - len(nxt.lstrip(" "))
            # Continuation must be indented to *exactly* the text
            # column. Deeper indent starts a nested structure (block
            # quote, nested paragraph, definition list) that docutils
            # parses separately.
            if nxt_indent != text_col:
                break
            if _match_list_item(nxt):
                break
            buf.append(nxt.strip())
            j += 1
        original = [lines[i], *lines[i + 1 : j]]
        # Fidelity guard: keep verbatim if already fits, or if a
        # visually-aligned over-indented line follows immediately
        # (splitting the item would orphan it without a blank line,
        # causing "Unexpected indentation" in docutils).
        next_raw = lines[j] if j < n else ""
        next_indent = len(next_raw) - len(next_raw.lstrip(" "))
        visually_attached = bool(next_raw.strip()) and next_indent > text_col
        if all(len(ln) <= width for ln in original) or visually_attached:
            emitted.extend(original)
        else:
            initial = indent + bullet + " "
            subsequent = " " * text_col
            joined = " ".join(buf)
            wrapped = _wrap_paragraph(joined, width, initial, subsequent)
            emitted.extend(wrapped.split("\n"))
        i = j
    return emitted, i


def _handle_prose(lines, i, n, width):
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
        if _FIELD_LIST_RE.match(nxt):
            break
        # A standalone '::' introduces a literal block and must stay on
        # its own line -- merging it turns '::' into ':' in the output.
        if nxt.strip() == "::":
            break
        # A line matching the bullet pattern inside a paragraph (no
        # preceding blank) is prose continuation, not a new list item.
        buf.append(nxt)
        j += 1
    joined = " ".join(s.strip() for s in buf)
    normalized = _collapse_spaces(joined)
    # Fidelity guard: keep verbatim only if the paragraph already fits
    # *and* has no redundant spaces to normalize.
    if normalized == joined and all(len(ln) <= width for ln in buf):
        return buf, j
    wrapped = _wrap_paragraph(normalized, width, "", "")
    return wrapped.split("\n"), j


# ---------------------------------------------------------------------------
# Main rewriter
# ---------------------------------------------------------------------------


def wrap_rst(source, width=WIDTH):
    """Return *source* with prose paragraphs wrapped to *width*."""
    lines = source.splitlines()
    out = []
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # Blank line.
        if not stripped:
            out.append(raw)
            i += 1
            continue

        # Indented line: literal block, directive body, nested content,
        # block quote. Pass through verbatim. (Indented list items are
        # not wrapped; see _handle_list_run for why.)
        if raw[:1] in {" ", "\t"}:
            out.append(raw)
            i += 1
            continue

        # Explicit markup: directive, comment, target, footnote/citation
        # def, substitution def.
        if stripped.startswith(".."):
            emitted, i = _handle_directive(lines, i, n, width)
            out.extend(emitted)
            continue

        # Section title followed by an underline of equal/greater length.
        if i + 1 < n and _is_underline(lines[i + 1]):
            ul = lines[i + 1].rstrip()
            if len(ul) >= len(stripped):
                out.extend((raw, lines[i + 1]))
                i += 2
                continue

        # Bare underline (overline already handled above).
        if _is_underline(raw):
            out.append(raw)
            i += 1
            continue

        # Field list item (e.g. ':Author: Giampaolo', ':type foo:').
        if _FIELD_LIST_RE.match(raw):
            out.append(raw)
            i += 1
            continue

        # Grid table row or line-block.
        if stripped[0] in "+|":
            out.append(raw)
            i += 1
            continue

        # Simple table (border of '===' / '---' groups).
        if _is_simple_table_border(raw):
            emitted, i = _handle_simple_table(lines, i, n)
            out.extend(emitted)
            continue

        # List item run (bullet or enumerated). Only recognised at block
        # start (preceded by blank line or document start) -- a bullet
        # mid-paragraph is prose continuation.
        if (not out or not out[-1].strip()) and _match_list_item(raw):
            emitted, i = _handle_list_run(lines, i, n, width)
            out.extend(emitted)
            continue

        # Definition-list term: unindented line immediately followed by
        # an indented line with no blank between. Wrapping the term
        # would create two separate terms in the parsed document.
        if i + 1 < n and lines[i + 1][:1] in {" ", "\t"} and lines[i + 1].strip():
            out.append(raw)
            i += 1
            continue

        # Plain prose paragraph.
        emitted, i = _handle_prose(lines, i, n, width)
        out.extend(emitted)

    result = "\n".join(out)
    # splitlines() + '\n'.join() is asymmetric by exactly one trailing
    # separator: restore it so trailing blank lines are byte-identical.
    if source.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _process_file(path):
    src = path.read_text(encoding="utf-8")
    dst = wrap_rst(src, WIDTH)
    changed = dst != src
    if DIFF:
        if changed:
            diff = difflib.unified_diff(
                src.splitlines(keepends=True),
                dst.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
            )
            sys.stdout.writelines(diff)
        return changed
    if CHECK:
        if changed:
            print(f"would reformat {path}")
        return changed
    if changed:
        path.write_text(dst, encoding="utf-8")
        print(f"reformatted {path}")
    return changed


def parse_cli():
    global WIDTH, CHECK, DIFF, PATHS
    parser = argparse.ArgumentParser(
        description="Wrap RST prose paragraphs to a max line length."
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
        "paths", nargs="+", type=Path, help="one or more .rst files to format"
    )
    args = parser.parse_args()
    WIDTH = args.width
    CHECK = args.check
    DIFF = args.diff
    PATHS = args.paths


def main():
    parse_cli()
    any_changed = False
    for path in PATHS:
        if _process_file(path):
            any_changed = True
    if CHECK and any_changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
