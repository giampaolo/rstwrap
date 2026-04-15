"""Tests for inline RST markup that must never be broken across lines."""

from . import BaseTest


class TestInlineMarkup(BaseTest):
    def test_inline_literal_not_broken(self):
        src = "Prose with ``an inline literal that has spaces inside`` here.\n"
        out = self.wrap(src)
        assert "``an inline literal that has spaces inside``" in out
        self.check_all(src, out)

    def test_inline_literal_spaces_not_collapsed(self):
        # Spaces inside ``...`` must survive space-collapsing.
        src = "See ``hello  world`` for details.\n"
        out = self.wrap(src)
        assert "``hello  world``" in out
        self.check_all(src, out)

    def test_emphasis_not_broken(self):
        src = "Prose with *emphasized words across tokens* here.\n"
        out = self.wrap(src)
        assert "*emphasized words across tokens*" in out
        self.check_all(src, out)

    def test_strong_not_broken(self):
        src = "This is **very important words** in a sentence.\n"
        out = self.wrap(src)
        assert "**very important words**" in out
        self.check_all(src, out)

    def test_role_not_broken(self):
        src = "See :func:`some function name` for details.\n"
        out = self.wrap(src)
        assert ":func:`some function name`" in out
        self.check_all(src, out)

    def test_hyperlink_ref_not_broken(self):
        src = "See `the full documentation <https://example.com>`_ for more.\n"
        out = self.wrap(src)
        assert "`the full documentation <https://example.com>`_" in out
        self.check_all(src, out)

    def test_anonymous_hyperlink_ref_not_broken(self):
        src = "See `anonymous link <https://example.com>`__ here.\n"
        out = self.wrap(src)
        assert "`anonymous link <https://example.com>`__" in out
        self.check_all(src, out)

    def test_substitution_ref_not_broken(self):
        src = "Use |my substitution ref| in the text here.\n"
        out = self.wrap(src)
        assert "|my substitution ref|" in out
        self.check_all(src, out)

    def test_footnote_ref_unchanged(self):
        src = "As noted [1]_ previously.\n"
        out = self.wrap(src)
        assert "[1]_" in out
        self.check_all(src, out)
