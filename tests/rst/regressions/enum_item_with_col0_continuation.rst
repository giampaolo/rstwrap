Enum item with col-0 continuation is prose
==========================================

Regression: a numbered marker (``1.``, ``2.``, ``a.``, ...) followed
by a non-blank continuation at the list's own indent (not at the
text column) is parsed by docutils as a plain paragraph starting
with "N.", not as an enumerated list. Wrapping the first line
alone would create a well-formed enum list and diverge from the
source doctree. The prose-ambiguity guard in ``_handle_list_run``
keeps the item verbatim in this case.

Bullet lists (``*``, ``-``, ``+``) don't have this ambiguity --
docutils always parses them as lists -- so only enum markers need
the guard.

2. When the column did not contain a default or server_default value here, a missing
value on a column configured this way would still render SQL NULL rather than
falling back to not inserting any value, behaving inconsistently.
