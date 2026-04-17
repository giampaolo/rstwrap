..
    Regression: docutils accepts any non-alnum 7-bit ASCII
    punctuation as an adornment char. _UNDERLINE_CHARS omitted
    ``/``, so titles like ``Python 2.6\n//////`` fell into the
    prose handler and lost their section.
    Found in Python PEP 3108.

Intro paragraph before.

Python 2.6
//////////

#. First item in the section.

#. Second item.

Trailing paragraph after.
