..
    Regression: an enumerated list that follows a 2-char section
    underline was not recognized as a new block. The ``at_block_start``
    predicate checked ``_is_underline`` (3+ chars) but not
    ``_is_short_underline`` (1-2 chars), so the first item's marker
    fell through to the prose handler and the items got merged into a
    single paragraph. Encountered in Ansible's
    ``dev_guide/style_guide/spelling_word_choice.rst``.

Intro.

MB
^^
(1) When spelled MB, short for megabyte (1,000,000 or 1,048,576 bytes).
(2) When spelled Mb, short for megabit.

Trailing paragraph.
