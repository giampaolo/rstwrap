"""CLI tests, one subclass per option/feature.

All classes that need a sample .rst file in a temp dir inherit from
``_CLITestBase`` which provides ``self.dir`` and ``self.rst`` via an
autouse fixture. ``TestSafe`` and ``TestPyprojectConfig`` keep their
own setup because they need different fixture semantics.
"""

import io

import pytest

import rst_wrap_lines


class _CLITestBase:
    """Shared autouse fixture: a tmp dir with a tiny ``sample.rst``."""

    @pytest.fixture(autouse=True)
    def tmp_rst(self, tmp_path):
        self.dir = tmp_path
        self.rst = tmp_path / "sample.rst"
        self.rst.write_text("Hello world.\n", encoding="utf-8")


class TestVersion(_CLITestBase):
    """``--version``."""

    def test_version_flag(self, capsys):
        # Prints to stdout and exits 0.
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli(["--version"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert rst_wrap_lines.__version__ in out


class TestParseCli(_CLITestBase):
    """``parse_cli`` machinery that isn't tied to a specific option:
    path collection, directory recursion, ignored dirs, statefulness.
    """

    def test_single_file(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert [self.rst] == rst_wrap_lines.PATHS

    def test_directory_collects_rst(self):
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert self.rst in rst_wrap_lines.PATHS

    def test_ignores_dotgit_dir(self):
        git_dir = self.dir / ".git"
        git_dir.mkdir()
        (git_dir / "hidden.rst").write_text("ignored\n", encoding="utf-8")
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert not any(".git" in str(p) for p in rst_wrap_lines.PATHS)

    def test_paths_reset_between_calls(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.PATHS.count(self.rst) == 1


class TestWidth(_CLITestBase):
    """``-w`` / ``--width``."""

    def test_width_flag_sets_module_constant(self):
        rst_wrap_lines.parse_cli(["--width", "60", str(self.rst)])
        assert rst_wrap_lines.WIDTH == 60


class TestFormat(_CLITestBase):
    """Default mode: rewrite the file in place."""

    def test_main_rewrites_file(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main([str(self.rst)])
        result = self.rst.read_text(encoding="utf-8")
        assert result != long_line
        for line in result.splitlines():
            assert len(line) <= 79


class TestCheck(_CLITestBase):
    """``--check``."""

    def test_check_flag_sets_module_constant(self):
        rst_wrap_lines.parse_cli(["--check", str(self.rst)])
        assert rst_wrap_lines.CHECK is True

    def test_check_exits_1_when_changed(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert exc_info.value.code == 1

    def test_check_does_not_write(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit):
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert self.rst.read_text(encoding="utf-8") == long_line

    def test_check_no_change_exits_0(self):
        # File already fits within 79 chars; no SystemExit expected.
        rst_wrap_lines.main(["--check", str(self.rst)])


class TestDiff(_CLITestBase):
    """``--diff``."""

    def test_diff_flag_sets_module_constant(self):
        rst_wrap_lines.parse_cli(["--diff", str(self.rst)])
        assert rst_wrap_lines.DIFF is True


class TestJoin(_CLITestBase):
    """``--join`` / ``--no-join``."""

    def test_join_is_default(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.JOIN is True

    def test_no_join_flag(self):
        rst_wrap_lines.parse_cli(["--no-join", str(self.rst)])
        assert rst_wrap_lines.JOIN is False


class TestColor(_CLITestBase):
    """``--color``."""

    def test_color_always(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["--diff", "--color", "always", "-"])
        out = capsys.readouterr().out
        assert "\033[" in out

    def test_color_never(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["--diff", "--color", "never", "-"])
        out = capsys.readouterr().out
        assert "\033[" not in out


class TestQuiet(_CLITestBase):
    """``-q`` / ``--quiet``."""

    def test_suppresses_reformatted_message(self, capsys):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main(["--quiet", str(self.rst)])
        # File was rewritten...
        assert self.rst.read_text(encoding="utf-8") != long_line
        # ...but no "reformatted FILE" line was printed.
        assert "reformatted" not in capsys.readouterr().out

    def test_suppresses_would_reformat_message(self, capsys):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--quiet", "--check", str(self.rst)])
        # Exit code still signals "would change".
        assert exc_info.value.code == 1
        # But no "would reformat FILE" line was printed.
        assert "would reformat" not in capsys.readouterr().out

    def test_short_alias(self, capsys):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main(["-q", str(self.rst)])
        assert "reformatted" not in capsys.readouterr().out


class TestSummary(_CLITestBase):
    """End-of-run summary line on multi-file invocations."""

    def _make_files(self, n_long, n_short):
        """Create *n_long* over-width and *n_short* short .rst files.

        Returns the list of path strings.
        """
        long_line = "word " * 20 + "\n"
        paths = []
        for i in range(n_long):
            p = self.dir / f"long{i}.rst"
            p.write_text(long_line, encoding="utf-8")
            paths.append(str(p))
        for i in range(n_short):
            p = self.dir / f"short{i}.rst"
            p.write_text("Short.\n", encoding="utf-8")
            paths.append(str(p))
        return paths

    def test_multi_file_format_mode(self, capsys):
        paths = self._make_files(n_long=2, n_short=3)
        rst_wrap_lines.main(paths)
        out = capsys.readouterr().out
        assert "2 reformatted, 3 unchanged." in out

    def test_multi_file_check_mode(self, capsys):
        paths = self._make_files(n_long=2, n_short=3)
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", *paths])
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "2 would be reformatted, 3 unchanged." in out

    def test_suppressed_by_quiet(self, capsys):
        paths = self._make_files(n_long=2, n_short=3)
        rst_wrap_lines.main(["--quiet", *paths])
        out = capsys.readouterr().out
        assert "reformatted" not in out
        assert "unchanged" not in out

    def test_skipped_for_single_file(self, capsys):
        paths = self._make_files(n_long=1, n_short=0)
        rst_wrap_lines.main(paths)
        out = capsys.readouterr().out
        # Per-file message appears; aggregate summary does not.
        assert "reformatted" in out
        assert "1 reformatted, 0 unchanged" not in out


class TestStdin(_CLITestBase):
    """``-`` (stdin / stdout)."""

    def test_format(self, monkeypatch, capsys):
        # `-` reads from stdin, writes formatted output to stdout.
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["-"])
        out = capsys.readouterr().out
        assert out != long_line
        for line in out.splitlines():
            assert len(line) <= 79

    def test_check_clean_exits_0(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("Short.\n"))
        rst_wrap_lines.main(["--check", "-"])
        # Check mode is silent on stdout; exit 0 (no SystemExit).
        assert capsys.readouterr().out == ""

    def test_check_dirty_exits_1(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", "-"])
        assert exc_info.value.code == 1
        # No formatted output to stdout in check mode.
        assert capsys.readouterr().out == ""

    def test_diff(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["--diff", "-"])
        out = capsys.readouterr().out
        assert out.startswith("--- <stdin>")
        assert "+++ <stdout>" in out

    def test_combined_with_path_rejected(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli(["-", str(self.rst)])
        # argparse error → exit 2
        assert exc_info.value.code == 2
        assert "cannot be combined" in capsys.readouterr().err


class TestSafe:
    """``--safe``: doctree verification (helper + CLI integration)."""

    def test_doctree_diff_returns_none_for_equal_trees(self):
        # Identical text: doctrees match, helper returns None.
        assert rst_wrap_lines._doctree_diff("Hello.\n", "Hello.\n") is None

    def test_doctree_diff_normalizes_whitespace(self):
        # Prose rewrap (different line breaks, same text): trees match
        # after whitespace normalization.
        src = "Hello world foo bar.\n"
        out = "Hello\nworld foo bar.\n"
        assert rst_wrap_lines._doctree_diff(src, out) is None

    def test_doctree_diff_detects_structural_change(self):
        # Paragraph vs. section title: structural difference.
        src = "Hello world.\n"
        dst = "Hello\n=====\n"
        diff = rst_wrap_lines._doctree_diff(src, dst)
        assert diff is not None
        assert "paragraph" in diff or "title" in diff

    def test_main_safe_flag_accepted(self, tmp_path):
        # --safe runs without error on a file whose wrap output is
        # doctree-equivalent (the common case).
        rst = tmp_path / "sample.rst"
        long_line = "word " * 20 + "\n"
        rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main(["--safe", str(rst)])
        # File was rewritten; content changed.
        assert rst.read_text(encoding="utf-8") != long_line

    def test_main_safe_refuses_write_on_mismatch(self, tmp_path, monkeypatch):
        # Simulate a buggy wrap by monkey-patching wrap_rst to return
        # something structurally different from the source. --safe must
        # detect the mismatch, leave the file unchanged, and exit 1.
        rst = tmp_path / "sample.rst"
        src = "Hello world.\n"
        rst.write_text(src, encoding="utf-8")

        def fake_wrap(text, width=79, join=False):
            return "Hello\n=====\n"

        monkeypatch.setattr(rst_wrap_lines, "wrap_rst", fake_wrap)
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--safe", str(rst)])
        assert exc_info.value.code == 1
        assert rst.read_text(encoding="utf-8") == src


class TestPyprojectConfig:
    """``[tool.rst-wrap-lines]`` discovery, validation, and overrides."""

    @pytest.fixture(autouse=True)
    def isolate_cwd(self, tmp_path, monkeypatch):
        # Each test runs in its own empty tmp dir so the project's own
        # pyproject.toml is never picked up by the upward search.
        self.dir = tmp_path
        self.rst = tmp_path / "sample.rst"
        self.rst.write_text("Hello world.\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

    def _write_config(self, body):
        (self.dir / "pyproject.toml").write_text(
            f"[tool.rst-wrap-lines]\n{body}\n", encoding="utf-8"
        )

    def test_no_pyproject_uses_defaults(self):
        # No pyproject.toml in tmp_path or its parents-up-to-tmp.
        # /tmp itself has no pyproject.toml so we get plain defaults.
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.WIDTH == 79
        assert rst_wrap_lines.JOIN is True
        assert rst_wrap_lines.SAFE is False

    def test_pyproject_sets_width(self):
        self._write_config("width = 60")
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.WIDTH == 60

    def test_pyproject_sets_join_and_safe(self):
        self._write_config("join = true\nsafe = true")
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.JOIN is True
        assert rst_wrap_lines.SAFE is True

    def test_cli_overrides_pyproject_width(self):
        self._write_config("width = 60")
        rst_wrap_lines.parse_cli(["--width", "100", str(self.rst)])
        assert rst_wrap_lines.WIDTH == 100

    def test_cli_no_join_overrides_pyproject_join_true(self):
        self._write_config("join = true")
        rst_wrap_lines.parse_cli(["--no-join", str(self.rst)])
        assert rst_wrap_lines.JOIN is False

    def test_pyproject_walks_up_from_subdir(self, monkeypatch):
        # Config in parent dir is discovered when CLI runs in a subdir.
        self._write_config("width = 70")
        sub = self.dir / "sub"
        sub.mkdir()
        monkeypatch.chdir(sub)
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.WIDTH == 70

    def test_pyproject_no_section_ignored(self):
        # pyproject.toml exists but has no [tool.rst-wrap-lines] section.
        (self.dir / "pyproject.toml").write_text(
            "[tool.other]\nfoo = 1\n", encoding="utf-8"
        )
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.WIDTH == 79

    def test_unknown_key_is_fatal(self, capsys):
        self._write_config("nonsense = 42")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli([str(self.rst)])
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "unknown key" in err
        assert "nonsense" in err
        # The error message lists the valid keys.
        assert "width" in err
        assert "join" in err
        assert "safe" in err

    def test_wrong_type_is_fatal(self, capsys):
        # width must be int, not string
        self._write_config('width = "wide"')
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli([str(self.rst)])
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "must be an integer" in err

    def test_bool_for_int_field_is_fatal(self, capsys):
        # bool is a subclass of int but should NOT be accepted for width.
        self._write_config("width = true")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli([str(self.rst)])
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "must be an integer" in err
