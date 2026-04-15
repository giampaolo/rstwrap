#!/usr/bin/env python3

"""Wrap RST prose paragraphs to a maximum line length.

Example usages:

    rst-wrap-lines docs/*.rst
    rst-wrap-lines docs/                # recurse into a directory
    rst-wrap-lines --check docs/*.rst
    rst-wrap-lines --diff docs/*.rst    # print unified diff, don't write
    rst-wrap-lines --width 80 foo.rst
    rst-wrap-lines --join docs/*.rst    # also merge short lines onto one
    rst-wrap-lines --safe docs/*.rst    # verify doctree via docutils
    cat foo.rst | rst-wrap-lines -      # read from stdin, write to stdout
"""

import argparse
import difflib
import importlib.metadata
import re
import sys
import tomllib
from pathlib import Path

try:
    __version__ = importlib.metadata.version("rst-wrap-lines")
except importlib.metadata.PackageNotFoundError:
    # Running from source without install (e.g. python3 rst_wrap_lines.py).
    __version__ = "unknown"

# ---------------------------------------------------------------------------
# CLI (module-scope constants, per project guidelines)
# ---------------------------------------------------------------------------

WIDTH = 79
CHECK = False
DIFF = False
JOIN = False
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
    """True if the line is a 1-2 char section underline (e.g. ``--``
    under a 2-letter module name like ``io``, or ``-`` under a 1-letter
    title like ``R``).

    Excludes ``::``, ``..``, and bare ``:`` / ``.`` which have
    dedicated meanings elsewhere.
    """
    s = line.rstrip()
    if len(s) not in (1, 2) or s in {"::", "..", ":", "."}:
        return False
    c = s[0]
    return c in _UNDERLINE_CHARS and all(ch == c for ch in s)


