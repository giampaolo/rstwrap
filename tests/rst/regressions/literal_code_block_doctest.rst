..
    Regression: doctest blocks inside a ``::`` literal block with long
    output lines must be preserved byte-for-byte. The tool must not
    wrap or merge any line.

Example usage::

   >>> import os
   >>> os.path.join("/tmp", "very-long-directory-name", "another-deeply-nested-subdirectory", "yet-another-level", "final-file.txt")
   '/tmp/very-long-directory-name/another-deeply-nested-subdirectory/yet-another-level/final-file.txt'
   >>> sorted(["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo", "lima", "mike"])
   ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf', 'hotel', 'india', 'juliet', 'kilo', 'lima', 'mike']

Trailing prose paragraph.
