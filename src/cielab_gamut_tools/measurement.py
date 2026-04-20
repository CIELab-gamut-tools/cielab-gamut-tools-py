"""
RGB test signal generation for display measurement.

Generates the ordered set of unique RGB surface points for display gamut
measurement, as specified in IDMS v1.3 §5.32, IEC 62977-3-5 Annex A, and
IEC 62906-6-1 Annex A.2.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def make_rgb_signals(
    m: int = 11,
    bits: int = 8,
) -> NDArray[np.integer]:
    """
    Generate the ordered set of RGB input signal values for gamut measurement.

    Produces the unique surface points of the RGB cube tessellation at grid
    resolution ``m``, scaled to the requested integer bit depth. This matches
    the MATLAB reference::

        [~, rgb] = make_tesselation(V);
        rgb = unique(rgb, 'rows');   % 726 → 602 for m=11

    The number of unique points is:

    .. code-block:: none

        n = 6m² − 12m + 8

    Standard sizes:

    =====  =====  ========================
      m      n    Note
    =====  =====  ========================
      11    602   Normative reference set
       9    386   Reduced (estimate only)
       7    218   Reduced (estimate only)
       5     98   Reduced (estimate only)
    =====  =====  ========================

    Args:
        m: Number of grid points per cube edge (default 11). Must be ≥ 2.
        bits: Output bit depth (default 8). Signal values are integers in
            ``[0, 2**bits - 1]``.

    Returns:
        Integer array of shape (n, 3) containing the RGB signal values in
        lexicographic order, with ``n = 6m² − 12m + 8``.

    Raises:
        ValueError: If ``m < 2`` or ``bits < 1``.

    Example:
        >>> signals = make_rgb_signals(m=11, bits=8)
        >>> signals.shape
        (602, 3)
        >>> signals.dtype
        dtype('uint16')
    """
    if m < 2:
        raise ValueError(f"m must be at least 2, got {m}")
    if bits < 1:
        raise ValueError(f"bits must be at least 1, got {bits}")

    from cielab_gamut_tools.geometry.tesselation import make_tesselation

    # make_tesselation resolution = number of subdivisions = m - 1
    _, vertices = make_tesselation(resolution=m - 1)

    # Scale from [0, 1] to integer range [0, max_val]
    max_val = (1 << bits) - 1
    scaled = np.round(vertices * max_val).astype(np.int64)

    # Deduplicate — matches MATLAB unique(rgb, 'rows') lexicographic sort
    unique_signals = np.unique(scaled, axis=0)

    expected_n = 6 * m * m - 12 * m + 8
    if len(unique_signals) != expected_n:
        raise RuntimeError(
            f"Expected {expected_n} unique signals for m={m}, got {len(unique_signals)}"
        )

    # Store as uint16 — fits any practical bit depth (≤ 16 bits)
    return unique_signals.astype(np.uint16)
