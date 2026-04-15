# rst-wrap-lines

A command-line tool to wrap prose paragraphs in reStructuredText (.rst)
files to a maximum line width.

Only prose paragraphs and list items are re-wrapped. Everything else
(directives, literal blocks, tables, section underlines, comments, indented
blocks) is left unchanged.

## Installation

```
pip install rst-wrap-lines
```

## Usage

Examples:

```bash
rst-wrap-lines docs/*.rst
rst-wrap-lines docs/                # whole dir, recursive
rst-wrap-lines --check docs/*.rst
rst-wrap-lines --width 120 foo.rst
rst-wrap-lines --join docs/*.rst    # also merge short consecutive lines
rst-wrap-lines --safe docs/*.rst    # verify output with docutils
cat foo.rst | rst-wrap-lines -      # read stdin, write to stdout
```

Options:

- `-w`, `--width`: maximum line length (default: 79)
- `--diff`: print a unified diff instead of writing files
- `--check`: exit with code 1 if any file would be changed; don't write
- `--join`: also merge short consecutive lines within a paragraph into one
  (up to the target width).
- `--safe`: after wrapping, parse both the input and the output with
  [docutils](https://docutils.sourceforge.io/), and skip any file whose
  document tree would change (printing a diff to stderr, exit code 1). Requires
  `pip install 'rst-wrap-lines[safe]'`.
- `-q`, `--quiet`: suppress informational output.
- `--version`: print the version and exit

## Editor integration

Use `-` instead of a file path to read from stdin and write to stdout.
This lets you hook it into any editor that can pipe the current buffer
through a shell command, and format `.rst` files on save.

### Vim / Neovim

Add to `~/.vimrc`:

```vim
autocmd BufWritePre *.rst silent! %!rst-wrap-lines -
```

### VS Code

With the [Custom Local Formatters](https://marketplace.visualstudio.com/items?itemName=jkillian.custom-local-formatters)
extension:

```json
"customLocalFormatters.formatters": [
  {
    "command": "rst-wrap-lines -",
    "languages": ["restructuredtext"]
  }
]
```

### Emacs

```elisp
(defun rst-wrap-lines-buffer ()
  (interactive)
  (let ((p (point)))
    (shell-command-on-region (point-min) (point-max)
                             "rst-wrap-lines -" nil t)
    (goto-char p)))
```

## Configuration via pyproject.toml

Project-wide defaults can be set in a `[tool.rst-wrap-lines]` section of
`pyproject.toml`. The tool walks up from the current working directory
to find the nearest one. Supported keys:

```toml
[tool.rst-wrap-lines]
width = 79
join = true
safe = true
```

Command-line flags **override** anything set in `pyproject.toml`. To turn
off a setting from the CLI for a single run, use the negation flags
`--no-join` / `--no-safe`. Per-invocation flags (`--check`, `--diff`) are not
configurable in pyproject.toml — they're run modes, not project policy.

## What gets wrapped

- Prose paragraphs
- List items (bullet and enumerated), including multi-line continuations
- Bodies of prose-body directives (`.. note::`, `.. warning::`,
  `.. versionadded::`, `.. class::`, etc.)
- Double spaces in prose are removed (e.g. `hello  world` → `hello world`),
  even when the paragraph already fits within the target width
- Trailing whitespace is stripped from every line.

With `--join`, short consecutive lines inside a paragraph are merged onto one
line (up to the target width). Without the flag, existing line breaks within
prose are preserved and only over-width lines get wrapped.

## What is left untouched

- Literal blocks (`.. code-block::`, `::` blocks)
- Tables (grid and simple)
- Section titles and underlines
- Comments, hyperlink targets, substitution definitions
- Field lists (`:param foo:`, `:type bar:`)
- Definition list terms and their bodies
- Option list items (`-x`, `--foo`)
- Block quotes

Inline RST constructs that contain internal whitespace (`` ``like this`` ``,
``:role:`display <target>` ``, ``*emphasis*``, ``**bold**``, etc.) are treated
as atomic tokens and never broken across lines. Spaces inside inline constructs
are left intact.

## Tested against real-world docs

This tool fills a very specific niche: formatting reStructuredText (RST)
**without breaking the semantic structure of the document**. The integration
test suite runs against a large corpus of real-world `.rst` files (~15.000 in
total) from several upstream projects:

- [CPython](https://github.com/python/cpython/tree/main/Doc) (~550 files)
- [Sphinx](https://github.com/sphinx-doc/sphinx/tree/master/doc) (~160 files)
- [Linux](https://github.com/torvalds/linux/tree/master/Documentation) (~1000 files)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy/tree/main/doc/build) (~200 files)
- [pytest](https://github.com/pytest-dev/pytest/tree/main/doc/en) (~260 files)
- [Python PEPs](https://github.com/python/peps/tree/main/peps) (~730 files)
- [Ansible](https://github.com/ansible/ansible-documentation/tree/devel/docs/docsite/rst) (~280 files)
- [NumPy](https://github.com/numpy/numpy/tree/main/doc/source) (~350 files)
- [Salt](https://github.com/saltstack/salt/tree/master/doc) (~2000 files)

For every file the suite verifies:

- **Idempotency**: running the tool twice produces the same output as
  running it once.
- **Width**: no tool-produced line exceeds the target width (verbatim
  passthrough of already-long source lines is allowed).
- **No double spaces**: no tool-produced prose line contains a bare
  double space.
- **Document tree invariant**: parsing the original and the wrapped
  file with [docutils](https://docutils.sourceforge.io/) produces
  identical document trees (after normalising intra-node whitespace).
  This confirms that rewrapping prose never alters headings, directives,
  code blocks, hyperlinks, or any other structural element.

## Development

```
make test                # run all tests
make test-parallel       # same, in parallel (faster)
make lint-all            # ruff + black (check-only)
make fix-all             # auto-apply formatter and lint fixes
```

The first test run clones the external doc repos (sparse, shallow) into
`/tmp/rst-wrap-lines-<project>/` and reuses them on subsequent runs.

## License

MIT
