"""
3D gamut surface visualization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from gamut_volume.gamut import Gamut


def plot_surface(
    gamut: "Gamut",
    ax: "Axes | None" = None,
    alpha: float = 0.8,
    show_axes: bool = True,
) -> "Figure":
    """
    Create a 3D surface plot of the gamut in CIELab space.

    The surface is colored using the approximate sRGB color at each point.

    Args:
        gamut: The gamut to plot.
        ax: Optional matplotlib 3D axes. If None, a new figure is created.
        alpha: Surface transparency (0=transparent, 1=opaque).
        show_axes: Whether to show axis labels and grid.

    Returns:
        The matplotlib Figure containing the plot.
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    from gamut_volume.colorspace.lab import lab_to_xyz
    from gamut_volume.colorspace.srgb import srgb_gamma_encode

    # Create figure if needed
    if ax is None:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    # Get triangle vertices
    lab = gamut.lab
    triangles = gamut.triangles

    # Convert Lab to approximate RGB for coloring
    xyz = lab_to_xyz(lab)
    # Simple XYZ to RGB (approximate, using sRGB matrix)
    M_xyz_to_rgb = np.array([
        [ 3.2406, -1.5372, -0.4986],
        [-0.9689,  1.8758,  0.0415],
        [ 0.0557, -0.2040,  1.0570],
    ])
    rgb_linear = xyz @ M_xyz_to_rgb.T
    rgb_linear = np.clip(rgb_linear, 0, 1)
    rgb = srgb_gamma_encode(rgb_linear)

    # Build polygon collection
    verts = []
    colors = []

    for tri in triangles:
        triangle_verts = lab[tri]
        # Use a*, b*, L* as x, y, z
        verts.append(triangle_verts[:, [1, 2, 0]])  # a*, b*, L*

        # Average color of triangle vertices
        tri_color = np.mean(rgb[tri], axis=0)
        colors.append(tri_color)

    poly = Poly3DCollection(verts, alpha=alpha)
    poly.set_facecolor(colors)
    poly.set_edgecolor("none")
    ax.add_collection3d(poly)

    # Set axis properties
    if show_axes:
        ax.set_xlabel("a*")
        ax.set_ylabel("b*")
        ax.set_zlabel("L*")

    # Set axis limits
    ax.set_xlim(-128, 128)
    ax.set_ylim(-128, 128)
    ax.set_zlim(0, 100)

    return fig
