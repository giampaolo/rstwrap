..
    Regression: a simple table may contain another simple table nested
    inside one of its cells (see the Description column below). The
    outer table's closing border is at column 0; the inner border is
    indented. Our collector treated any border-line-followed-by-blank
    as the closing of the outer table, so the inner mini-table's
    closing border (which is indented and followed by a blank line)
    was mistakenly taken as the outer closer, splitting the table and
    breaking the doctree. The fix is to compare the indent of the
    candidate closing border against the indent of the opening border.

    Encountered in the Linux kernel's
    ``Documentation/driver-api/nvdimm/btt.rst``.

3. Theory of Operation
======================


a. The BTT Map
--------------

The map is a simple lookup/indirection table that maps an LBA to an
internal block.

======== =============================================================
Bit      Description
======== =============================================================
31 - 30  Error and Zero flags - Used in the following way:

	== ==  ====================================================
	31 30  Description
	== ==  ====================================================
	0  0   Initial state. Reads return zeroes; Premap = Postmap
	0  1   Zero state: Reads return zeroes
	1  0   Error state: Reads fail; Writes clear 'E' bit
	1  1   Normal Block -- has valid postmap
	== ==  ====================================================

29 - 0   Mappings to internal 'postmap' blocks
======== =============================================================


Some of the terminology that will be subsequently used.
