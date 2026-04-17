..
    Regression: ``(a)``, ``(b)``, ... is a valid enum list.
    _ENUM_RE only matched parenthesized digits, so letter-form items
    fell into the prose handler and merged into a paragraph.
    Found in Linux ``admin-guide/cgroup-v2.rst``.

setns(2) to another cgroup namespace is allowed when:

(a) the process has CAP_SYS_ADMIN against its current user namespace
(b) the process has CAP_SYS_ADMIN against the target cgroup
    namespace's userns

No implicit cgroup changes happen with attaching to another cgroup
namespace.
