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
from docutils.core import publish_doctree
from docutils.utils import Reporter

import rst_wrap_lines
from rst_wrap_lines import WIDTH
from rst_wrap_lines import DoctreeParseError
from rst_wrap_lines import _doctree_diff
from rst_wrap_lines import wrap_rst

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
_LIST_ITEM_LEAD_RE = re.compile(r"^\s*([-*+]|\d+[.)]|\(\d+\)|#\.)\s+")

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

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_all(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src, join=self.JOIN)
        # The tool strips trailing whitespace on every line, so a
        # "verbatim passthrough" output line matches the source only
        # after rstrip'ing.
        src_line_set = {ln.rstrip() for ln in src.splitlines()}

        # 1. idempotency
        assert wrap_rst(out, join=self.JOIN) == out, "not idempotent"

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
        #    intentional and excluded from this check). List-item
        #    lines are excluded: the bullet-to-text spacing is
        #    preserved verbatim from the source and may be 2+ spaces
        #    (checked separately by assert_no_double_space_in_list_items
        #    on the text *after* the bullet marker).
        for line in out.splitlines():
            if line in src_line_set:
                continue  # verbatim passthrough -- OK
            if line.startswith((" ", "\t", "..")):
                continue  # indented or directive line -- skip
            if _LIST_ITEM_LEAD_RE.match(line):
                continue  # list item -- skip
            if has_bare_double_space(line):
                pytest.fail(
                    f"tool-produced line has bare double-space: {line!r:.100}"
                )

        # 4. universal sanity checks.
        self.check_all(src, out)


def parse_doctree(text):
    """Parse *text* with docutils, return the tree or ``None``."""
    try:
        return publish_doctree(
            text,
            settings_overrides={
                "report_level": Reporter.SEVERE_LEVEL + 1,
                "halt_level": Reporter.SEVERE_LEVEL + 1,
            },
        )
    except (KeyError, TypeError, AttributeError, ValueError):
        return None


def code_blocks_from_tree(tree):
    """Extract code block text from a docutils tree.

    Returns a set of strings (lines rstripped). Excludes
    unknown-directive fallbacks (text starting with ``..``).
    """

    blocks = set()
    node_types = (
        docutils.nodes.literal_block,
        docutils.nodes.doctest_block,
    )
    for node in tree.findall(lambda n: isinstance(n, node_types)):
        text = node.astext()
        if text.lstrip().startswith(".."):
            continue
        normalized = "\n".join(ln.rstrip() for ln in text.splitlines())
        blocks.add(normalized)
    return blocks


class TestDocutils(BaseTest):
    """Verify that wrap_rst() does not alter the docutils document tree
    or code block content.

    Parse both the original and the wrapped version with docutils
    once, then check two invariants:
    1. The normalised doctree is unchanged.
    2. Every code block in the source appears unchanged in the output.

    Runs with ``join=True`` so the short-line merge path is held to
    the same doctree-invariant as the default wrap path.
    """

    JOIN = True

    @pytest.mark.parametrize("path", _RST_FILE_PARAMS)
    def test_doctree_unchanged(self, path):
        src = path.read_text(encoding="utf-8")
        out = wrap_rst(src, join=self.JOIN)
        if src == out:
            return
        try:
            diff = _doctree_diff(src, out)
        except DoctreeParseError as e:
            with pytest.raises(SystemExit) as exc_info:
                rst_wrap_lines.main(["--safe", str(path)])
            assert exc_info.value.code == 1
            pytest.skip(f"docutils could not parse: {e}")
        if diff is not None:
            pytest.fail(diff)

        # Code block preservation: parse once, check every source
        # code block appears unchanged in the output.
        src_tree = parse_doctree(src)
        if src_tree is None:
            return
        out_tree = parse_doctree(out)
        if out_tree is None:
            return
        src_blocks = code_blocks_from_tree(src_tree)
        out_blocks = code_blocks_from_tree(out_tree)
        for block in src_blocks:
            assert (
                block in out_blocks
            ), f"code block changed or missing in output:\n{block}"
