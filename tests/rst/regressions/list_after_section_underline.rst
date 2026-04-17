List after section underline
============================

Regression for a bug where a bullet list directly following a
section underline (no blank line between them) was not recognised
as a list. The main loop's block-start predicate required the
previous output line to be blank, so the bullets fell through to
the prose / definition-list branches and got merged or mangled.

Subsection
----------
* An item that fits under width.
* A long bullet item whose content is definitely over seventy-nine chars so it wraps.
* Third item.
