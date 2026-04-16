..
    Regression: multiple blank lines between a directive marker and
    its indented body must be preserved (they are part of the
    directive). Multiple blank lines *after* a directive body before
    the next top-level block must be collapsed.

.. doctest::



   >>> 1 + 1
   2



After directive.



.. note::

   Note body paragraph one.



   Note body paragraph two.



Next top-level paragraph.
