..
    Regression: a "quoted literal block" is introduced by ``::`` just
    like a regular literal block, but its body is unindented -- every
    line instead begins with the same non-alphanumeric quoting
    character (here ``#``). Our tool treated the unindented body as
    prose, merged the lines, and broke the literal block in the
    doctree. Encountered in the Linux kernel's
    ``Documentation/driver-api/usb/typec_bus.rst``.

Helper macro ``TYPEC_MODAL_STATE()`` can also be used::

#define ALTMODEX_CONF_A = TYPEC_MODAL_STATE(0);
#define ALTMODEX_CONF_B = TYPEC_MODAL_STATE(1);

Trailing prose paragraph comes after.
