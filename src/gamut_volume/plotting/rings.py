"""
2D gamut rings visualization.

Shows gamut boundaries at different L* (lightness) levels as polar plots,
which is useful for comparing gamut coverage at different lightness values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from gamut_volume.gamut import Gamut


def plot_rings(
    gamut: "Gamut",
    reference: "Gamut | None" = None,
    l_values: list[float] | None = None,
    ax: "Axes | None" = None,
    show_legend: bool = True,
) -> "Figure":
    """
    Create a 2D polar plot showing gamut boundaries at different L* levels.

    Args:
        gamut: The gamut to plot.
        reference: Optional reference gamut to overlay (e.g., sRGB).
        l_values: L* values for rings (default [25, 50, 75]).
        ax: Optional matplotlib polar axes. If None, a new figure is created.
        show_legend: Whether to show the legend.

    Returns:
        The matplotlib Figure containing the plot.
    """
    import matplotlib.pyplot as plt

    if l_values is None:
        l_values = [25.0, 50.0, 75.0]

    # Create figure if needed
    if ax is None:
        fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))
    else:
        fig = ax.get_figure()

    # Colors for different L* values
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(l_values)))

    # Plot gamut rings
    for l_val, color in zip(l_values, colors):
        h, c = _extract_ring(gamut, l_val)
        if len(h) > 0:
            # Close the ring
            h = np.append(h, h[0])
            c = np.append(c, c[0])
            ax.plot(h, c, color=color, linewidth=2, label=f"L*={l_val:.0f}")

    # Plot reference rings if provided
    if reference is not None:
        # Get underlying Gamut if SyntheticGamut
        if hasattr(reference, "gamut"):
            reference = reference.gamut

        for l_val, color in zip(l_values, colors):
            h, c = _extract_ring(reference, l_val)
            if len(h) > 0:
                h = np.append(h, h[0])
                c = np.append(c, c[0])
                ax.plot(h, c, color=color, linewidth=1, linestyle="--", alpha=0.7)

    # Configure axes
    ax.set_theta_zero_location("E")  # 0° at right (red)
    ax.set_theta_direction(1)  # Counter-clockwise
    ax.set_rlabel_position(45)
    ax.set_ylabel("Chroma (C*)")

    if show_legend:
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    return fig


def _extract_ring(
    gamut: "Gamut",
    l_target: float,
    h_steps: int = 360,
    l_tolerance: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract the gamut boundary at a specific L* value.

    Args:
        gamut: The gamut to extract from.
        l_target: Target L* value.
        h_steps: Number of hue angle samples.
        l_tolerance: L* tolerance for including points.

    Returns:
        Tuple of (hue_angles, chroma_values) arrays.
    """
    lab = gamut.lab
    L = lab[:, 0]
    a = lab[:, 1]
    b = lab[:, 2]

    # Filter points near target L*
    mask = np.abs(L - l_target) < l_tolerance

    if not np.any(mask):
        return np.array([]), np.array([])

    a_sel = a[mask]
    b_sel = b[mask]

    # Convert to polar
    c_sel = np.sqrt(a_sel**2 + b_sel**2)
    h_sel = np.arctan2(b_sel, a_sel)
    h_sel = np.mod(h_sel, 2 * np.pi)

    # Bin by hue and take maximum chroma in each bin
    h_bins = np.linspace(0, 2 * np.pi, h_steps + 1)
    h_centers = (h_bins[:-1] + h_bins[1:]) / 2
    c_max = np.zeros(h_steps)

    indices = np.digitize(h_sel, h_bins) - 1
    indices = np.clip(indices, 0, h_steps - 1)

    for i in range(h_steps):
        mask_bin = indices == i
        if np.any(mask_bin):
            c_max[i] = np.max(c_sel[mask_bin])

    # Remove empty bins
    valid = c_max > 0
    return h_centers[valid], c_max[valid]
