# Changelog

## Unreleased

- IMPORTANT: Collapse multiple consecutive blank lines between paragraphs into
  one.
- IMPORTANT: Wrap nested bullet lists: when a parent bullet is followed by a
  blank line, over-width children are re-wrapped alongside the parent.
- Fix: malformed directive markers (e.g. `.. note:::ref:`) were mis-parsed as
  directives and their bodies re-wrapped, breaking the doctree.
- Fix: nested bullets without a preceding blank line were merged into the
  parent paragraph under `join=True`.

## 0.1.0 - 2026-04-16

Initial release. Main features:

- Wrap prose paragraphs, list items, and body of directives (`.. note::`,
  `.. warning::`, ...) to a target line width.
- Leave structural content (code blocks, tables, titles, comments, etc.)
  identical.
- `--check` / `--diff` modes for CI enforcement.
- `--safe` mode: verify with docutils that the output's doctree is identical
  to the input's.
- Configurable via `[tool.rstwrap]` in `pyproject.toml`.
- stdin/stdout mode (`rstwrap -`) for editor format-on-save integration.
