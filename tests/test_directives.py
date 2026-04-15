"""Tests for directive handling (prose-body vs opaque)."""

from . import BaseTest


class TestDirectives(BaseTest):
    def test_opaque_directive_body_verbatim(self):
        # code-block is not in _PROSE_BODY_DIRECTIVES; body must pass
        # through byte-identical even if lines are long.
        long_line = "    " + "x" * 100
        src = f".. code-block:: python\n\n{long_line}\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_image_directive_unchanged(self):
        src = ".. image:: foo.png\n   :width: 100\n   :alt: some alt text\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)

    def test_prose_directive_body_wrapped(self):
        # .. note:: is in _PROSE_BODY_DIRECTIVES; its long body must
        # be wrapped.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. note::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. note::")
        for line in out.splitlines()[1:]:
            assert len(line) <= self.WIDTH
        self.check_all(src, out)

    def test_warning_directive_body_wrapped(self):
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. warning::\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. warning::")
        self.check_all(src, out)

    def test_domain_prefixed_prose_directive_body_wrapped(self):
        # e.g. .. py:function:: is treated as "function" after
        # stripping the domain prefix.
        long_body = "   " + " ".join(["word"] * 30)
        src = f".. py:function:: foo(x)\n\n{long_body}\n"
        out = self.wrap(src)
        assert out.startswith(".. py:function::")
        self.check_all(src, out)

    def test_prose_directive_short_body_unchanged(self):
        src = ".. note::\n\n   Short note.\n"
        out = self.wrap(src)
        assert out == src
        self.check_all(src, out)
