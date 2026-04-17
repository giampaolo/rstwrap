..
    Regression: a quoted literal block (introduced by ``::``) whose
    every line begins with ``*`` (or ``-`` / ``+``) is parsed by
    docutils as a literal block, not as a bullet list. Our main loop
    had the list-item dispatch BEFORE the quoted-literal-block check,
    so the ``*`` lines were intercepted as a bullet list, wrapped, and
    the literal block was destroyed in the doctree.

    Encountered in Python PEP 0653.

This has been rejected for a few reasons::

* Using the class specified in the pattern is more amenable to optimization and can offer better performance.
* Using the class specified in the pattern has the potential to provide better error reporting is some cases.
* Neither approach is perfect, both have odd corner cases.

Trailing prose paragraph after.
