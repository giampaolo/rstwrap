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
            # idempotency
            if wrap_rst(out) != out:
                failures.append(f"{path.name}: not idempotent")
        if failures:
            pytest.fail("\n".join(failures))
