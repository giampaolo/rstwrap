..
    Regression: a bare ``--`` line used as a signature/attribution
    separator is immediately followed by prose (no blank line between).
    Encountered in the Linux kernel's ``Documentation/mm/ksm.rst`` where
    the author's name follows a ``--`` separator. This is invalid RST:
    docutils requires >=3 chars for a section underline and parses a
    bare ``--`` as plain text with an INFO-level warning ("Possible
    incomplete section title. Treating the overline as ordinary text
    because it's so short."). Our tool therefore merges the ``--`` into
    the following paragraph -- matching what docutils does -- and the
    doctree invariant still holds.

Some prose paragraph that precedes the separator and is long enough
that it might get re-wrapped by the tool when the width is 79.

--
Izik Eidus,
Hugh Dickins, 17 Nov 2009
