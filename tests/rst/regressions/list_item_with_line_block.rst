..
    Regression: a bullet list item whose body is an RST line block
    (each continuation line starts with ``|``) must be preserved
    verbatim. ``_handle_list_run`` was merging the ``|``-prefixed
    continuation lines into the item's paragraph under ``--join``,
    destroying the ``<line_block>`` structure in the doctree.
    Encountered in Python PEP 0011.

Some paragraph before the list.

* | Name:             VMS (issue 16136)
  | Unsupported in:   Python 3.3
  | Code removed in:  Python 3.4

* | Name:             Windows 2000
  | Unsupported in:   Python 3.3
  | Code removed in:  Python 3.4

Trailing paragraph after.
