"""Tests run against .rst files from multiple sources.

Currently includes:
- Local regression fixtures (tests/rst/, always present)
- CPython documentation (Doc/, ~600 files)
- Sphinx documentation (doc/, ~100 files)
- SQLAlchemy documentation (doc/build/)
- pytest documentation (doc/en/)
- Linux kernel documentation (Documentation/)
- Python PEPs (peps/)
- Ansible documentation (docs/docsite/rst/)
- NumPy documentation (doc/source/)
- Salt documentation (doc/)

Each .rst file is a separate parametrized test item, so that
pytest-xdist can distribute them across workers.

The external repos are cloned once (sparse) into temp directories and
reused across runs. Cloning is triggered in conftest.py during
collection setup, **before** pytest-xdist spawns worker processes.

Adding a regression test: drop a .rst file into tests/rst/ and it
will be picked up automatically on the next run.
"""

import pathlib
import re

import docutils.nodes
import pytest

import rst_wrap_lines
from rst_wrap_lines import _DIRECTIVE_RE as _TOOL_DIRECTIVE_RE
from rst_wrap_lines import WIDTH
from rst_wrap_lines import DoctreeParseError
from rst_wrap_lines import _doctree_diff
from rst_wrap_lines import _parse_rst
from rst_wrap_lines import wrap_rst

from . import _UNDERLINE_RE
from . import BaseTest
from . import has_bare_double_space
from .conftest import ANSIBLE_CLONE_DIR
from .conftest import CLONE_DIR
from .conftest import LINUX_CLONE_DIR
from .conftest import NUMPY_CLONE_DIR
from .conftest import PEPS_CLONE_DIR
from .conftest import PYTEST_CLONE_DIR
from .conftest import SALT_CLONE_DIR
from .conftest import SPHINX_CLONE_DIR
from .conftest import SQLALCHEMY_CLONE_DIR

# Matches the bullet prefix of a list item at any indent (bullet char
# followed by one or more spaces). Used in test_all to skip the
# general double-space check on list-item lines -- list items may
# legitimately have 2+ spaces between the bullet and the text.
LIST_ITEM_LEAD_RE = re.compile(r"^\s*([-*+]|\d+[.)]|\(\d+\)|#\.)\s+")

# Directives whose body is code or verbatim content that must pass
# through unchanged.  Used to identify *real* code blocks among the
# literal_block nodes that docutils produces for unknown directives
# (without Sphinx every unknown directive body becomes a literal
# block).  Anything NOT in this set is assumed to be prose, metadata,
# or structural content — safe to skip when verifying code-block
# preservation.
CODE_BODY_DIRECTIVES = frozenset({
    # Standard code display
    "code-block",
    "code",
    "sourcecode",
    "highlight",
    "literalinclude",
    "parsed-literal",
    # Raw / math
    "raw",
    "math",
    # Sphinx testing
    "doctest",
    "testcode",
    "testoutput",
    "testsetup",
    "testcleanup",
    # Misc code-body
    "ipython",
    "try_examples",
    "productionlist",
    "grammar-snippet",
    # Graphviz
    "graphviz",
    "digraph",
    "graph",
})

_LOCAL_RST_DIR = pathlib.Path(__file__).parent / "rst"

_SOURCES = [
    (_LOCAL_RST_DIR, "local"),
    (CLONE_DIR / "Doc", "cpython"),
    (SPHINX_CLONE_DIR / "doc", "sphinx"),
    (SQLALCHEMY_CLONE_DIR / "doc" / "build", "sqlalchemy"),
    (PYTEST_CLONE_DIR / "doc" / "en", "pytest"),
    (LINUX_CLONE_DIR / "Documentation", "linux"),
    (PEPS_CLONE_DIR / "peps", "peps"),
    (ANSIBLE_CLONE_DIR / "docs" / "docsite" / "rst", "ansible"),
    (NUMPY_CLONE_DIR / "doc" / "source", "numpy"),
    (SALT_CLONE_DIR / "doc", "salt"),
]

# Build (path, id_string) pairs so that files with the same name from
# different repos get distinct parametrize ids (e.g. "cpython/index.rst"
# vs "sphinx/index.rst").
_RST_FILE_PARAMS = [
    pytest.param(path, id=f"{label}/{path.name}")
    for doc_dir, label in _SOURCES
    for path in sorted(doc_dir.rglob("*.rst"))
]
assert _RST_FILE_PARAMS

# Plain list used where only the paths are needed.
RST_FILES = [p.values[0] for p in _RST_FILE_PARAMS]


