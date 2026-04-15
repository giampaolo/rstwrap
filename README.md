# rst-wrap-lines

A command-line tool that wraps prose paragraphs of `.rst` (reStructured Text)
files to a maximum line length.

Only prose paragraphs and list items are re-wrapped. Everything else
(directives, literal blocks, tables, section underlines, comments, indented
blocks) is passed through byte-identical. If a file is already clean, the tool
produces a zero-byte diff.

## Installation

```
pip install rst-wrap-lines
```

## Usage

```bash
rst-wrap-lines docs/*.rst
rst-wrap-lines docs/                # whole dir, recursive
rst-wrap-lines --check docs/*.rst
rst-wrap-lines --width 80 foo.rst
rst-wrap-lines --join docs/*.rst    # also merge short consecutive lines
rst-wrap-lines --safe docs/*.rst    # verify output with docutils
cat foo.rst | rst-wrap-lines -      # read stdin, write to stdout
```

Options:

- `-w`, `--width` — maximum line length (default: 79)
- `--check` — exit with code 1 if any file would be changed; do not write
- `--diff` — print a unified diff instead of writing files
- `--join` — also merge short consecutive lines inside a paragraph onto
  one line (up to the target width). For example:

  ```
  foo         →   foo bar zoo
  bar
  zoo
  ```

- `--safe` — after wrapping, parse both the input and the output with
  [docutils](https://docutils.sourceforge.io/) and compare the resulting
  document trees. Any file whose tree would change is left untouched and
  a diff is printed to stderr; the process then exits with code 1. Use
  this as a defensive check in CI or on first-time runs against an
  unfamiliar corpus. Requires docutils:

  ```
  pip install 'rst-wrap-lines[safe]'
  ```

- **stdin / stdout** — pass `-` instead of a file path to read RST from
  stdin and write the formatted result to stdout. Combines with `--check`
  (silent, exit 1 if changed) and `--diff` (writes the diff to stdout).
  This is the integration point for editor formatters (Vim's
  `formatprg`, VS Code formatters, format-on-save plugins, etc.).

- `-q`, `--quiet` — suppress informational output.

- `--version` — print the version and exit

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

The integration test suite runs against a large corpus of real-world `.rst`
files (~1,800 in total) from several upstream projects:

- [CPython](https://github.com/python/cpython/tree/main/Doc) (~550 files)
- [Sphinx](https://github.com/sphinx-doc/sphinx/tree/master/doc) (~160 files)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy/tree/main/doc/build) (~200 files)
- [pytest](https://github.com/pytest-dev/pytest/tree/main/doc/en) (~260 files)

For every file the suite verifies:

- **Idempotency** — running the tool twice produces the same output as
  running it once.
- **Width** — no tool-produced line exceeds the target width (verbatim
  passthrough of already-long source lines is allowed).
- **No double spaces** — no tool-produced prose line contains a bare
  double space.
- **Document tree invariant** — parsing the original and the wrapped
  file with [docutils](https://docutils.sourceforge.io/) produces
  identical document trees (after normalising intra-node whitespace).
  This confirms that rewrapping prose never alters headings, directives,
  code blocks, hyperlinks, or any other structural element.

## Comparison with [rstfmt](https://github.com/dzhu/rstfmt)

[rstfmt](https://github.com/dzhu/rstfmt) is an opinionated RST formatter
in the style of Black or gofmt. It parses each file into a full docutils
AST and re-emits a canonical layout from the tree. This project takes the
opposite approach: source is edited line-by-line with regex-level
heuristics, and anything the tool can't confidently rewrap is passed
through byte-identical.

|                              | rstfmt                         | rst-wrap-lines                       |
| ---                          | ---                            | ---                                  |
| Approach                     | parse to AST, re-emit          | edit source in place                 |
| Philosophy                   | canonical format (Black/gofmt) | minimal diff                         |
| Runtime dep on docutils      | yes, always                    | no (only with `--safe`)              |
| Works on un-parseable input  | no                             | yes (unknown directives passed through) |
| Diff on an already-clean file| can be large                   | zero bytes                           |
| Normalises bullets / indent / underline styles | yes     | no                                   |

Pick rstfmt if you want one canonical layout enforced across a project.
Pick rst-wrap-lines if you're adopting line-length rules incrementally on
an established codebase and can't reformat everything at once.

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
