..
    Regression: nested-list dispatch fires on a homemade ASCII
    table whose rows begin with ``+``. The intro ends with ``:``
    (not ``::``), so the opaque-context guard doesn't apply. Rows
    must exceed width, else ``fits_verbatim`` masks the bug.
    Found in Linux ``admin-guide/pm/amd-pstate.rst``.

Results:

     Open selftest.tbench.csv :

     +-------------------------------------------------+--------------+----------+
     + Governor                                        | Round        | Des-perf |
     +-------------------------------------------------+--------------+----------+
     + amd-pstate-ondemand                             | 1            | 165.329  |
     +-------------------------------------------------+--------------+----------+
