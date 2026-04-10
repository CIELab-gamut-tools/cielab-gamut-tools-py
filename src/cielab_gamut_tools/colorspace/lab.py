"""
CIE XYZ and CIELab color space conversions.

CIELab is a perceptually uniform color space defined by CIE 15:2004.
All conversions use the D50 reference illuminant as per ICC standards.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


# D50 reference white XYZ values (Y=1 normalization)
D50_WHITE_XYZ = np.array([0.96422, 1.0, 0.82521])

# CIELab conversion constants
EPSILON = 216 / 24389  # (6/29)^3
KAPPA = 24389 / 27     # (29/3)^3


def xyz_to_lab(
    xyz: NDArray[np.floating],
    white: NDArray[np.floating] = D50_WHITE_XYZ,
) -> NDArray[np.floating]:
    """
    Convert CIE XYZ to CIELab.

    Args:
        xyz: XYZ tristimulus values, shape (N, 3) or (3,).
        white: Reference white XYZ (default D50).

    Returns:
        CIELab values [L*, a*, b*], same shape as input.

    Note:
        Input XYZ should be adapted to D50 before conversion for
        correct results. Use `adapt_d65_to_d50()` if your data is
        measured under D65 illumination.
    """
    xyz = np.asarray(xyz)
    white = np.asarray(white)

    # Normalize by white point
    xyz_normalized = xyz / white

    # Apply nonlinear transform
    f = _lab_f(xyz_normalized)

    # Compute Lab
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])

    return np.stack([L, a, b], axis=-1)


def lab_to_xyz(
    lab: NDArray[np.floating],
    white: NDArray[np.floating] = D50_WHITE_XYZ,
) -> NDArray[np.floating]:
    """
    Convert CIELab to CIE XYZ.

    Args:
        lab: CIELab values [L*, a*, b*], shape (N, 3) or (3,).
        white: Reference white XYZ (default D50).

    Returns:
        XYZ tristimulus values, same shape as input.
    """
    lab = np.asarray(lab)
    white = np.asarray(white)

    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]

    # Compute f values
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200

    f = np.stack([fx, fy, fz], axis=-1)

    # Apply inverse nonlinear transform
    xyz_normalized = _lab_f_inv(f)

    # Denormalize by white point
    return xyz_normalized * white


def xy_to_XYZ(xy: NDArray[np.floating], Y: float = 1.0) -> NDArray[np.floating]:
    """
    Convert CIE xy chromaticity to XYZ tristimulus.

    Args:
        xy: Chromaticity coordinates [x, y], shape (2,) or (N, 2).
        Y: Luminance value (default 1.0).

    Returns:
        XYZ tristimulus values, shape (3,) or (N, 3).
    """
    xy = np.asarray(xy)
    x, y = xy[..., 0], xy[..., 1]

    X = (x / y) * Y
    Z = ((1 - x - y) / y) * Y

    return np.stack([X, np.full_like(X, Y), Z], axis=-1)


def _lab_f(t: NDArray[np.floating]) -> NDArray[np.floating]:
    """CIELab forward nonlinear function."""
    result = np.empty_like(t)
    mask = t > EPSILON
    result[mask] = np.cbrt(t[mask])
    result[~mask] = (KAPPA * t[~mask] + 16) / 116
    return result


def _lab_f_inv(f: NDArray[np.floating]) -> NDArray[np.floating]:
    """CIELab inverse nonlinear function."""
    result = np.empty_like(f)
    f3 = f ** 3
    mask = f3 > EPSILON
    result[mask] = f3[mask]
    result[~mask] = (116 * f[~mask] - 16) / KAPPA
    return result
