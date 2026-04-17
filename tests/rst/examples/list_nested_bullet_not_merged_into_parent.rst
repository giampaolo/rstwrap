..
    Example: a deeper-indent bullet at the parent's text column
    (malformed, no blank line) was slurped into the parent and
    re-flowed as ``- Parent. - Nested.`` on one line, destroying
    the bullet structure. Doctree is unchanged either way, so the
    catch lives in the paired unit test.

- Parent line short.
  - Nested item.
