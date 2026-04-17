..
    Regression: a bullet-list item whose bullet is followed by a tab
    (``-<TAB>text``) has its text column at 8 after tab expansion, not
    at 2 (the char count). When the line is long enough to be
    re-wrapped, the tool must emit a continuation indent that
    docutils still reads as >= col 8 -- otherwise the continuation is
    parsed as a separate ``block_quote`` and the doctree diverges
    from the source's doctree. Using two spaces (char count of the
    ``-<TAB>`` prefix) breaks the invariant; keeping the tab (or
    visually equivalent whitespace) in the subsequent indent
    preserves it. Encountered in Linux's
    ``Documentation/admin-guide/kernel-per-CPU-kthreads.rst``.

References
==========

-	Documentation/core-api/irq/irq-affinity.rst: Binding interrupts to sets of CPUs.

-	Documentation/admin-guide/cgroup-v1: Using cgroups to bind tasks to sets of CPUs.
