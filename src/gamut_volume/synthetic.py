"""
Synthetic reference gamut generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    pass


# Standard illuminant white points (CIE xy chromaticity)
D65_WHITE = np.array([0.31272, 0.32903])
D50_WHITE = np.array([0.34567, 0.35850])
DCI_WHITE = np.array([0.314, 0.351])
D60_WHITE = np.array([0.32168, 0.33767])

# Standard gamut primaries (CIE xy chromaticity)
SRGB_PRIMARIES = np.array([
    [0.6400, 0.3300],  # Red
    [0.3000, 0.6000],  # Green
    [0.1500, 0.0600],  # Blue
])

BT2020_PRIMARIES = np.array([
    [0.708, 0.292],   # Red
    [0.170, 0.797],   # Green
    [0.131, 0.046],   # Blue
])

DCI_P3_PRIMARIES = np.array([
    [0.680, 0.320],   # Red
    [0.265, 0.690],   # Green
    [0.150, 0.060],   # Blue
])


class SyntheticGamut:
    """
    A synthetic reference gamut defined by primaries, white point, and gamma.

    Synthetic gamuts are computed mathematically rather than from measurements,
    making them useful as reference standards for coverage calculations.
    """

    def __init__(
        self,
        primaries_xy: NDArray[np.floating],
        white_xy: NDArray[np.floating],
        gamma: float = 2.2,
    ) -> None:
        """
        Create a synthetic gamut from primaries and white point.

        Args:
            primaries_xy: CIE xy chromaticity of RGB primaries, shape (3, 2).
            white_xy: CIE xy chromaticity of white point, shape (2,).
            gamma: Display gamma (default 2.2 for sRGB-like response).
        """
        self.primaries_xy = np.asarray(primaries_xy)
        self.white_xy = np.asarray(white_xy)
        self.gamma = gamma

        self._gamut: "Gamut | None" = None

    @classmethod
    def srgb(cls) -> SyntheticGamut:
        """Create an sRGB reference gamut (D65, gamma 2.2)."""
        return cls(SRGB_PRIMARIES, D65_WHITE, gamma=2.2)

    @classmethod
    def bt2020(cls) -> SyntheticGamut:
        """Create a BT.2020 reference gamut (D65, gamma 2.4)."""
        return cls(BT2020_PRIMARIES, D65_WHITE, gamma=2.4)

    @classmethod
    def dci_p3(cls) -> SyntheticGamut:
        """Create a DCI-P3 reference gamut (DCI white, gamma 2.6)."""
        return cls(DCI_P3_PRIMARIES, DCI_WHITE, gamma=2.6)

    @classmethod
    def display_p3(cls) -> SyntheticGamut:
        """Create a Display P3 reference gamut (D65 white, gamma 2.2)."""
        return cls(DCI_P3_PRIMARIES, D65_WHITE, gamma=2.2)

    def _build_gamut(self) -> "Gamut":
        """Build the underlying Gamut object."""
        from gamut_volume.gamut import Gamut
        from gamut_volume.colorspace.adaptation import adapt_d65_to_d50
        from gamut_volume.colorspace.lab import xyz_to_lab
        from gamut_volume.geometry.tesselation import make_tesselation

        # Generate RGB cube tesselation
        triangles, rgb_surface = make_tesselation()

        # Convert RGB to XYZ using primaries and white point
        xyz_surface = self._rgb_to_xyz(rgb_surface)

        # Chromatic adaptation to D50
        xyz_d50 = adapt_d65_to_d50(xyz_surface, source_white=self.white_xy)

        # Convert to CIELab
        lab = xyz_to_lab(xyz_d50)

        return Gamut(lab, triangles)

    def _rgb_to_xyz(self, rgb: NDArray[np.floating]) -> NDArray[np.floating]:
        """
        Convert RGB values to XYZ using this gamut's primaries and white point.

        Args:
            rgb: Linear RGB values, shape (N, 3), range [0, 1].

        Returns:
            XYZ tristimulus values, shape (N, 3).
        """
        # Apply gamma to get linear RGB
        rgb_linear = np.power(rgb, self.gamma)

        # Build RGB to XYZ matrix from primaries and white point
        M = _build_rgb_to_xyz_matrix(self.primaries_xy, self.white_xy)

        # Transform
        return rgb_linear @ M.T

    @property
    def gamut(self) -> "Gamut":
        """Get the underlying Gamut object, building it if needed."""
        if self._gamut is None:
            self._gamut = self._build_gamut()
        return self._gamut

    def volume(self) -> float:
        """Calculate the gamut volume."""
        return self.gamut.volume()

    def intersect(self, other: "Gamut | SyntheticGamut") -> "Gamut":
        """Compute intersection with another gamut."""
        return self.gamut.intersect(other)

    def plot_surface(self, **kwargs) -> "Figure":
        """Create a 3D surface plot."""
        return self.gamut.plot_surface(**kwargs)

    def plot_rings(self, **kwargs) -> "Figure":
        """Create a 2D gamut rings plot."""
        return self.gamut.plot_rings(**kwargs)


def _build_rgb_to_xyz_matrix(
    primaries_xy: NDArray[np.floating],
    white_xy: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Build the 3x3 RGB to XYZ transformation matrix.

    Args:
        primaries_xy: CIE xy of primaries, shape (3, 2).
        white_xy: CIE xy of white point, shape (2,).

    Returns:
        3x3 transformation matrix.
    """
    from gamut_volume.colorspace.lab import xy_to_XYZ

    # Convert primaries from xy to XYZ (Y=1)
    primaries_XYZ = np.array([xy_to_XYZ(xy) for xy in primaries_xy])

    # Convert white point from xy to XYZ (Y=1)
    white_XYZ = xy_to_XYZ(white_xy)

    # Solve for scaling factors S such that S * primaries_XYZ = white_XYZ
    # This ensures RGB=[1,1,1] maps to the white point
    S = np.linalg.solve(primaries_XYZ.T, white_XYZ)

    # Build final matrix: each column is a scaled primary
    M = primaries_XYZ.T * S

    return M
