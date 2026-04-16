..
    Regression: when a prose paragraph contains a long inline token
    (e.g. a hyperlink with display text) that cannot be split across
    lines, wrapping might produce an output line longer than the target
    width. The no-lengthen guard in ``_handle_prose`` detects this and
    keeps the paragraph verbatim rather than making things worse.

See the `prebuilt binary packages are
available <https://docs.python.org/dev/download.html>`_.  Also see other stuff that matters.
