"""Tests running wrap_rst() against the CPython documentation.

The CPython repo is cloned once (sparse, Doc/ only) into a temp
directory and reused across runs. The clone only happens when this
test class is collected.
"""

import difflib
import subprocess
from pathlib import Path

import docutils.nodes
import pytest
from docutils.core import publish_doctree
from docutils.utils import Reporter

from rst_wrap_lines import WIDTH
from rst_wrap_lines import wrap_rst

from . import BaseTest
from . import has_bare_double_space

CLONE_DIR = Path("/tmp/rst-wrap-lines-cpython")
DOC_DIR = CLONE_DIR / "Doc"

REPO_URL = "https://github.com/python/cpython"


def clone_cpython_repo():
    if not CLONE_DIR.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                "main",
                "--single-branch",
                "--depth",
                "1",
                REPO_URL,
                str(CLONE_DIR),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", "Doc/"],
            cwd=CLONE_DIR,
            check=True,
        )


class TestCPythonDocs(BaseTest):
    @classmethod
    def setup_class(cls):
        clone_cpython_repo()

    def test_all(self):
        failures = []
        rst_files = sorted((DOC_DIR).rglob("*.rst"))
        assert rst_files, f"no .rst files found under {DOC_DIR}"
        for path in rst_files:
            src = path.read_text(encoding="utf-8")
            out = wrap_rst(src)
            src_line_set = set(src.splitlines())

            # 1. idempotency
            if wrap_rst(out) != out:
                failures.append(f"{path.name}: not idempotent")
                continue

            # 2. no tool-produced line may exceed the target width.
            # Verbatim passthrough of already-long source lines is OK.
            for line in out.splitlines():
                if line in src_line_set:
                    continue  # verbatim passthrough -- OK
                if len(line) > WIDTH:
                    failures.append(
                        f"{path.name}: tool-produced line exceeds width"
                        f" ({len(line)} > {WIDTH}): {line!r:.80}"
                    )
                    break

            # 3. no prose line produced by the tool should contain a bare
            # double-space (spaces inside inline RST constructs are
            # intentional and excluded from this check).
            for line in out.splitlines():
                if line in src_line_set:
                    continue  # verbatim passthrough -- OK
                if line.startswith((" ", "\t", "..")):
                    continue  # indented or directive line -- skip
                if has_bare_double_space(line):
                    failures.append(
                        f"{path.name}: tool-produced line has bare"
                        f" double-space: {line!r:.100}"
                    )
                    break

            # 4-7. universal sanity checks.
            try:
                self.check_all(src, out)
            except AssertionError as e:
                failures.append(f"{path.name}: {e}")

        if failures:
            pytest.fail("\n".join(failures))


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


@pytest.mark.slow
class TestZDocutils(BaseTest):
    """Verify that wrap_rst() does not alter the docutils document tree.

    For every .rst file in the CPython docs, parse both the original and
    the wrapped version with docutils and compare the resulting trees
    (after normalising intra-node whitespace).  A difference means the
    tool changed something structural, not just prose line lengths.
    """

    @classmethod
    def setup_class(cls):
        clone_cpython_repo()

    def test_doctree_unchanged(self):
        failures = []
        rst_files = sorted(DOC_DIR.rglob("*.rst"))
        assert rst_files, f"no .rst files found under {DOC_DIR}"
        for path in rst_files:
            src = path.read_text(encoding="utf-8")
            out = wrap_rst(src)
            if src == out:
                continue
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
                print(diff)
                failures.append("\n".join(diff))
        if failures:
            pytest.fail("\n\n".join(failures))
