..
    Regression: a short section title (1-2 chars) with a matching
    2-char underline, followed immediately by the section body *with
    no blank line* between the underline and the first body paragraph.
    Docutils parses this as a section with title + underline + body,
    but our tool's title-underline dispatch only accepted underlines
    of 3+ chars. The ``--`` fell through to the prose handler, which
    merged it into the body paragraph, destroying the section.

    The existing ``short_section_underline.rst`` fixture covers the
    blank-line case (``io\n--\n\n...``); this one covers the no-blank
    case. Encountered in the Linux kernel's
    ``Documentation/kbuild/kbuild.rst``.

CROSS_COMPILE is also used for ccache in some setups.

CF
--
Additional options for sparse.

CF is often used on the command-line like this.
