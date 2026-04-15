"""
Main Gamut class for representing and analyzing color gamuts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from cielab_gamut_tools.synthetic import SyntheticGamut


class Gamut:
    """
    Represents a color gamut in CIELab space.

    A gamut is the range of colors that a device can produce. This class
    stores the gamut as a tesselated surface in CIELab coordinates and
    provides methods for volume calculation, intersection, and visualization.

    Attributes:
        lab: CIELab coordinates of the gamut surface points (N x 3 array).
        triangles: Triangle indices for the tesselated surface (M x 3 array).
    """

    def __init__(
        self,
        lab: NDArray[np.floating],
        triangles: NDArray[np.integer],
        *,
        rgb: NDArray[np.floating] | None = None,
        title: str | None = None,
    ) -> None:
        """
        Initialize a Gamut from CIELab coordinates and triangulation.

        Args:
            lab: CIELab coordinates of surface points, shape (N, 3).
            triangles: Triangle vertex indices, shape (M, 3).
            rgb: RGB coordinates of surface points, shape (N, 3), range [0, 1].
                 Aligned with ``lab``. Used for primary colour indicators.
            title: Human-readable gamut name shown in plot titles.

        Note:
            Most users should use the factory methods `from_cgats()` or
            `from_xyz()` rather than calling this constructor directly.
        """
        self.lab = lab
        self.triangles = triangles
        self.rgb = rgb
        self.title = title
        self._volume: float | None = None
        self._cylindrical_map: NDArray[np.floating] | None = None
        self._cylmap_counts: NDArray[np.integer] | None = None

    @classmethod
    def from_cgats(cls, path: str) -> Gamut:
        """
        Load a gamut from a CGATS.17 format file.

        Args:
            path: Path to the CGATS file containing RGB and XYZ measurements.

        Returns:
            A new Gamut instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid or missing required fields.
        """
        import os
        from cielab_gamut_tools.io.cgats import read_cgats

        rgb, xyz, metadata = read_cgats(path)
        title = metadata.get("title") or os.path.splitext(os.path.basename(path))[0]
        return cls.from_xyz(rgb, xyz, metadata=metadata, title=title)

    @classmethod
    def from_xyz(
        cls,
        rgb: NDArray[np.floating],
        xyz: NDArray[np.floating],
        *,
        metadata: dict | None = None,
        title: str | None = None,
    ) -> Gamut:
        """
        Create a gamut from RGB and XYZ measurement data.

        Args:
            rgb: RGB values, shape (N, 3), range [0, 1] or [0, 255].
            xyz: Corresponding XYZ tristimulus values, shape (N, 3).
            metadata: Optional metadata dict (e.g., from CGATS file).
            title: Human-readable gamut name shown in plot titles.

        Returns:
            A new Gamut instance.
        """
        from cielab_gamut_tools.colorspace.adaptation import adapt_d65_to_d50
        from cielab_gamut_tools.colorspace.lab import xyz_to_lab
        from cielab_gamut_tools.geometry.tesselation import make_tesselation

        # Normalize RGB to [0, 1] if needed
        if rgb.max() > 1.0:
            rgb = rgb / 255.0

        # Create surface tesselation
        triangles, rgb_surface = make_tesselation()

        # Interpolate XYZ for tesselation points
        xyz_surface = _interpolate_xyz(rgb, xyz, rgb_surface)

        # Chromatic adaptation D65 -> D50
        xyz_d50 = adapt_d65_to_d50(xyz_surface)

        # Convert to CIELab
        lab = xyz_to_lab(xyz_d50)

        return cls(lab, triangles, rgb=rgb_surface, title=title)

    def volume(self) -> float:
        """
        Calculate the gamut volume in CIELab cubic units.

        The volume is computed using cylindrical integration in CIELab space,
        discretized into 100 L* levels and 360 hue angles.

        Returns:
            The gamut volume.
        """
        if self._volume is None:
            from cielab_gamut_tools.geometry.volume import (
                get_cylindrical_map,
                _integrate_cylmap,
            )

            cylmap, counts = get_cylindrical_map(self)
            self._volume = _integrate_cylmap(cylmap, counts, 100, 360)
        return self._volume

    def intersect(self, other: Gamut | SyntheticGamut) -> Gamut:
        """
        Compute the intersection of this gamut with another.

        Args:
            other: The gamut to intersect with.

        Returns:
            A new Gamut representing the intersection volume.
        """
        from cielab_gamut_tools.geometry.volume import intersect_gamuts

        return intersect_gamuts(self, other)

    def plot_surface(
        self,
        ax: Axes | None = None,
        alpha: float = 0.8,
    ) -> Figure:
        """
        Create a 3D surface plot of the gamut.

        Args:
            ax: Optional matplotlib 3D axes to plot on.
            alpha: Surface transparency (0-1).

        Returns:
            The matplotlib Figure containing the plot.
        """
        from cielab_gamut_tools.plotting.surface import plot_surface

        return plot_surface(self, ax=ax, alpha=alpha)

    def plot_rings(
        self,
        reference: Gamut | SyntheticGamut | None = None,
        reference2: Gamut | SyntheticGamut | None = None,
        **kwargs,
    ) -> Figure:
        """
        Create a 2D gamut rings plot in the a*-b* plane.

        Each ring's radius encodes the cumulative gamut volume up to that L*
        level, so the area enclosed equals the cumulative volume.

        Args:
            reference: Optional reference gamut.
            reference2: Optional second reference gamut (outer ring only).
            **kwargs: All other keyword arguments are forwarded to
                ``plot_rings()`` — see that function for the full list.

        Returns:
            The matplotlib Figure containing the plot.
        """
        from cielab_gamut_tools.plotting.rings import plot_rings

        return plot_rings(self, reference=reference, reference2=reference2, **kwargs)


def _interpolate_xyz(
    rgb_measured: NDArray[np.floating],
    xyz_measured: NDArray[np.floating],
    rgb_query: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Interpolate XYZ values for query RGB points based on measurements.

    Uses the measured RGB->XYZ mapping to estimate XYZ values at arbitrary
    RGB coordinates on the gamut surface.

    Args:
        rgb_measured: Measured RGB values, shape (N, 3), range [0, 1].
        xyz_measured: Corresponding XYZ values, shape (N, 3).
        rgb_query: RGB coordinates to interpolate, shape (M, 3).

    Returns:
        Interpolated XYZ values, shape (M, 3).
    """
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

    # Build linear interpolator from measured data
    linear_interp = LinearNDInterpolator(rgb_measured, xyz_measured)

    # Interpolate XYZ at query points
    xyz_query = linear_interp(rgb_query)

    # LinearNDInterpolator returns NaN for points outside the convex hull
    # of the input data. Use nearest-neighbor for those points.
    nan_mask = np.isnan(xyz_query).any(axis=1)

    if np.any(nan_mask):
        nearest_interp = NearestNDInterpolator(rgb_measured, xyz_measured)
        xyz_query[nan_mask] = nearest_interp(rgb_query[nan_mask])

    return xyz_query
