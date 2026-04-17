..
    Regression: RST option list items (``-f FILE``, ``--output FILE``)
    must not be merged into prose paragraphs. Without the
    ``_OPTION_LIST_RE`` check in the dispatch loop, the tool would treat
    option lines as ordinary prose and join them into a single wrapped
    paragraph, destroying the option-list structure in the doctree.

-h         Show help message and exit.
-f FILE    Read input from FILE instead of stdin.
-o FILE    Write output to FILE instead of stdout.
--verbose  Enable verbose output. This is a longer description that might tempt the tool to wrap it together with the next option entry into a single paragraph.
--quiet    Suppress all non-error output.
