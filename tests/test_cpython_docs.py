"""Tests running wrap_rst() against the CPython documentation.

The CPython repo is cloned once (sparse, Doc/ only) into a temp
directory and reused across runs. The clone only happens when this
test class is collected.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from rst_wrap_lines import WIDTH
from rst_wrap_lines import wrap_rst

from . import BaseTest
from . import has_bare_double_space

CLONE_DIR = Path("/tmp/rst-wrap-lines-cpython")
DOC_DIR = CLONE_DIR / "Doc"
DOC_DIR_2 = CLONE_DIR / "Doc-2"

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


@pytest.mark.slow
class TestZSphinxBuild(BaseTest):

    @classmethod
    def setup_class(cls):
        clone_cpython_repo()
        # shutil.rmtree(DOC_DIR_2, ignore_errors=True)
        # shutil.copytree(DOC_DIR, DOC_DIR_2)

    @staticmethod
    def log(msg):
        print("\n")
        print("=" * 70)
        print(msg)
        print("=" * 70)

    def test_it(self):
        sphinx_cmd = [
            "sphinx-build",
            "-b",
            "html",
            "-D",
            "html_last_updated_fmt=",
            ".",
            "",
        ]

        # Sphinx build #1.
        self.log("Build original CPython doc")
        sphinx_cmd[-1] = "_build/html-1"
        subprocess.run(sphinx_cmd, cwd=DOC_DIR_2, check=True)

        # Run CLI tool.
        self.log("Execute CLI tool")
        cmd = [sys.executable, "-m", "rst_wrap_lines", DOC_DIR_2]
        subprocess.run(cmd, cwd=DOC_DIR_2, check=True)

        # Sphinx build #2; if something went wrong, we'll crash here
        # already.
        self.log("Re-build CPython doc")
        sphinx_cmd[-1] = "_build/html-2"
        subprocess.run(sphinx_cmd, cwd=DOC_DIR_2, check=True)
