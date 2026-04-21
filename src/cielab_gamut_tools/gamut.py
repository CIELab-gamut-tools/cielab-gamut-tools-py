"""
Main Gamut class for representing and analyzing color gamuts.
"""

from __future__ import annotations

import warnings
from pathlib import Path
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
        rgb: RGB coordinates of the surface points (N x 3, range [0, 1]),
             or None if not available.
        xyz: XYZ tristimulus values of the surface points in the source
             colorspace (D65 for most displays), shape (N x 3), or None.
             Retained from construction for export and future analyses.
        title: Human-readable gamut name.
    """

    def __init__(
        self,
        lab: NDArray[np.floating],
        triangles: NDArray[np.integer],
        *,
        rgb: NDArray[np.floating] | None = None,
        xyz: NDArray[np.floating] | None = None,
        title: str | None = None,
    ) -> None:
        """
        Initialize a Gamut from CIELab coordinates and triangulation.

        Args:
            lab: CIELab coordinates of surface points, shape (N, 3).
            triangles: Triangle vertex indices, shape (M, 3).
            rgb: RGB coordinates of surface points, shape (N, 3), range [0, 1].
                 Aligned with ``lab``. Used for topology reconstruction and
                 primary colour indicators.
            xyz: XYZ tristimulus values of surface points in source colorspace
                 (typically D65), shape (N, 3). Retained for export and future
                 analyses in chromaticity or XYZ space.
            title: Human-readable gamut name shown in plot titles.

        Note:
            Most users should use the factory methods `from_cgats()` or
            `from_xyz()` rather than calling this constructor directly.
        """
        self.lab = lab
        self.triangles = triangles
        self.rgb = rgb
        self.xyz = xyz
        self.title = title
        self._volume: float | None = None
        self._cylindrical_map: NDArray[np.floating] | None = None
        self._cylmap_counts: NDArray[np.integer] | None = None

    @classmethod
    def from_cgats(cls, path: str | Path) -> Gamut:
        """
        Load a gamut from a CGATS.17 format file.

        Handles both CGE_MEASUREMENT files (RGB + XYZ) and CGE_ENVELOPE
        files (RGB + LAB). When XYZ is present it takes priority and the
        Bradford D65→D50 adaptation and Lab conversion are applied. When
        only LAB is present the stored values are used directly.

        RGB values must be present in the file to reconstruct the gamut
        topology; a file without RGB is rejected with a warning.

        Args:
            path: Path to the CGATS file.

        Returns:
            A new Gamut instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid, required fields are
                missing, or RGB data is absent.
        """
        from cielab_gamut_tools.io.cgats import read_cgats

        path = Path(path)
        data = read_cgats(path)
        title = data.metadata.get("title") or path.stem

        if data.xyz is not None:
            if data.rgb is None:
                warnings.warn(
                    f"{path.name}: XYZ data found without RGB values. "
                    "RGB is required to reconstruct the gamut topology and is "
                    "mandatory for standards-compliant analysis.",
                    UserWarning,
                    stacklevel=2,
                )
                raise ValueError(
                    "CGATS file must contain RGB values alongside XYZ data"
                )
            return cls.from_xyz(data.rgb, data.xyz, metadata=data.metadata, title=title)

        if data.lab is not None:
            if data.rgb is None:
                warnings.warn(
                    f"{path.name}: LAB data found without RGB values. "
                    "RGB is required to reconstruct the gamut topology and is "
                    "mandatory for standards-compliant analysis.",
                    UserWarning,
                    stacklevel=2,
                )
                raise ValueError(
                    "CGATS file must contain RGB values alongside LAB data"
                )
            return cls._from_lab_and_rgb(
                data.rgb, data.lab, metadata=data.metadata, title=title
            )

        raise ValueError(
            f"{path.name}: CGATS file must contain XYZ or LAB colorspace data"
        )

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

        The XYZ values are assumed to be in D65 colorspace (typical for
        emissive displays). Bradford chromatic adaptation to D50 is applied
        before converting to CIELab.

        Args:
            rgb: RGB values, shape (N, 3), range [0, 1] or [0, 255].
            xyz: Corresponding XYZ tristimulus values, shape (N, 3).
            metadata: Optional metadata dict (e.g., from CGATS file).
            title: Human-readable gamut name shown in plot titles.

        Returns:
            A new Gamut instance. ``gamut.xyz`` holds the D65 surface XYZ
            values (interpolated to tesselation points) for later export.
        """
        from cielab_gamut_tools.colorspace.adaptation import adapt_d65_to_d50
        from cielab_gamut_tools.colorspace.lab import xyz_to_lab
        from cielab_gamut_tools.geometry.tesselation import make_tesselation

        # Normalize RGB to [0, 1] if needed
        if rgb.max() > 1.0:
            rgb = rgb / 255.0

        # Create surface tesselation
        triangles, rgb_surface = make_tesselation()

        # Expand 602 measured XYZ values to the 726 tessellation vertices
        xyz_surface = _expand_colordata_to_tesselation(rgb, xyz, rgb_surface)

        # Chromatic adaptation D65 -> D50
        xyz_d50 = adapt_d65_to_d50(xyz_surface)

        # Convert to CIELab
        lab = xyz_to_lab(xyz_d50)

        return cls(lab, triangles, rgb=rgb_surface, xyz=xyz_surface, title=title)

    @classmethod
    def _from_lab_and_rgb(
        cls,
        rgb: NDArray[np.floating],
        lab: NDArray[np.floating],
        *,
        metadata: dict | None = None,
        title: str | None = None,
    ) -> Gamut:
        """
        Create a gamut directly from RGB and CIELab surface data.

        Used when loading a CGE_ENVELOPE file that already contains D50
        Lab coordinates. The standard tesselation topology is reconstructed
        from the RGB values; no colorspace conversion is applied.

        Args:
            rgb: RGB values, shape (N, 3), range [0, 1] or [0, 255].
            lab: CIELab values, shape (N, 3).
            metadata: Optional metadata dict.
            title: Human-readable gamut name.

        Returns:
            A new Gamut instance. ``gamut.xyz`` is None (not available from
            a LAB-only source file).
        """
        from cielab_gamut_tools.geometry.tesselation import make_tesselation

        if rgb.max() > 1.0:
            rgb = rgb / 255.0

        triangles, rgb_surface = make_tesselation()
        lab_surface = _expand_colordata_to_tesselation(rgb, lab, rgb_surface)

        return cls(lab_surface, triangles, rgb=rgb_surface, xyz=None, title=title)

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

    def compute_rings(
        self,
        l_steps: int = 100,
        h_steps: int = 360,
    ) -> NDArray[np.floating]:
        """
        Compute the C*_RSS gamut ring radii at each (L*, hue) grid point.

        The ring radius at L* level *l* and hue *h* satisfies:

        .. code-block:: none

            C*_RSS(l, h) = sqrt(2 × cumsum_l(V(l, h)) / Δh)

        where the cumulative sum is taken over L* from 0 upward. This is the
        normative ring metric in IDMS v1.3, IEC 62977-3-5, and IEC 62906-6-1.

        Args:
            l_steps: Number of L* bins (default 100).
            h_steps: Number of hue bins (default 360).

        Returns:
            Array of shape ``(l_steps, h_steps)`` of C*_RSS values. Row 0
            is the cumulative ring at the first L* bin; the last row is the
            outer ring at ~L*=100.
        """
        from cielab_gamut_tools.geometry.volume import compute_cylindrical_rings

        return compute_cylindrical_rings(self, l_steps, h_steps)

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

    def to_cgats(
        self,
        path: str | Path,
        *,
        mode: str = "envelope",
        description: str | None = None,
        created: str | None = None,
    ) -> None:
        """
        Write gamut data to a CGATS.17 Format 2 file.

        Args:
            path: Output file path.
            mode: Controls which data columns are written and which
                ``IDMS_FILE_TYPE`` header is used:

                - ``"envelope"`` *(default)*: RGB + LAB,
                  ``IDMS_FILE_TYPE = CGE_ENVELOPE``.
                - ``"measurement"``: RGB + XYZ,
                  ``IDMS_FILE_TYPE = CGE_MEASUREMENT``.
                - ``"all"``: RGB + XYZ + LAB, no ``IDMS_FILE_TYPE`` header.

            description: Free-text description line. Defaults to
                ``self.title`` when not supplied.
            created: Creation date string written as ``CREATED\\t<value>``.

        Raises:
            ValueError: If *mode* is ``"measurement"`` or ``"all"`` and
                ``self.xyz`` is None.
            ValueError: If *mode* is unrecognised.

        Note:
            RGB values are scaled from the internal [0, 1] range to [0, 255]
            on output to match the IDMS reference files.
        """
        from cielab_gamut_tools.io.cgats import write_cgats

        valid_modes = ("envelope", "measurement", "all")
        if mode not in valid_modes:
            raise ValueError(
                f"mode must be one of {valid_modes!r}, got {mode!r}"
            )

        if mode in ("measurement", "all") and self.xyz is None:
            raise ValueError(
                f"to_cgats(mode={mode!r}) requires XYZ data, but self.xyz is None. "
                "XYZ is retained when the Gamut was created via from_xyz() or "
                "from_cgats() with an XYZ-containing file."
            )

        # Scale RGB from internal [0, 1] to [0, 255] for CGATS output
        rgb_out: NDArray[np.floating] | None = None
        if self.rgb is not None:
            rgb_out = np.round(self.rgb * 255).astype(np.float64)

        # Deduplicate tessellation vertices before writing.
        #
        # make_tesselation() deliberately produces 726 vertices for m=11 (the
        # standard 11-point grid): edge and corner vertices are replicated across
        # adjacent faces so the triangulation is geometrically complete. For CGATS
        # output we must remove these duplicates and write only the 602 unique
        # surface points, exactly matching MATLAB's:
        #
        #   [~, rgb] = make_tesselation(V);
        #   rgb = unique(rgb, 'rows');          % in make_rgb_signals.m
        #
        # This matters most for mode="measurement": duplicate RGB values would
        # send the metrologist the same signal twice, wasting measurement time.
        # Envelope and all modes are deduplicated for the same reason — a
        # standards-compliant CGE_ENVELOPE file has exactly n unique rows.
        if rgb_out is not None:
            _, unique_idx = np.unique(rgb_out, axis=0, return_index=True)
            # unique_idx is already in the lexicographic sort order that
            # np.unique uses, matching MATLAB's unique(rgb,'rows') ordering.
            rgb_out = rgb_out[unique_idx]
            lab_out = self.lab[unique_idx] if mode in ("envelope", "all") else None
            xyz_out = (
                self.xyz[unique_idx]
                if mode in ("measurement", "all") and self.xyz is not None
                else None
            )
        else:
            lab_out = self.lab if mode in ("envelope", "all") else None
            xyz_out = (
                self.xyz
                if mode in ("measurement", "all") and self.xyz is not None
                else None
            )

        file_type: str | None = {
            "envelope": "CGE_ENVELOPE",
            "measurement": "CGE_MEASUREMENT",
            "all": None,
        }[mode]

        write_cgats(
            path,
            rgb=rgb_out,
            xyz=xyz_out,
            lab=lab_out,
            description=description if description is not None else self.title,
            created=created,
            file_type=file_type,
        )

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


