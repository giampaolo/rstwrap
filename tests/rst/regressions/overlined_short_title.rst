..
    Regression: an overlined title uses a line of punctuation above
    and below a short title (e.g. ``==`` overline + ``rv`` + ``==``
    underline). The main loop had a passthrough for ``_is_underline``
    bare lines (3+ chars) but not for 2-char ``_is_short_underline``,
    so the ``==`` overline fell through to the prose handler and got
    merged with the title into ``== rv``, destroying the section in
    the doctree.

    Encountered in the Linux kernel's
    ``Documentation/tools/rv/rv.rst``.

.. SPDX-License-Identifier: GPL-2.0

==
rv
==
--------------------
Runtime Verification
--------------------

:Manual section: 1