# Field list item: ':field name: value'. Field names may contain spaces
# (e.g. ':type exc_info:') and inline markup including inline literals
# (e.g. ':``p_vaddr``: segment virtual address'). Disambiguation from
# ':role:`text`' inline markup is handled by the trailing ``(?:\s|$)``:
# a field list has a space (or end of line) after the closing colon,
# while a role is immediately followed by a backtick.
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
    """Collect a simple-table block verbatim (border to closing border).

    A simple table may contain a nested simple table inside one of its
    cells; the nested table's closing border is indented relative to
    the outer table. Only a same-indent border followed by a blank
    line counts as the outer closer.
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
    """Collect a quoted literal block verbatim.

    A quoted literal block follows a paragraph ending in ``::`` (same
    as a regular literal block), but its body is unindented: every line
    begins with the same non-alphanumeric, non-whitespace quoting
    character. Docutils treats the whole run as literal; we must pass
    it through without wrapping or merging.
    """
    quote_char = lines[i][0]
    emitted = []
    while i < n and lines[i][:1] == quote_char:
        emitted.append(lines[i])
        i += 1
    return emitted, i


def _prev_nonblank_ends_with_colons(out):
    """True if the last non-blank line in *out* ends with ``::``."""
    for ln in reversed(out):
        if ln.strip():
            return ln.rstrip().endswith("::")
    return False


def _handle_list_run(lines, i, n, width, join):
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
            nxt_li = _match_list_item(nxt)
            if nxt_li and nxt_li[0] == list_indent:
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
        # Prose-ambiguity guard (enum lists only): a numbered marker
        # followed by a non-blank line at the list's own indent (less
        # than text_col) that is not a sibling list item is parsed by
        # docutils as a paragraph starting with "N.", not as an enum
        # list. Bullet lists don't have this ambiguity -- docutils
        # always parses ``*``/``-``/``+`` as a list. Wrapping in the
        # ambiguous case would create a well-formed enum list and
        # change the doctree; keep verbatim instead.
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
        # Line-block body: the item's body is an RST line block (each
        # line prefixed with ``|``). Merging those lines into a single
        # paragraph destroys the ``<line_block>`` structure, so always
        # keep such items verbatim regardless of width or ``--join``.
        line_block_body = rest.startswith("| ") or rest == "|"
        if (
            fits_verbatim
            or visually_attached
            or prose_ambiguity
            or line_block_body
        ):
            emitted.extend(original)
        else:
            initial = indent + bullet + " "
            subsequent = " " * text_col
            joined = " ".join(buf)
            wrapped = _wrap_paragraph(joined, width, initial, subsequent)
            candidate = wrapped.split("\n")
            # No-lengthen guard: if wrapping would produce a line longer
            # than width (e.g. because a long inline token such as a
            # hyperlink cannot be split), keep the original verbatim.
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
        # A line matching the bullet pattern inside a paragraph (no
        # preceding blank) is prose continuation, not a new list item.
        buf.append(nxt)
        j += 1
    # Indented-follow guard: if the paragraph is immediately followed
    # (no blank line between) by an indented non-blank line, docutils
    # parses it as ``paragraph + block_quote`` when the paragraph is
    # multi-line, but as ``definition_list`` when it is single-line.
    # Merging or re-wrapping to a different line count would flip that
    # interpretation, so keep the paragraph verbatim. Triggers on
    # malformed RST (valid RST has a blank line before indented
    # content), but the doctree invariant must still hold.
    indented_follow = (
        j < n and lines[j][:1] in {" ", "\t"} and lines[j].strip()
    )
    if indented_follow and len(buf) > 1:
        return buf, j
    joined = " ".join(s.strip() for s in buf)
    normalized = _collapse_spaces(joined)
    # Fidelity guard: keep verbatim only if the paragraph already fits
    # *and* has no redundant spaces to normalize. In join mode a
    # multi-line paragraph is always re-wrapped so short consecutive
    # lines merge onto one.
    fits_verbatim = (
        normalized == joined
        and all(len(ln) <= width for ln in buf)
        and not (join and len(buf) > 1)
    )
    if fits_verbatim:
        return buf, j
    wrapped = _wrap_paragraph(normalized, width, "", "")
    candidate = wrapped.split("\n")
    # No-lengthen guard: if wrapping would produce a line longer than
    # width (e.g. because a long inline token such as a hyperlink or
    # role cannot be split), keep the original verbatim.
    if any(len(ln) > width for ln in candidate):
        return buf, j
    return candidate, j


# ---------------------------------------------------------------------------
# Main rewriter
# ---------------------------------------------------------------------------


def wrap_rst(source, width=WIDTH, join=False):
    """Wrap prose paragraphs to *width* and remove double spaces.

    With *join* True, short consecutive lines inside a prose paragraph
    or list item are merged onto one line (up to the target width).
    Default False preserves the existing line breaks.
    """
    # Strip trailing whitespace from every line up front. It's never
    # meaningful in RST (the doctree ignores it) and stripping here
    # means downstream handlers can't accidentally preserve it.
    lines = [ln.rstrip() for ln in source.splitlines()]
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
            emitted, i = _handle_directive(lines, i, n, width, join)
            out.extend(emitted)
            continue

        # Anonymous hyperlink target: ``__ URL``. Must be preserved
        # verbatim -- joining it into surrounding prose would turn the
        # target definition into garbled text.
        if stripped.startswith("__ "):
            out.append(raw)
            i += 1
            continue

        # Section title followed by an underline of equal/greater
        # length. Both standard underlines (>=3 chars) and 2-char
        # underlines (e.g. ``--`` under a 2-letter title like ``CF``)
        # are accepted.
        if i + 1 < n and (
            _is_underline(lines[i + 1])
            or _is_short_underline(lines[i + 1])
        ):
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

        # Bare 2-char underline on its own line (e.g. ``==`` overline
        # preceding a short title like ``rv``). Without this passthrough
        # the line falls into prose and merges with the title.
        if _is_short_underline(raw):
            out.append(raw)
            i += 1
            continue

        # Field list item (e.g. ':Author: Giampaolo', ':type foo:').
        if _FIELD_LIST_RE.match(raw):
            out.append(raw)
            i += 1
            continue

        # Option list item (e.g. '-f FILE', '--output FILE').
        if _OPTION_LIST_RE.match(raw):
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

        # List item run (bullet or enumerated). Recognised at block
        # boundaries: blank line, section underline, or after indented
        # content (nested body, continuation paragraph). A bullet that
        # directly follows unindented prose is a line-wrap continuation,
        # not a new list.
        at_block_start = (
            not out
            or not out[-1].strip()
            or _is_underline(out[-1])
            or out[-1][:1] in {" ", "\t"}
        )
        if at_block_start and _match_list_item(raw):
            emitted, i = _handle_list_run(lines, i, n, width, join)
            out.extend(emitted)
            continue

        # Definition-list term: unindented line immediately followed by
        # an indented line with no blank between. Wrapping the term
        # would create two separate terms in the parsed document. The
        # body (indented lines) is handled verbatim by the indented-
        # block branch above.
        if (
            i + 1 < n
            and lines[i + 1][:1] in {" ", "\t"}
            and lines[i + 1].strip()
        ):
            out.append(raw)
            i += 1
            continue

        # Quoted literal block: unindented body introduced by ``::``
        # in the previous paragraph, every line starting with the same
        # non-alphanumeric, non-whitespace quoting character. Pass the
        # run through verbatim -- docutils treats it as literal.
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

        # Plain prose paragraph.
        emitted, i = _handle_prose(lines, i, n, width, join)
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


def _doctree_diff(src, dst):
    """Return a short unified diff if the doctrees of *src* and *dst*
    differ, otherwise ``None``.

    Used by the ``--safe`` post-check: parse both texts with docutils,
    compare after stripping source-position attributes and normalizing
    whitespace inside Text nodes. docutils is imported lazily so users
    who don't opt in don't pay the import cost.
    """
    try:
        import docutils.nodes
        from docutils.core import publish_doctree
        from docutils.utils import Reporter
    except ImportError:
        print(
            "--safe requires docutils; install with:"
            "  pip install rst-wrap-lines[safe]",
            file=sys.stderr,
        )
        sys.exit(2)

    def _norm(text):
        tree = publish_doctree(
            text,
            settings_overrides={
                "report_level": Reporter.SEVERE_LEVEL + 1,
                "halt_level": Reporter.SEVERE_LEVEL + 1,
            },
        )
        # ``findall`` returns a generator; removing/replacing nodes
        # during iteration causes the traversal to skip siblings.
        # Materialize before mutating.
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

    s1 = _norm(src)
    s2 = _norm(dst)
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
    """Return a list of .rst files for *path*.

    If *path* is a file, return it as-is (a single-element list).
    If *path* is a directory, recursively collect all .rst files,
    skipping subdirectories whose name is in IGNORED_DIRS.
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
    """Run ``--safe`` post-check; on doctree mismatch, emit stderr
    diagnostics and return True so the caller can skip writing.
    """
    if not SAFE or src == dst:
        return False
    tree_diff = _doctree_diff(src, dst)
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
            sys.stdout.writelines(
                difflib.unified_diff(
                    src.splitlines(keepends=True),
                    dst.splitlines(keepends=True),
                    fromfile=label,
                    tofile=diff_dst_label,
                )
            )
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
    return _process(
        src,
        label="<stdin>",
        diff_dst_label="<stdout>",
        write_fn=sys.stdout.write,
        log_changes=False,
    )