def _expand_colordata_to_tesselation(
    rgb_measured: NDArray[np.floating],
    colordata_measured: NDArray[np.floating],
    rgb_tesselation: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Expand N measured colordata values to the full 726-vertex tessellation.

    This matches the role of MATLAB's ``map_rows.m``: for each tessellation
    vertex, find the corresponding measured point and copy its colordata.

    **Lookup strategy — integer space at scale 255**

    CGATS files store RGB as integers in [0, 255].  When read back and
    normalised to [0, 1] a tessellation value such as 0.1 becomes 26/255 ≈
    0.10196, which no longer matches the linspace value 0.1 in float space.
    Rounding both sides to the nearest integer at scale 255 restores the
    exact match:  ``round(0.1 × 255) = round(0.10196 × 255) = 26``.

    For any query vertex that cannot be matched exactly (e.g. genuinely
    non-grid measurement data), the function falls back to scattered linear
    interpolation so the general case is still handled gracefully.

    Args:
        rgb_measured: Measured RGB values, shape (N, 3), normalised [0, 1].
        colordata_measured: Corresponding color values (XYZ or Lab), shape (N, 3).
        rgb_tesselation: RGB coordinates of the 726 tessellation vertices,
            shape (726, 3), normalised [0, 1].

    Returns:
        Color values at all tessellation vertices, shape (726, 3).
    """
    # Build a lookup from integer RGB tuple → row index in the measured data.
    # Scaling by 255 and rounding reverses the CGATS integer→float conversion.
    rgb_m_int = np.round(rgb_measured * 255).astype(np.int32)
    lookup: dict[tuple[int, int, int], int] = {
        (int(r[0]), int(r[1]), int(r[2])): i for i, r in enumerate(rgb_m_int)
    }

    rgb_t_int = np.round(rgb_tesselation * 255).astype(np.int32)
    result = np.empty((len(rgb_tesselation), colordata_measured.shape[1]))
    fallback_indices: list[int] = []

    for i, t in enumerate(rgb_t_int):
        idx = lookup.get((int(t[0]), int(t[1]), int(t[2])))
        if idx is not None:
            result[i] = colordata_measured[idx]
        else:
            fallback_indices.append(i)
            result[i] = np.nan

    if fallback_indices:
        # Genuine non-grid data: fall back to scattered linear interpolation.
        from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

        fb = np.array(fallback_indices)
        linear = LinearNDInterpolator(rgb_measured, colordata_measured)
        interp_vals = linear(rgb_tesselation[fb])

        nan_mask = np.isnan(interp_vals).any(axis=1)
        if nan_mask.any():
            nearest = NearestNDInterpolator(rgb_measured, colordata_measured)
            interp_vals[nan_mask] = nearest(rgb_tesselation[fb][nan_mask])

        result[fb] = interp_vals

    return result


# Legacy alias kept for any external callers
_interpolate_colordata = _expand_colordata_to_tesselation
_interpolate_xyz = _expand_colordata_to_tesselation
