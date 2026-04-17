..
    Regression: ``.. note:::ref:...`` is not a valid directive (no
    space after ``::``), so docutils parses the whole block as a
    comment -- body must pass through verbatim.
    Found in Linux ``userspace-api/media/v4l/mmap.rst``.

.. note:::ref:`VIDIOC_STREAMOFF <VIDIOC_STREAMON>`
   removes all buffers from both queues as a side effect. Since there is
   no notion of doing anything "now" on a multitasking system, if an
   application needs to synchronize with another event.
