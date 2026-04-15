..
    Regression: a multi-line prose paragraph immediately followed by
    an indented non-blank line (no blank line between) is parsed by
    docutils as paragraph + block_quote. Merging the prose into a
    single line changes docutils' interpretation to definition_list
    (term + definition), breaking the doctree.

    The source is technically malformed RST (docutils emits an ERROR
    for the unexpected indent), but still parseable and our doctree
    invariant must hold. Encountered in Python PEPs' header blocks
    (see PEP 0246), which use this layout without blank separators.

PEP: 246
Title: Object Adaptation
Author: Alex Martelli <aleaxit@gmail.com>,
        Clark C. Evans <cce@clarkevans.com>
Status: Rejected


Trailing paragraph that should not be affected.
