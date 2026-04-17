..
    Regression: docutils accepts any non-alphanumeric printable 7-bit
    ASCII punctuation as a section adornment character. Our
    ``_UNDERLINE_CHARS`` had a restricted subset that omitted common
    chars like ``/``. Titles underlined with the missing chars fell
    through to the prose handler and got merged with their underlines,
    destroying the section in the doctree.

    Encountered in Python PEP 3108 which uses ``//////////`` as a
    section underline.

Intro paragraph before.

Python 2.6
//////////

#. First item in the section.

#. Second item.

Trailing paragraph after.