# Options that ``[tool.rst-wrap-lines]`` in pyproject.toml may set,
# mapped to the type each value must have. ``check`` and ``diff`` are
# intentionally CLI-only -- they're per-invocation flags, not project
# policy.
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
    """Return validated options from ``[tool.rst-wrap-lines]`` in the
    nearest pyproject.toml, or an empty dict if none is found.

    Unknown keys and wrong-typed values are fatal: print an error to
    stderr and exit with code 2. This catches typos early instead of
    silently ignoring them.
    """
    path = _find_pyproject_toml()
    if path is None:
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        return _config_error(f"cannot read {path}: {e}")
    section = data.get("tool", {}).get("rst-wrap-lines", {})
    valid = {}
    for k, v in section.items():
        expected = _VALID_PYPROJECT_KEYS.get(k)
        if expected is None:
            valid_keys = ", ".join(sorted(_VALID_PYPROJECT_KEYS))
            return _config_error(
                f"unknown key in [tool.rst-wrap-lines] in {path}: {k!r}"
                f" (valid keys: {valid_keys})"
            )
        # bool is a subclass of int -- reject True/False for width.
        if expected is int and (isinstance(v, bool) or not isinstance(v, int)):
            return _config_error(
                f"[tool.rst-wrap-lines].{k} in {path} must be an integer,"
                f" got {type(v).__name__}"
            )
        if expected is bool and not isinstance(v, bool):
            return _config_error(
                f"[tool.rst-wrap-lines].{k} in {path} must be a boolean,"
                f" got {type(v).__name__}"
            )
        valid[k] = v
    return valid


def parse_cli(args=None):
    global WIDTH, CHECK, DIFF, JOIN, SAFE, QUIET, PATHS

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
        default=False,
        help=(
            "merge short consecutive lines inside a paragraph onto one"
            " line, up to the target width"
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
    # Apply [tool.rst-wrap-lines] from pyproject.toml as defaults; the
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

    # Summary on multi-file runs (skipped under --quiet, --diff, and
    # for single-file invocations where the per-file output is enough).
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
