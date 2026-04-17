..
    Regression: a quoted literal block after ``::`` has an unindented
    body whose every line starts with the same quote char (here
    ``#``). Treated as prose, the lines got merged.
    Found in Linux ``driver-api/usb/typec_bus.rst``.

Helper macro ``TYPEC_MODAL_STATE()`` can also be used::

#define ALTMODEX_CONF_A = TYPEC_MODAL_STATE(0);
#define ALTMODEX_CONF_B = TYPEC_MODAL_STATE(1);

Trailing prose paragraph comes after.
