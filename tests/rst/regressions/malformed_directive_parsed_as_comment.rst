Malformed directive parsed as comment
=====================================

Regression for a bug found in the Linux kernel docs
(``Documentation/userspace-api/media/v4l/mmap.rst``). A line like
``.. note:::ref:...`` is not a valid directive marker (the directive
name is followed by three colons with no space), so docutils parses
the whole block as a single ``comment`` node, not as a directive.

``_handle_directive`` in the tool still treats it as a directive and
re-wraps the indented body, which shifts the line breaks inside the
comment text. ``TestDocutils.assert_nodes_preserved`` requires
``comment`` text to be byte-identical (newlines included), so the
doctree invariant breaks.

The fix is in ``_handle_directive``: only re-wrap the body when the
marker is a syntactically valid directive (name ``::``). Anything
else is a comment and its body must pass through verbatim.

.. note:::ref:`VIDIOC_STREAMOFF <VIDIOC_STREAMON>`
   removes all buffers from both queues as a side effect. Since there is
   no notion of doing anything "now" on a multitasking system, if an
   application needs to synchronize with another event.
