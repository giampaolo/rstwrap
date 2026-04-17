..
    Regression: a quoted literal block after ``::`` whose lines start
    with ``*`` / ``-`` / ``+`` is literal, not a bullet list.
    Quoted-literal check must come before list dispatch.
    Found in Python PEP 0653.

This has been rejected for a few reasons::

* Using the class specified in the pattern is more amenable to optimization and can offer better performance.
* Using the class specified in the pattern has the potential to provide better error reporting is some cases.
* Neither approach is perfect, both have odd corner cases.

Trailing prose paragraph after.
