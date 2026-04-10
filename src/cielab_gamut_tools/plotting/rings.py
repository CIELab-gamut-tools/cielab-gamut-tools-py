"""
2D gamut rings visualization.

Each ring corresponds to an L* level. The radius at each hue angle is
computed so that the area enclosed by the ring equals the cumulative gamut
volume up to that L* level. The plot is in Cartesian (a*, b*) coordinates.

Algorithm matches calcGamutRings.m / PlotRings.m from gamut-volume-m (MATLAB
reference implementation for IEC/ICDM standards).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from cielab_gamut_tools.gamut import Gamut


def plot_rings(
    gamut: "Gamut",
    reference: "Gamut | None" = None,
    l_rings: list[float] | None = None,
    ax: "Axes | None" = None,
) -> "Figure":
    """
    Create a 2D gamut rings plot in the a*-b* plane.

    Each ring corresponds to an L* lightness level. The radius at each hue
    angle encodes the cumulative gamut volume up to that L* level, such that
    the area enclosed by the ring equals the cumulative volume. This matches
    the MATLAB PlotRings/calcGamutRings algorithm.

    Args:
        gamut: The gamut to plot.
        reference: Optional reference gamut — only the outer (L*=100) ring is
                   shown, as a dashed line.
        l_rings: Inner ring L* values (default: 10, 20, ..., 90). The outer
                 ring at L*=100 is always included.
        ax: Optional matplotlib Cartesian axes. If None, a new figure is
            created.

    Returns:
        The matplotlib Figure containing the plot.
    """
    import matplotlib.pyplot as plt

    if l_rings is None:
        l_rings = list(np.arange(10, 100, 10))  # 10:10:90

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.get_figure()

    ax.set_aspect("equal")
    ax.set_box_aspect(1)
    ax.axhline(0, color="lightgray", linewidth=0.5, zorder=0)
    ax.axvline(0, color="lightgray", linewidth=0.5, zorder=0)

    # Compute ring coordinates for the test gamut.
    # rows: [L*=0, l_rings..., L*=100]; skip row 0 (point at origin)
    x, y, vol = _calc_gamut_rings(gamut, l_rings)
    for i in range(1, x.shape[0]):
        xi = np.append(x[i], x[i, 0])
        yi = np.append(y[i], y[i, 0])
        ax.plot(xi, yi, "k-", linewidth=1.0)

    # Reference gamut: only the outer (L*=100) ring, dashed
    if reference is not None:
        if hasattr(reference, "gamut"):
            reference = reference.gamut
        ref_x, ref_y, _ = _calc_gamut_rings(reference, [])
        xi = np.append(ref_x[-1], ref_x[-1, 0])
        yi = np.append(ref_y[-1], ref_y[-1, 0])
        ax.plot(xi, yi, "--k", linewidth=1.0)

    # L* ring labels — default indices 0 and 4 (L*=10 and L*=50), matching
    # MATLAB's LLabelIndices=[1,5] (1-indexed)
    all_l = list(l_rings) + [100]
    for li in [0, 4]:
        if li < len(all_l):
            row = li + 1  # +1 to skip L*=0 row
            col = int(x.shape[1] * 15 // 16)
            ax.text(
                x[row, col], y[row, col],
                f"L*={all_l[li]:.0f}",
                fontsize=9, ha="center", va="center",
            )

    # Centre mark
    ax.plot(0, 0, "+k", markersize=20, markeredgewidth=1.5)

    ax.set_xlabel("a*")
    ax.set_ylabel("b*")
    ax.set_title(f"CIELab gamut rings\nVolume = {vol:.0f}")

    plt.tight_layout()
    return fig


def _calc_gamut_rings(
    gamut: "Gamut",
    l_rings: list[float],
    l_steps: int = 100,
    h_steps: int = 360,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Calculate ring x, y coordinates from the gamut cylindrical map.

    Matches calcGamutRings.m from gamut-volume-m. For each hue angle, the
    ring radius at a given L* level is chosen so that:
        area = sum_h(r² * dH / 2) = cumulative gamut volume up to L*

    Args:
        gamut: Gamut object (may have pre-computed _cylindrical_map).
        l_rings: Inner L* values for rings (without 0 or 100).
        l_steps: Number of L* bins (default 100).
        h_steps: Number of hue bins (default 360).

    Returns:
        x: (len(l_rings)+2, h_steps) — rows for L* = [0, l_rings..., 100]
        y: same shape
        vol: total gamut volume
    """
    from cielab_gamut_tools.geometry.volume import get_cylindrical_map

    # get_cylindrical_map handles building and caching automatically
    cylmap, counts = get_cylindrical_map(gamut, l_steps, h_steps)
    l_steps = cylmap.shape[0]
    h_steps = cylmap.shape[1]

    dH = 2 * np.pi / h_steps
    dL = 100.0 / l_steps

    # Volume contribution per (L*, hue) cell: sum(sign * t² * dL * dH / 2)
    # cylmap shape: (l_steps, h_steps, _MAX_K, 2); counts: (l_steps, h_steps)
    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]  # (l_steps, h_steps, _MAX_K)
    volmap = (
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask, axis=2)
        * dL * dH / 2
    )  # (l_steps, h_steps)

    # Cumulative volume over L* (from dark L*=0 toward light L*=100)
    cumvol = np.cumsum(volmap, axis=0)  # (l_steps, h_steps)

    # Squared radius such that area of ring = cumulative volume:
    #   sum_h(r² * dH / 2) = cumvol  →  r² = 2 * cumvol / dH
    r2_full = 2.0 * cumvol / dH  # (l_steps, h_steps)

    # L* grid for interpolation: [0, dL, 2*dL, ..., 100] (l_steps+1 values)
    L_grid = np.linspace(0.0, 100.0, l_steps + 1)

    # r² at each grid point: row 0 = L*=0 (zero everywhere), rows 1..l_steps = r2_full
    r2_grid = np.vstack([np.zeros((1, h_steps)), r2_full])  # (l_steps+1, h_steps)

    # Query L* values: [0, l_rings..., 100]
    L_query = np.concatenate([[0.0], l_rings, [100.0]])

    # Vectorised linear interpolation along L* for all hues at once
    idx = np.searchsorted(L_grid, L_query, side="right")
    idx = np.clip(idx, 1, len(L_grid) - 1)
    frac = (L_query - L_grid[idx - 1]) / (L_grid[idx] - L_grid[idx - 1])
    frac = np.clip(frac, 0.0, 1.0)  # (n_query,)

    r2_lo = r2_grid[idx - 1, :]     # (n_query, h_steps)
    r2_hi = r2_grid[idx, :]
    r2 = r2_lo + frac[:, np.newaxis] * (r2_hi - r2_lo)  # (n_query, h_steps)

    r = np.sqrt(np.maximum(r2, 0.0))

    # Unit direction vectors for each hue bin midpoint.
    # Convention (matching MATLAB): sin→a* axis, cos→b* axis
    midH = np.arange(dH / 2, 2 * np.pi, dH)  # (h_steps,)
    ux = np.sin(midH)
    uy = np.cos(midH)

    x = r * ux  # (n_query, h_steps)
    y = r * uy

    return x, y, float(np.sum(volmap))