class TestCorpus(BaseTest):
    """Run wrap_rst() against every collected .rst file and verify
    basic invariants: idempotency, no tool-produced line exceeds the
    target width, no bare double-space in tool-produced prose.

    The integration corpus runs with ``join=True`` so the short-line
    merge path is exercised against every upstream project's docs.
    """

    JOIN = True

    def assert_cross_mode_stable(self, out):
        """join=True output is a fixpoint under join=False."""
        assert (
            wrap_rst(out, join=False) == out
        ), "join=True output is not stable under join=False"

    def assert_no_line_exceeds_width(self, src_line_set, out):
        """No tool-produced line exceeds WIDTH."""
        for line in out.splitlines():
            if line in src_line_set:
                continue  # verbatim passthrough -- OK
            if len(line) > WIDTH:
                pytest.fail(
                    "tool-produced line exceeds width"
                    f" ({len(line)} > {WIDTH}): {line!r:.80}"
                )

    def assert_no_double_space_in_prose(self, src_line_set, out):
        """No tool-produced prose line has a bare double-space."""
        for line in out.splitlines():
            if line in src_line_set:
                continue  # verbatim passthrough -- OK
            if line.startswith((" ", "\t", "..")):
                continue  # indented or directive line -- skip
            if LIST_ITEM_LEAD_RE.match(line):
                continue  # list item -- skip
            if has_bare_double_space(line):
                pytest.fail(
                    f"tool-produced line has bare double-space: {line!r:.100}"
                )

    def assert_only_prose_changed(self, src, out):
        """Every non-prose source line survives in the output.

        If a source line (after rstrip) is missing from the output
        it must be a prose or list-item line that got reflowed.
        Blank lines, indented content, explicit markup, and section
        underlines must never disappear.
        """
        out_line_set = {ln.rstrip() for ln in out.splitlines()}
        for line in src.splitlines():
            s = line.rstrip()
            if s in out_line_set:
                continue
            # Line is missing from output -- only OK for prose /
            # list items that the tool legitimately reflowed.
            if not s:
                pytest.fail("blank line removed from output")
            if s[0] in {" ", "\t"}:
                # Indented lines may change inside prose-body
                # directives (.. note::, etc.), so we can't flag
                # these universally.
                continue
            if s.startswith(".."):
                pytest.fail(f"explicit markup line changed: {s!r:.80}")
            if _UNDERLINE_RE.match(s):
                pytest.fail(f"section underline changed: {s!r:.80}")
            # Column-0, non-structural: prose or list item.
            # Legitimately reflowed -- OK.

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_all(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src, join=self.JOIN)
        # The tool strips trailing whitespace on every line, so a
        # "verbatim passthrough" output line matches the source only
        # after rstrip'ing.
        src_line_set = {ln.rstrip() for ln in src.splitlines()}

        assert wrap_rst(out, join=self.JOIN) == out, "not idempotent"
        self.assert_cross_mode_stable(out)
        self.assert_no_line_exceeds_width(src_line_set, out)
        self.assert_no_double_space_in_prose(src_line_set, out)
        self.assert_only_prose_changed(src, out)
        self.check_all(src, out)


def is_code_directive_fallback(text):
    """True if *text* is a code-body directive that docutils dumped
    as a literal block because it doesn't know the directive.

    Docutils without Sphinx turns every unknown directive body into a
    literal_block whose text starts with the directive marker.  This
    function identifies the subset whose body is verbatim code (listed
    in ``CODE_BODY_DIRECTIVES``).  All other directive fallbacks
    (prose, metadata, structural) return False and are skipped
    when comparing node text.
    """
    m = _TOOL_DIRECTIVE_RE.match(text.lstrip())
    return bool(m) and m.group(1) in CODE_BODY_DIRECTIVES


