import io

import pytest

import rst_wrap_lines


class TestCLI:
    @pytest.fixture(autouse=True)
    def tmp_rst(self, tmp_path):
        """Write a sample .rst file into tmp_path and expose both."""
        self.dir = tmp_path
        self.rst = tmp_path / "sample.rst"
        self.rst.write_text("Hello world.\n", encoding="utf-8")

    # --- parse_cli ---

    def test_parse_cli_single_file(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert [self.rst] == rst_wrap_lines.PATHS

    def test_parse_cli_directory_collects_rst(self):
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert self.rst in rst_wrap_lines.PATHS

    def test_parse_cli_width(self):
        rst_wrap_lines.parse_cli(["--width", "60", str(self.rst)])
        assert rst_wrap_lines.WIDTH == 60

    def test_parse_cli_check_flag(self):
        rst_wrap_lines.parse_cli(["--check", str(self.rst)])
        assert rst_wrap_lines.CHECK is True

    def test_parse_cli_diff_flag(self):
        rst_wrap_lines.parse_cli(["--diff", str(self.rst)])
        assert rst_wrap_lines.DIFF is True

    def test_parse_cli_ignores_dotgit_dir(self):
        git_dir = self.dir / ".git"
        git_dir.mkdir()
        (git_dir / "hidden.rst").write_text("ignored\n", encoding="utf-8")
        rst_wrap_lines.parse_cli([str(self.dir)])
        assert not any(".git" in str(p) for p in rst_wrap_lines.PATHS)

    def test_parse_cli_paths_reset_between_calls(self):
        rst_wrap_lines.parse_cli([str(self.rst)])
        rst_wrap_lines.parse_cli([str(self.rst)])
        assert rst_wrap_lines.PATHS.count(self.rst) == 1

    # --- main ---

    def test_main_rewrites_file(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        rst_wrap_lines.main([str(self.rst)])
        result = self.rst.read_text(encoding="utf-8")
        assert result != long_line
        for line in result.splitlines():
            assert len(line) <= 79

    def test_main_check_exits_1_when_changed(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert exc_info.value.code == 1

    def test_main_check_does_not_write(self):
        long_line = "word " * 20 + "\n"
        self.rst.write_text(long_line, encoding="utf-8")
        with pytest.raises(SystemExit):
            rst_wrap_lines.main(["--check", str(self.rst)])
        assert self.rst.read_text(encoding="utf-8") == long_line

    def test_main_no_change_exits_0(self):
        # File already fits within 79 chars; no SystemExit expected.
        rst_wrap_lines.main(["--check", str(self.rst)])

    # --- stdin / stdout ---

    def test_stdin_format(self, monkeypatch, capsys):
        # `-` reads from stdin, writes formatted output to stdout.
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["-"])
        out = capsys.readouterr().out
        assert out != long_line
        for line in out.splitlines():
            assert len(line) <= 79

    def test_stdin_check_clean_exits_0(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("Short.\n"))
        rst_wrap_lines.main(["--check", "-"])
        # Check mode is silent on stdout; exit 0 (no SystemExit).
        assert capsys.readouterr().out == ""

    def test_stdin_check_dirty_exits_1(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.main(["--check", "-"])
        assert exc_info.value.code == 1
        # No formatted output to stdout in check mode.
        assert capsys.readouterr().out == ""

    def test_stdin_diff(self, monkeypatch, capsys):
        long_line = "word " * 20 + "\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(long_line))
        rst_wrap_lines.main(["--diff", "-"])
        out = capsys.readouterr().out
        assert out.startswith("--- <stdin>")
        assert "+++ <stdout>" in out

    def test_stdin_combined_with_path_rejected(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            rst_wrap_lines.parse_cli(["-", str(self.rst)])
        # argparse error → exit 2
        assert exc_info.value.code == 2
        assert "cannot be combined" in capsys.readouterr().err


class TestSafe:
    """Exercise the opt-in ``--safe`` doctree verification path."""

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
