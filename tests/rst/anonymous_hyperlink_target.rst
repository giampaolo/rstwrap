..
    Regression: anonymous hyperlink targets (``__ URL``) must be passed
    through verbatim. Without the ``stripped.startswith("__ ")`` guard
    in the dispatch loop, the tool would merge the target URL into the
    surrounding prose paragraph, turning it into garbled text and losing
    the hyperlink target from the doctree.

`Example link`__

__ https://example.com/some/very/long/path/that/should/not/be/merged

Another paragraph after the anonymous target.