class TestDocutils(BaseTest):
    """Verify that wrap_rst() does not alter the docutils document tree
    or code block content.

    Parse both the original and the wrapped version with docutils
    once, then check two invariants:
    1. The normalised doctree is unchanged (whitespace-insensitive).
    2. All nodes appear in the same order with the same types, and
       non-paragraph nodes have byte-identical text.
    """

    # Node types to walk for the ordered-node check.  Covers
    # structural, inline, and verbatim nodes.
    CHECKED_TYPES = (
        # Structural
        docutils.nodes.section,
        docutils.nodes.paragraph,
        docutils.nodes.title,
        docutils.nodes.bullet_list,
        docutils.nodes.enumerated_list,
        docutils.nodes.definition_list,
        docutils.nodes.field_list,
        docutils.nodes.table,
        docutils.nodes.block_quote,
        docutils.nodes.footnote,
        docutils.nodes.citation,
        docutils.nodes.line_block,
        docutils.nodes.transition,
        docutils.nodes.comment,
        docutils.nodes.target,
        docutils.nodes.substitution_definition,
        docutils.nodes.literal_block,
        docutils.nodes.doctest_block,
        # Inline
        docutils.nodes.emphasis,
        docutils.nodes.strong,
        docutils.nodes.literal,
        docutils.nodes.reference,
        docutils.nodes.footnote_reference,
        docutils.nodes.substitution_reference,
        docutils.nodes.title_reference,
    )

    # Node types whose text is their own content (not aggregated
    # from child paragraphs) and must be byte-identical after
    # re-wrapping.  Container nodes (section, bullet_list, etc.)
    # are excluded because their astext() includes descendant
    # paragraph text which legitimately changes.
    TEXT_CHECK_TYPES = (
        docutils.nodes.title,
        docutils.nodes.literal_block,
        docutils.nodes.doctest_block,
        docutils.nodes.comment,
        docutils.nodes.target,
        docutils.nodes.substitution_definition,
        docutils.nodes.emphasis,
        docutils.nodes.strong,
        docutils.nodes.literal,
        docutils.nodes.reference,
        docutils.nodes.footnote_reference,
        docutils.nodes.substitution_reference,
        docutils.nodes.title_reference,
    )

    def assert_doctree_unchanged(self, src, out, src_tree, out_tree):
        diff = _doctree_diff(src, out, src_tree=src_tree, dst_tree=out_tree)
        if diff is not None:
            pytest.fail(f"doctree changed:\n{diff}")

    def assert_nodes_preserved(self, src_tree, out_tree):
        """Walk both trees in document order and verify that:

        - The sequence of node types is identical.
        - For nodes whose text must not change (everything except
          paragraphs and prose-directive literal blocks), the text
          is byte-identical.
        """

        def collect(tree):
            nodes = []
            for node in tree.findall(
                lambda n: isinstance(n, self.CHECKED_TYPES)
            ):
                # Skip nodes inside system_message.
                parent = node.parent
                in_sysmsg = False
                while parent is not None:
                    if isinstance(parent, docutils.nodes.system_message):
                        in_sysmsg = True
                        break
                    parent = parent.parent
                if in_sysmsg:
                    continue
                nodes.append(node)
            return nodes

        src_nodes = collect(src_tree)
        out_nodes = collect(out_tree)

        # Compare type sequence.
        src_types = [n.__class__.__name__ for n in src_nodes]
        out_types = [n.__class__.__name__ for n in out_nodes]
        assert src_types == out_types, (
            "node type sequence differs "
            f"({len(src_types)} vs {len(out_types)} nodes)"
        )

        # Compare text for leaf-content nodes.
        inline_types = (
            docutils.nodes.emphasis,
            docutils.nodes.strong,
            docutils.nodes.literal,
            docutils.nodes.reference,
            docutils.nodes.footnote_reference,
            docutils.nodes.substitution_reference,
            docutils.nodes.title_reference,
        )
        for src_node, out_node in zip(src_nodes, out_nodes, strict=True):
            if not isinstance(src_node, self.TEXT_CHECK_TYPES):
                continue
            # Prose-directive fallback: docutils dumped the body as
            # a literal block, but the tool legitimately wraps it.
            if isinstance(src_node, docutils.nodes.literal_block):
                text = src_node.astext()
                if _TOOL_DIRECTIVE_RE.match(text.lstrip()):
                    if not is_code_directive_fallback(text):
                        continue
            # Inline nodes inside paragraphs can have their
            # inter-word whitespace changed by re-wrapping
            # (newline -> space).  Normalize before comparing.
            if isinstance(src_node, inline_types):
                src_text = " ".join(src_node.astext().split())
                out_text = " ".join(out_node.astext().split())
            else:
                src_text = "\n".join(
                    ln.rstrip() for ln in src_node.astext().splitlines()
                )
                out_text = "\n".join(
                    ln.rstrip() for ln in out_node.astext().splitlines()
                )
            assert src_text == out_text, (
                f"{src_node.__class__.__name__} text changed:\n"
                f"  src: {src_text[:200]!r}\n"
                f"  out: {out_text[:200]!r}"
            )

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_it(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src, join=self.JOIN)
        if src == out:
            return
        try:
            src_tree = _parse_rst(src)
            out_tree = _parse_rst(out)
        except DoctreeParseError as e:
            with pytest.raises(SystemExit) as exc_info:
                rst_wrap_lines.main(["--safe", str(path)])
            assert exc_info.value.code == 1
            return pytest.skip(f"docutils could not parse: {e}")

        self.assert_doctree_unchanged(src, out, src_tree, out_tree)
        self.assert_nodes_preserved(src_tree, out_tree)
