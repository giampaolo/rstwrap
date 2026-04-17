..
    Regression: an enumerated list using ``(a)``, ``(b)``, ... (single
    letter surrounded by parens) is a valid RST enum list with
    ``prefix="("`` and ``suffix=")"``. Encountered in the Linux kernel's
    ``Documentation/admin-guide/cgroup-v2.rst``. The tool's ``_ENUM_RE``
    only matched ``(\d+)`` (parenthesized digit), so letter-form
    parenthesized enums fell through to the prose handler and got
    merged into a single paragraph, breaking the doctree.

setns(2) to another cgroup namespace is allowed when:

(a) the process has CAP_SYS_ADMIN against its current user namespace
(b) the process has CAP_SYS_ADMIN against the target cgroup
    namespace's userns

No implicit cgroup changes happen with attaching to another cgroup
namespace.
