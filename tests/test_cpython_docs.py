"""Tests running wrap_rst() against the CPython documentation.

The CPython repo is cloned once (sparse, Doc/ only) into a temp
directory and reused across runs. The clone only happens when this
test class is collected.
"""

import subprocess
from pathlib import Path

import pytest

from rst_wrap_lines import wrap_rst

from . import InternalBaseTest

CLONE_DIR = Path("/tmp/rst-wrap-lines-cpython")
REPO_URL = "https://github.com/python/cpython"


class TestCPythonDocs(InternalBaseTest):
    @classmethod
    def setup_class(cls):
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

    def test_all(self):
        failures = []
        rst_files = sorted((CLONE_DIR / "Doc").rglob("*.rst"))
        assert rst_files, f"no .rst files found under {CLONE_DIR / 'Doc'}"
        for path in rst_files:
            src = path.read_text(encoding="utf-8")
            out = wrap_rst(src)
            # 1. idempotency
            if wrap_rst(out) != out:
                failures.append(f"{path.name}: not idempotent")
                continue
            # 2. the tool must never increase the maximum line length of
            # a file (e.g. by joining a hyperlink that was manually split
            # across lines into a single un-splittable token).
            max_src = max((len(x) for x in src.splitlines()), default=0)
            max_out = max((len(x) for x in out.splitlines()), default=0)
            if max_out > max_src:
                failures.append(
                    f"{path.name}: max line length increased"
                    f" ({max_src} -> {max_out})"
                )
        if failures:
            pytest.fail("\n".join(failures))
