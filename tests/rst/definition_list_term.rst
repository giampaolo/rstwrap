..
    Regression: a definition-list term is an unindented line immediately
    followed (no blank line) by an indented definition body. If the tool
    wraps a long term line into two lines, docutils parses it as two
    separate terms instead of one, changing the doctree. The dispatch
    loop in ``wrap_rst`` must detect this pattern and pass the term
    through verbatim.

term one
    The definition of term one.

a longer definition list term that approaches the target width to stress the passthrough
    This definition body belongs to the long term above. If the term
    were wrapped, it would split into two terms and break the doctree.

another term
    With its definition.
