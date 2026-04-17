..
    Regression: multiple consecutive blank lines between top-level
    paragraphs must be collapsed into one. Blank lines inside
    indented content (literal blocks, directive bodies) and simple
    tables must be preserved.

Paragraph one.



Paragraph two after three blank lines.




Paragraph three after four blank lines.

A literal block with internal double blanks::

   code line A


   code line B


   code line C

A simple table with double blank lines between rows:

======  =====
Col A   Col B
======  =====
row 1   val 1


row 2   val 2
======  =====

Trailing prose.
