..
    Regression: a bare ``--`` separator followed by prose (no blank)
    must merge into the paragraph -- docutils parses ``--`` as plain
    text (too short for a section underline).
    Found in Linux ``mm/ksm.rst``.

Some prose paragraph that precedes the separator and is long enough
that it might get re-wrapped by the tool when the width is 79.

--
Izik Eidus,
Hugh Dickins, 17 Nov 2009
