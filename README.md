# rstwrap

[![Tests](https://img.shields.io/github/actions/workflow/status/giampaolo/rstwrap/tests.yml?label=tests)](https://github.com/giampaolo/rstwrap/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/rstwrap.svg)](https://pypi.org/project/rstwrap/)
[![Python versions](https://img.shields.io/badge/python-3.9+-blue.svg)](https://pypi.org/project/rstwrap/)
[![Status](https://img.shields.io/pypi/status/rstwrap.svg)](https://pypi.org/project/rstwrap/)
[![License](https://img.shields.io/pypi/l/rstwrap.svg)](https://github.com/giampaolo/rstwrap/blob/master/LICENSE)

A command-line tool to wrap prose paragraphs in reStructuredText (.rst)
files to a maximum line width.

Only prose paragraphs and list items are wrapped. Everything else (directives,
literal blocks, tables, section underlines, comments, indented blocks) is left
unchanged.

```diff
- This is a very long paragraph that goes way beyond the standard seventy-nine characters and really should be wrapped for better readability in a terminal or text editor.
+ This is a very long paragraph that goes way beyond the standard seventy-nine
+ characters and really should be wrapped for better readability in a terminal or
+ text editor.
```

Primary workflows:

- Local: format `.rst` files automatically on save in your editor.
- CI: enforce consistent line width using the --check flag.

## Installation

```
pip install rstwrap
```

## Usage

Examples:

```bash
rstwrap docs/*.rst
rstwrap docs/                # whole dir, recursive
rstwrap --check docs/*.rst
rstwrap --width 120 foo.rst
rstwrap --no-join docs/*.rst  # only wrap over-width lines
rstwrap --safe docs/*.rst    # verify output with docutils
cat foo.rst | rstwrap -      # read stdin, write to stdout
```

Options:

- `-w`, `--width`: maximum line length (default: 79)
- `--diff`: print a unified diff instead of writing files
- `--color`: colorize diff output (`auto`, `always`, `never`; default: `auto`)
- `--check`: exit with code 1 if any file would be changed; don't write
- `--join` / `--no-join`: merge short consecutive lines within a paragraph into
  a single line (up to the target width).
- `--safe`: after wrapping, parse both the input and the output with
  [docutils](https://docutils.sourceforge.io/), and skip any file whose
  document tree would change (prints a diff to stderr and exits with code 1).
  Requires `pip install 'rstwrap[safe]'`.
- `-q`, `--quiet`: suppress informational output.
- `--version`: print the version and exit

## Editor integration

Use `-` instead of a file path to read from stdin and write to stdout.
This lets you integrate it into any editor that can pipe the current buffer
through a shell command, and format `.rst` files on save.

### Vim / Neovim

Add to `~/.vimrc`:

```vim
autocmd BufWritePre *.rst silent! %!rstwrap -
```

### VS Code

With the [Custom Local Formatters](https://marketplace.visualstudio.com/items?itemName=jkillian.custom-local-formatters)
extension:

```json
"customLocalFormatters.formatters": [
  {
    "command": "rstwrap -",
    "languages": ["restructuredtext"]
  }
]
```

### Sublime Text

With the [Fmt](https://packagecontrol.io/packages/Fmt) plugin, add to
`Preferences > Package Settings > Fmt > Settings`:

```json
{
  "rules": [
    {
      "selector": "text.restructuredtext",
      "cmd": ["rstwrap", "-"],
      "format_on_save": true
    }
  ]
}
```

### Emacs

```elisp
(defun rstwrap-buffer ()
  (interactive)
  (let ((p (point)))
    (shell-command-on-region (point-min) (point-max)
                             "rstwrap -" nil t)
    (goto-char p)))
```

## GitHub Actions

Add the following workflow into `.github/workflows/rstwrap.yml` to fail CI for
any `.rst` file that isn't properly wrapped. Adjust `docs/` to wherever your
`.rst` files live.

```yaml
name: rstwrap
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v6
        with:
          python-version: '3.x'
      - run: pip install 'rstwrap[safe]'
      - run: rstwrap --check --diff --safe docs/
```

## Configuration via pyproject.toml

Project-wide defaults can be set in a `[tool.rstwrap]` section of
`pyproject.toml`. The tool walks up from the current working directory
to find the nearest one. Supported keys:

```toml
[tool.rstwrap]
width = 120    # default: 79
join = false   # default: true
safe = true    # default: false
```

Command-line flags **override** anything set in `pyproject.toml`. To turn
off a setting from the CLI for a single run, use the negation flags
`--no-join` / `--no-safe`. Per-invocation flags (`--check`, `--diff`) are not
configurable in pyproject.toml — they're run modes, not project policy.

## What gets wrapped

- **Prose paragraphs**

  ```diff
  - This is a very long paragraph that goes way beyond the standard seventy-nine characters and really should be wrapped.
  + This is a very long paragraph that goes way beyond the standard
  + seventy-nine characters and really should be wrapped.
  ```

- **Lists** (bullet and enumerated), including nested sublists

  ```diff
  - - This is a very long bullet item that exceeds the target width and needs to be re-wrapped to fit within the line limit.
  + - This is a very long bullet item that exceeds the target width and
  +   needs to be re-wrapped to fit within the line limit.
  ```

- **Bodies of directives that contain prose** (`.. note::`, `.. warning::`,
  `.. versionadded::`, `.. class::`, etc.)

  ```diff
    .. note::
  -    This is a very long note that exceeds the target width and needs to be re-wrapped to fit within the line limit.
  +    This is a very long note that exceeds the target width and needs
  +    to be re-wrapped to fit within the line limit.
  ```

- **Short consecutive lines** within a paragraph (disable with `--no-join`)

  ```diff
  - Some short
  - lines that
  - could fit on one.
  + Some short lines that could fit on one.
  ```

## What gets formatted

Beyond wrapping, the tool also applies these normalizations everywhere
(including lines that already fit within the target width):

- **Double or more spaces** in prose are collapsed

  ```diff
  - hello  world
  + hello world
  ```

- **Consecutive blank lines** between top-level paragraphs are collapsed
  into one. Blank lines inside indented content (literal blocks,
  directive bodies, simple tables) are preserved verbatim.

  ```diff
  - Paragraph one.
  -
  -
  -
  - Paragraph two.
  + Paragraph one.
  +
  + Paragraph two.
  ```

- **Trailing whitespace** is stripped from every line

  ```diff
  - Some text with trailing spaces.···
  + Some text with trailing spaces.
  ```

- **`\r\n` (Windows line endings)** are converted to `\n` (UNIX)

## What is left untouched

- Code blocks (`.. code-block::`, `::` blocks)
- Tables (grid and simple)
- Section titles and underlines
- Comments, hyperlink targets, substitution definitions
- Field lists (`:param foo:`, `:type bar:`)
- Option list items (`-x`, `--foo`)
- Block quotes
- Inline RST constructs (``:role:`display <target>` ``, ``*emphasis*``,
  ``**bold**``, etc.) are treated as atomic tokens: they are never split across
  lines, and their internal whitespace is preserved.

## Tested against real-world docs

This tool targets a very specific niche: formatting reStructuredText (RST)
**without breaking the semantic structure of the document**. The integration
test suite runs against a large corpus of real-world `.rst` files (~7800 in
total) from several upstream projects:

- [CPython](https://github.com/python/cpython/tree/main/Doc) (~550 files)
- [Linux](https://github.com/torvalds/linux/tree/master/Documentation) (~3900 files)
- [Python PEPs](https://github.com/python/peps/tree/main/peps) (~740 files)
- [Sphinx](https://github.com/sphinx-doc/sphinx/tree/master/doc) (~150 files)
- [Salt](https://github.com/saltstack/salt/tree/master/doc) (~1100 files)
- [Ansible](https://github.com/ansible/ansible-documentation/tree/devel/docs/docsite/rst) (~480 files)
- [NumPy](https://github.com/numpy/numpy/tree/main/doc/source) (~340 files)
- [pytest](https://github.com/pytest-dev/pytest/tree/main/doc/en) (~260 files)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy/tree/main/doc/build) (~200 files)

For every file the suite verifies:

- **Idempotency**: running the tool twice produces the same output as
  running it once.
- **Width**: no tool-produced line exceeds the target width, except when
  a paragraph contains an unsplittable token (e.g. a long inline
  hyperlink).
- **No double spaces**: no tool-produced prose line contains a bare
  double space.
- **Document tree invariant**: parsing the original and the wrapped file with
  [docutils](https://docutils.sourceforge.io/) produces identical document
  trees (after normalising intra-node whitespace). This confirms that wrapping
  prose never alters headings, directives, code blocks, hyperlinks, or any
  other structural element.

## Comparison with other tools

[docstrfmt](https://github.com/LilSpazJoekp/docstrfmt),
[rstfmt](https://github.com/dzhu/rstfmt), and
[rstformat](https://github.com/vscode-restructuredtext/vscode-restructuredtext)
(the engine behind the VS Code RST extension) are opinionated formatters
in the spirit of [Black](https://github.com/psf/black): they parse RST
into a `docutils` document tree and re-emit it in a canonical shape.

The `docutils` tree discards source-level style (underline character,
bullet marker, indent width, blank-line counts), so the emitter has to
pick one style and rewrite every construct to match it.

`rstwrap` works directly on source lines and only ever rewrites prose.
Section titles, tables, code blocks, bullets, underlines, and blank-line
layout are preserved verbatim; the doctree is guaranteed to parse the
same (enforced by the test suite and by `--safe`). `docutils` is an
optional extra when using `--check`.

Rule of thumb: use `docstrfmt` for a uniform style. Use `rstwrap` to enforce
line width while leaving every other stylistic choice alone.

## License

MIT
