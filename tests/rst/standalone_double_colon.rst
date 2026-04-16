..
    Regression: a standalone ``::`` on its own line introduces a literal
    block. If ``_handle_prose`` merges the ``::`` into the preceding
    paragraph, the ``::`` becomes a trailing ``:`` in the prose and the
    literal block is lost in the doctree. The guard in ``_handle_prose``
    must stop accumulating when it encounters a bare ``::`` line.

This paragraph has enough filler text to push the content near the wrap
boundary, which tempts the tool to merge the next line.

::

    This is a literal block.
    It must stay as-is.

Another paragraph after the literal block.
