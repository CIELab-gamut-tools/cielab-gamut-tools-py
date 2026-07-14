# TODO

There is a discrepancy between the python and matlab, but neither are probably correct.  They deal with non-standard vertex grids differently.
The Matlab does not fix what grid points to use, so long as all are defined everywhere, but a user could 'hide' unfortunate
performance by using non-standard vertex spacing.  The python interpolates to a standard spacing, but will take ANY data as input and fill in missing vertices.

Probably two options:

1. do we treat MATLAB's "complete grid or error" as the normative behaviour and remove Python's silent interpolation
2. do we keep interpolation but restrict it to structurally-valid grids (uniform spacing, count checks) so it can't be used to launder cherry-picked measurements
Either is defensible.  Or, perhaps, it standard mode it is strict, but you can specify a permissive mode?
