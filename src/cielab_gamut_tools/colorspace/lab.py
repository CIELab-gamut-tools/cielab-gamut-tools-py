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


# sRGB primaries → XYZ(D65) matrix (matches MATLAB lab2srgb.m)
_M_SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
# D65 white = column sums of the transposed matrix = row sums of _M_SRGB_TO_XYZ
_D65_WHITE_FROM_M = _M_SRGB_TO_XYZ.sum(axis=1)
_M_XYZ_TO_LINEAR_SRGB = np.linalg.inv(_M_SRGB_TO_XYZ)


def lab_to_srgb_display(lab: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Convert CIELab to sRGB [0, 255] for display use only.

    Matches MATLAB CIEtools/lab2srgb.m exactly: uses D65 reference white
    derived from the sRGB primaries matrix and simple 2.2 power gamma
    (not the piecewise IEC 61966 sRGB transfer function).

    Args:
        lab: CIELab values [L*, a*, b*], shape (N, 3) or (3,).

    Returns:
        sRGB values [0, 255] as float, same shape as input.
        Clipped and floor-rounded, matching MATLAB output.

    Note:
        This function is for computing display colours (e.g. band fills,
        primary arrow colours). Do not use for gamut measurement pipelines.
    """
    xyz = lab_to_xyz(lab, white=_D65_WHITE_FROM_M)
    linear = xyz @ _M_XYZ_TO_LINEAR_SRGB.T
    return np.floor(np.clip(linear, 0.0, 1.0) ** (1.0 / 2.2) * 255.0)


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
