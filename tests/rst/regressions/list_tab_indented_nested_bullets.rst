..
    Regression: visually_attached uses ``lstrip(' ')`` (no tabs), so
    tab-nested children read as indent 0; wrapping the parent flipped
    the doctree. Nested dispatch is gated to space-indent only.
    Found in Linux ``misc-devices/xilinx_sdfec.rst``.

Monitor for Interrupts
----------------------

	- Use the poll system call to monitor for an interrupt. The poll system call waits for an interrupt to wake it up or times out if no interrupt occurs.
	- On return Poll ``revents`` will indicate whether stats and/or state have been updated
		- ``POLLPRI`` indicates a critical error and the user should use :c:macro:`XSDFEC_GET_STATUS` and :c:macro:`XSDFEC_GET_STATS` to confirm
