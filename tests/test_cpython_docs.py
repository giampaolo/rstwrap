"""Tests run against .rst files from multiple sources.

Currently includes:
- Local regression fixtures (tests/rst/, always present)
- CPython documentation (Doc/, ~600 files)
- Sphinx documentation (doc/, ~100 files)

Each .rst file is a separate parametrized test item, so that
pytest-xdist can distribute them across workers.

The external repos are cloned once (sparse) into temp directories and
reused across runs. Cloning is triggered in conftest.py during
collection setup, **before** pytest-xdist spawns worker processes.

Adding a regression test: drop a .rst file into tests/rst/ and it
will be picked up automatically on the next run.
"""

import difflib
import pathlib

import docutils.nodes
import pytest
from docutils.core import publish_doctree
from docutils.utils import Reporter

from rst_wrap_lines import WIDTH
from rst_wrap_lines import wrap_rst

from . import BaseTest
from . import has_bare_double_space
from .conftest import CLONE_DIR
from .conftest import SPHINX_CLONE_DIR

_LOCAL_RST_DIR = pathlib.Path(__file__).parent / "rst"

_SOURCES = [
    (_LOCAL_RST_DIR, "local"),
    (CLONE_DIR / "Doc", "cpython"),
    (SPHINX_CLONE_DIR / "doc", "sphinx"),
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


class TestCPythonDocs(BaseTest):
    """Run wrap_rst() against every collected .rst file and verify
    basic invariants: idempotency, no tool-produced line exceeds the
    target width, no bare double-space in tool-produced prose.
    """

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_all(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src)
        src_line_set = set(src.splitlines())

        # 1. idempotency
        assert wrap_rst(out) == out, "not idempotent"

        # 2. no tool-produced line may exceed the target width.
        #    Verbatim passthrough of already-long source lines is OK.
        for line in out.splitlines():
            if line in src_line_set:
                continue  # verbatim passthrough -- OK
            if len(line) > WIDTH:
                pytest.fail(
                    "tool-produced line exceeds width"
                    f" ({len(line)} > {WIDTH}): {line!r:.80}"
                )

        # 3. no prose line produced by the tool should contain a bare
        #    double-space (spaces inside inline RST constructs are
        #    intentional and excluded from this check).
        for line in out.splitlines():
            if line in src_line_set:
                continue  # verbatim passthrough -- OK
            if line.startswith((" ", "\t", "..")):
                continue  # indented or directive line -- skip
            if has_bare_double_space(line):
                pytest.fail(
                    f"tool-produced line has bare double-space: {line!r:.100}"
                )

        # 4. universal sanity checks.
        self.check_all(src, out)


def _doctree_str(text):
    """Parse RST and return a normalized document-tree string.

    Whitespace inside text nodes is collapsed so that prose re-wrapping
    by our tool does not produce false positives.  All other structure
    (nodes, attributes, nesting) is preserved verbatim.
    """
    tree = publish_doctree(
        text,
        settings_overrides={
            # silence stderr noise from Sphinx-specific / unknown directives
            "report_level": Reporter.SEVERE_LEVEL + 1,
            "halt_level": Reporter.SEVERE_LEVEL + 1,
        },
    )
    # Remove system_message nodes: they reflect docutils warnings about
    # Sphinx-specific / unknown directives and parsing ambiguities that
    # vary with line positions, not document structure.
    for node in tree.findall(docutils.nodes.system_message):
        node.parent.remove(node)
    # Strip source-position attributes: line numbers shift whenever prose
    # is re-wrapped, so they must not influence the comparison.
    for node in tree.findall(docutils.nodes.Element):
        node.attributes.pop("source", None)
        node.attributes.pop("line", None)
        node.line = None
    for node in tree.findall(docutils.nodes.Text):
        normalized = " ".join(str(node).split())
        node.parent.replace(node, docutils.nodes.Text(normalized))
    return tree.pformat()


class TestDocutils(BaseTest):
    """Verify that wrap_rst() does not alter the docutils document tree.

    Parse both the original and the wrapped version with docutils and
    compare the resulting trees (after normalising intra-node
    whitespace).  A difference means the tool changed something
    structural, not just prose line lengths.
    """

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_doctree_unchanged(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src)
        if src == out:
            return
        s1 = _doctree_str(src)
        s2 = _doctree_str(out)
        if s1 != s2:
            diff = difflib.unified_diff(
                s1.splitlines(),
                s2.splitlines(),
                fromfile=f"{path.name} (original)",
                tofile=f"{path.name} (wrapped)",
                lineterm="",
                n=2,
            )
            pytest.fail("\n".join(diff))
