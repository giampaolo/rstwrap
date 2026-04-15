..
    Regression: a 1-char section title (``R``) with a 1-char underline
    (``-``) is a valid RST section -- docutils recognizes any repeated
    punctuation underline of length >= title length. ``_is_short_
    underline`` only accepted length 2, so the ``-`` fell through to
    the prose handler and got merged with the title into ``R -``,
    destroying the section. Encountered in Python PEP 0450.

Some prose paragraph before.

R
-

R (and its cousin S) is a programming language designed for statistics work.

C#
--

C# is a language too.
