..
    Regression: nested-list dispatch fired on an indented bullet
    right after indented prose (no blank); docutils parses the run
    as one paragraph (``*`` is inline text).
    Found in pytest ``doc/en/backwards-compatibility.rst``.

a) trivial: APIs that trivially translate to the new mechanism.

   For the PR to mature from POC to acceptance, it must contain:
   * Setup of deprecation errors/warnings that help users fix and port their code. If it is possible to introduce a deprecation period under the current series, before the true breakage, it should be introduced in a separate PR and be part of the current release stream.
   * Detailed description of the rationale and examples on how to port code in ``doc/en/deprecations.rst``.
