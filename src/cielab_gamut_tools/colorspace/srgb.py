"""
sRGB color space utilities.

Provides gamma encoding/decoding functions for sRGB as defined in
IEC 61966-2-1:1999.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def srgb_gamma_encode(linear: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Apply sRGB gamma encoding (linear to sRGB).

    The sRGB transfer function is piecewise:
    - Linear portion for small values (< 0.0031308)
    - Power function with gamma ≈ 2.4 for larger values

    Args:
        linear: Linear RGB values in range [0, 1].

    Returns:
        sRGB-encoded values in range [0, 1].
    """
    linear = np.asarray(linear)
    result = np.empty_like(linear)

    mask = linear <= 0.0031308
    result[mask] = 12.92 * linear[mask]
    result[~mask] = 1.055 * np.power(linear[~mask], 1 / 2.4) - 0.055

    return result


def srgb_gamma_decode(encoded: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Apply sRGB gamma decoding (sRGB to linear).

    Args:
        encoded: sRGB-encoded values in range [0, 1].

    Returns:
        Linear RGB values in range [0, 1].
    """
    encoded = np.asarray(encoded)
    result = np.empty_like(encoded)

    mask = encoded <= 0.04045
    result[mask] = encoded[mask] / 12.92
    result[~mask] = np.power((encoded[~mask] + 0.055) / 1.055, 2.4)

    return result
