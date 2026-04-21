"""
Chromatic adaptation transforms.

Provides Bradford chromatic adaptation for converting XYZ values
measured under one illuminant to another (e.g., D65 to D50).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from cielab_gamut_tools.colorspace.lab import xy_to_XYZ


# Bradford transformation matrix (XYZ to LMS cone response)
BRADFORD_M = np.array([
    [ 0.8951,  0.2664, -0.1614],
    [-0.7502,  1.7135,  0.0367],
    [ 0.0389, -0.0685,  1.0296],
])

BRADFORD_M_INV = np.linalg.inv(BRADFORD_M)

# Standard illuminant white points (xy chromaticity)
D65_XY = np.array([0.31272, 0.32903])
D50_XY = np.array([0.34567, 0.35850])


def adapt_d65_to_d50(
    xyz: NDArray[np.floating],
    source_white: NDArray[np.floating] = D65_XY,
) -> NDArray[np.floating]:
    """
    Adapt XYZ values from D65 (or other source) to D50 using Bradford transform.

    Args:
        xyz: XYZ tristimulus values, shape (N, 3) or (3,).
        source_white: Source illuminant xy chromaticity (default D65).

    Returns:
        D50-adapted XYZ values, same shape as input.

    Note:
        The Bradford transform is preferred for color appearance applications
        as it includes a degree of nonlinearity that better models human
        chromatic adaptation.
    """
    return chromatic_adaptation(xyz, source_white, D50_XY)


def chromatic_adaptation(
    xyz: NDArray[np.floating],
    source_white_xy: NDArray[np.floating],
    dest_white_xy: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Apply Bradford chromatic adaptation transform.

    Args:
        xyz: XYZ tristimulus values, shape (N, 3) or (3,).
        source_white_xy: Source illuminant xy chromaticity.
        dest_white_xy: Destination illuminant xy chromaticity.

    Returns:
        Adapted XYZ values, same shape as input.
    """
    # Convert white points from xy to XYZ
    source_white_XYZ = xy_to_XYZ(source_white_xy)
    dest_white_XYZ = xy_to_XYZ(dest_white_xy)

    return chromatic_adaptation_xyz(xyz, source_white_XYZ, dest_white_XYZ)


def chromatic_adaptation_xyz(
    xyz: NDArray[np.floating],
    source_white_xyz: NDArray[np.floating],
    dest_white_xyz: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Apply Bradford chromatic adaptation transform using XYZ white points directly.

    Mirrors MATLAB's ``camcat_cc(XYZ, XYZn, D50)``.  Accepts white points as
    XYZ tristimulus values rather than xy chromaticities — use this when the
    white point is known in XYZ (e.g. from a measurement row) rather than as a
    standard-illuminant chromaticity.

    Args:
        xyz: XYZ tristimulus values, shape (N, 3) or (3,).
        source_white_xyz: Source white point in XYZ, shape (3,).
        dest_white_xyz: Destination white point in XYZ, shape (3,).

    Returns:
        Adapted XYZ values, same shape as input.
    """
    xyz = np.asarray(xyz)
    source_white_xyz = np.asarray(source_white_xyz)
    dest_white_xyz = np.asarray(dest_white_xyz)

    # Transform white points to cone response domain
    source_lms = BRADFORD_M @ source_white_xyz
    dest_lms = BRADFORD_M @ dest_white_xyz

    # Compute adaptation matrix
    scale = dest_lms / source_lms
    M_adapt = BRADFORD_M_INV @ np.diag(scale) @ BRADFORD_M

    # Apply to input
    if xyz.ndim == 1:
        return M_adapt @ xyz
    else:
        return xyz @ M_adapt.T
