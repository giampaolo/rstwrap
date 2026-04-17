..
    Regression: ``N.`` followed by a non-blank line at the list's
    own indent (not at the text column) parses as a paragraph
    starting with ``N.``, not an enum list. Wrapping would create
    a real enum and change the doctree; keep verbatim. Bullets
    have no such ambiguity.

2. When the column did not contain a default or server_default value here, a missing
value on a column configured this way would still render SQL NULL rather than
falling back to not inserting any value, behaving inconsistently.
