..
    Regression: an inner simple table's closing border (indented,
    followed by blank) was taken as the outer table's closer,
    splitting it. The closer must match the opener's indent.
    Found in Linux ``driver-api/nvdimm/btt.rst``.

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
