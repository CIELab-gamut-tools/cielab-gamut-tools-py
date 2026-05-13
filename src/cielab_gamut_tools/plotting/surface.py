"""
3D gamut surface visualization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from cielab_gamut_tools.gamut import Gamut


def plot_surface(
    gamut: "Gamut",
    ax: "Axes | None" = None,
    alpha: float = 0.8,
    wireframe: bool = False,
    color: str | None = None,
    chroma: float | None = None,
    lightness: float | None = None,
    linewidth: float | None = None,
    show_axes: bool = True,
    figsize: tuple[float, float] = (10.0, 8.0),
    title: str | None = None,
    xlim: tuple[float, float] = (-128.0, 128.0),
    ylim: tuple[float, float] = (-128.0, 128.0),
    zlim: tuple[float, float] = (0.0, 100.0),
    elev: float | None = None,
    azim: float | None = None,
) -> "tuple[Figure, Axes]":
    """
    Create a 3D surface plot of the gamut in CIELab space.

    The surface is colored using the approximate sRGB color at each point.

    Args:
        gamut: The gamut to plot.
        ax: Optional matplotlib 3D axes. If ``None``, a new figure is created.
        alpha: For solid: face transparency (0=transparent, 1=opaque). For
            wireframe: edge opacity.
        wireframe: If ``True``, render edges only (no filled faces). The
            ``color``, ``chroma``, ``lightness``, and ``linewidth`` parameters
            only apply when this is ``True``.
        color: Fixed matplotlib color string for wireframe edges (e.g.
            ``"#808080"``, ``"grey"``). Mutually exclusive with ``chroma`` and
            ``lightness``.
        chroma: Scale factor applied to the a* and b* components of the
            per-face Lab colour before converting to sRGB edge colours.
            ``0`` gives neutral grey, ``1`` (default) keeps full colour.
            Mutually exclusive with ``color``.
        lightness: Override the L* component of the per-face Lab colour before
            converting to sRGB edge colours (0–100). Can be combined with
            ``chroma``. Mutually exclusive with ``color``.
        linewidth: Edge line width in points. ``None`` uses the matplotlib
            default.
        show_axes: Whether to show axis labels and grid.
        figsize: Figure size in inches as ``(width, height)`` (default
            ``(10, 8)``). Ignored when ``ax`` is supplied.
        title: Axes title. ``None`` (default) produces no title.
        xlim: a* axis limits (default ``(-128, 128)``).
        ylim: b* axis limits (default ``(-128, 128)``).
        zlim: L* axis limits (default ``(0, 100)``).
        elev: 3D view elevation angle in degrees. ``None`` uses matplotlib
            default (~30°).
        azim: 3D view azimuth angle in degrees. ``None`` uses matplotlib
            default (~-60°).

    Returns:
        A ``(Figure, Axes)`` tuple for the plot.
    """
    if color is not None and (chroma is not None or lightness is not None):
        raise ValueError("color is mutually exclusive with chroma and lightness")

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    from cielab_gamut_tools.colorspace.lab import lab_to_xyz
    from cielab_gamut_tools.colorspace.srgb import srgb_gamma_encode

    if ax is None:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.get_figure()

    lab = gamut.lab
    triangles = gamut.triangles

    # XYZ → sRGB matrix (approximate, D65 adapted)
    M_xyz_to_rgb = np.array([
        [ 3.2406, -1.5372, -0.4986],
        [-0.9689,  1.8758,  0.0415],
        [ 0.0557, -0.2040,  1.0570],
    ])

    # Per-vertex sRGB from unmodified Lab (solid face colours)
    xyz = lab_to_xyz(lab)
    rgb_linear = xyz @ M_xyz_to_rgb.T
    rgb_linear = np.clip(rgb_linear, 0, 1)
    rgb = srgb_gamma_encode(rgb_linear)

    verts: list = []
    face_rgbs: list[np.ndarray] = []
    for tri in triangles:
        verts.append(lab[tri][:, [1, 2, 0]])  # a*, b*, L*
        face_rgbs.append(np.mean(rgb[tri], axis=0))

    poly = Poly3DCollection(verts)

    if wireframe:
        if color is not None:
            import matplotlib.colors as mcolors
            r, g, b = mcolors.to_rgb(color)
            edge_colors: list = [(r, g, b, alpha)] * len(verts)
        elif chroma is not None or lightness is not None:
            # Apply chroma/lightness modifications in Lab before converting
            lab_e = lab.copy()
            if lightness is not None:
                lab_e[:, 0] = lightness
            if chroma is not None:
                lab_e[:, 1] *= chroma
                lab_e[:, 2] *= chroma
            xyz_e = lab_to_xyz(lab_e)
            rgb_lin_e = xyz_e @ M_xyz_to_rgb.T
            rgb_lin_e = np.clip(rgb_lin_e, 0, 1)
            rgb_e = srgb_gamma_encode(rgb_lin_e)
            edge_colors = [(*np.mean(rgb_e[tri], axis=0), alpha) for tri in triangles]
        else:
            edge_colors = [(*fc, alpha) for fc in face_rgbs]

        poly.set_facecolor([(0.0, 0.0, 0.0, 0.0)] * len(verts))
        poly.set_edgecolor(edge_colors)
        if linewidth is not None:
            poly.set_linewidth(linewidth)
    else:
        poly.set_facecolor(face_rgbs)
        poly.set_edgecolor("none")
        poly.set_alpha(alpha)

    ax.add_collection3d(poly)

    if show_axes:
        ax.set_xlabel("a*")
        ax.set_ylabel("b*")
        ax.set_zlabel("L*")

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_zlim(*zlim)

    if title is not None:
        ax.set_title(title)

    if elev is not None or azim is not None:
        ax.view_init(elev=elev, azim=azim)

    return fig, ax
