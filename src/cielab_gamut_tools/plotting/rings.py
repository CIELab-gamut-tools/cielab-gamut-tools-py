"""
2D gamut rings visualization.

Each ring corresponds to an L* level. The radius at each hue angle is
computed so that the area enclosed by the ring equals the cumulative gamut
volume up to that L* level. The plot is in Cartesian (a*, b*) coordinates.

Algorithm matches calcGamutRings.m / PlotRings.m from gamut-volume-m (MATLAB
reference implementation for IEC/ICDM standards).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from cielab_gamut_tools.gamut import Gamut


@dataclass
class _GamutRings:
    """Ring coordinates and metadata returned by _calc_gamut_rings."""
    x: np.ndarray       # (n_query, h_steps) — ring x coords (a* axis)
    y: np.ndarray       # (n_query, h_steps) — ring y coords (b* axis)
    r2: np.ndarray      # (n_query, h_steps) — squared radii
    ux: np.ndarray      # (h_steps,) — unit direction along a*
    uy: np.ndarray      # (h_steps,) — unit direction along b*
    vol: float          # total gamut volume
    volmap: np.ndarray  # (l_steps, h_steps) — per-cell volume
    dH: float           # hue step size (radians)
    dL: float           # L* step size
    l_rings: list[float]  # inner L* values (without 0 and 100)


def plot_rings(
    gamut: "Gamut",
    reference: "Gamut | None" = None,
    reference2: "Gamut | None" = None,
    *,
    # Ring format
    l_rings: list[float] | None = None,
    l_label_indices: list[int] = [0, 4],
    l_label_colors: str | list | None = "default",
    ring_line: str = "k",
    ref_line: str = "--k",
    ref2_line: str = ":k",
    # Colour bands
    show_bands: bool = True,
    band_chroma: float = 50.0,
    band_ls: float | tuple | list = (20.0, 90.0),
    band_hue: float | Literal["match"] = "match",
    show_ref_bands: bool = True,
    ref_band_chroma: float = 0.0,
    ref_band_ls: float | tuple | list = (30.0, 98.0),
    ref_band_hue: float | Literal["match"] = "match",
    # Reference options
    ring_reference: Literal["none", "ref", "intersection"] = "none",
    intersection_plot: bool = False,
    intersect_gamut: bool = False,
    intersection_line: str = "",
    # Primary indicators
    primaries: Literal["none", "rgb", "all"] = "rgb",
    primary_color: Literal["input", "output"] = "output",
    primary_chroma: float | Literal["auto"] = 950.0,
    primary_origin: Literal["centre", "center", "ring"] = "centre",
    ref_primaries: Literal["none", "rgb", "all"] = "none",
    ref_primary_chroma: float | Literal["auto"] = "auto",
    ref_primary_origin: Literal["centre", "center", "ring"] = "ring",
    # Decorations
    cent_mark: str | None = "+k",
    cent_mark_size: float = 20.0,
    chroma_rings: list[float] = [],
    # Axes
    ax: "Axes | None" = None,
    clear_axes: bool = True,
) -> "Figure":
    """
    Create a 2D gamut rings plot in the a*-b* plane.

    Each ring corresponds to an L* lightness level. The radius at each hue
    angle encodes the cumulative gamut volume up to that L* level, such that
    the area enclosed by the ring equals the cumulative volume. This matches
    the MATLAB PlotRings/calcGamutRings algorithm.

    Args:
        gamut: The gamut to plot.
        reference: Optional reference gamut.
        reference2: Optional second reference gamut (outer ring only, with
            ``ref2_line`` style).
        l_rings: Inner ring L* values (default: 10, 20, ..., 90). The outer
            ring at L*=100 is always included.
        l_label_indices: 0-based indices into ``[*l_rings, 100]`` of which
            rings to label. Default ``[0, 4]`` → L*=10 and L*=50.
            Pass ``[]`` to suppress all labels.
        l_label_colors: Colour(s) for the ring labels.  ``"default"`` makes
            the outermost label black and all others white. A single matplotlib
            colour string applies to all labels. A list gives one colour per
            label.
        ring_line: Matplotlib linestyle for all gamut rings (default ``"k"``).
        ref_line: Linestyle for the first reference outer ring (default
            ``"--k"``).
        ref2_line: Linestyle for the second reference outer ring (default
            ``":k"``).
        show_bands: Draw coloured fills between rings (default ``True``).
        band_chroma: Chroma saturation of band fill colours (default 50).
            Set to 0 for monochrome bands.
        band_ls: Band lightness value(s). A 2-element tuple ``(lo, hi)`` is
            linearly interpolated across all bands; a list of N values gives
            one per band; a scalar repeats for all bands.
        band_hue: Hue of the band fill. ``"match"`` (default) uses the hue
            angle of each chart sector. A float (degrees) uses a fixed hue.
        show_ref_bands: Show reference colour bands behind the test bands.
            Only active when ``intersection_plot=True``.
        ref_band_chroma: Chroma of reference band colours (default 0).
        ref_band_ls: Reference band lightness, same semantics as ``band_ls``.
        ref_band_hue: Reference band hue, same semantics as ``band_hue``.
        ring_reference: How the reference gamut is shown on each inner ring.
            ``"none"`` (default) — only the outer ring of the reference is
            shown.  ``"ref"`` — all inner rings of the reference are shown
            inside the test rings.  ``"intersection"`` — inner rings show
            the intersection of test and reference.
        intersection_plot: If ``True`` (and a reference is provided), the
            reference gamut forms the outer boundary and the test gamut area
            is shown inside it. Forces ``intersect_gamut=True``.
        intersect_gamut: Replace the test gamut with its intersection with
            the reference before display (original volume retained for title).
        intersection_line: Linestyle for the intersection boundary in
            intersection-plot mode. ``""`` (default) draws no line.
        primaries: Which test gamut primaries to show as arrows.
            ``"rgb"`` (default), ``"all"`` (R,G,B,C,M,Y), or ``"none"``.
            Requires ``gamut.rgb`` to be set.
        primary_color: Arrow head colour source. ``"output"`` (default) uses
            the gamut's Lab value converted to sRGB. ``"input"`` uses the
            nominal primary colour.
        primary_chroma: C* radius of the primary arrow head (default 950).
            ``"auto"`` sets it to ``max_chroma + 100``.
        primary_origin: Where primary arrows start. ``"centre"`` (default)
            or ``"ring"``.
        ref_primaries: Which reference primaries to show (default ``"none"``).
        ref_primary_chroma: C* radius of reference primary arrow heads.
            ``"auto"`` (default) sets it to ``primary_chroma + 50``.
        ref_primary_origin: Where reference primary arrows start (default
            ``"ring"``).
        cent_mark: Matplotlib marker spec for the centre cross (default
            ``"+k"``). Pass ``None`` to suppress.
        cent_mark_size: Size of the centre mark (default 20).
        chroma_rings: C* radii at which to draw constant-chroma reference
            circles (default ``[]``).
        ax: Optional matplotlib axes. If ``None``, a new figure is created.
        clear_axes: Clear the axes before plotting (default ``True``).

    Returns:
        The matplotlib Figure containing the plot.
    """
    import matplotlib.pyplot as plt

    if l_rings is None:
        l_rings = list(np.arange(10, 100, 10))

    # ── Resolve gamut / intersection logic ────────────────────────────────
    _ref = _unwrap(reference)
    _ref2 = _unwrap(reference2)

    intersection_plot = intersection_plot and _ref is not None
    intersect_gamut = intersect_gamut or intersection_plot

    if intersect_gamut and _ref is not None:
        from cielab_gamut_tools.geometry.volume import intersect_gamuts
        orig_vol = _unwrap(gamut).volume()
        test_gamut = intersect_gamuts(_unwrap(gamut), _ref)
    else:
        test_gamut = _unwrap(gamut)
        orig_vol = None

    # ── Compute ring coordinates ───────────────────────────────────────────
    if intersection_plot:
        rings = _calc_gamut_rings(_ref, l_rings)
        test_x, test_y, test_vol = _calc_sub_rings(rings, test_gamut)
        ref_x, ref_y, ref_vol = _calc_sub_rings(rings, _ref)
    else:
        rings = _calc_gamut_rings(test_gamut, l_rings)
        test_x = rings.x[1:]   # skip L*=0 row; shape (n_rings, h_steps)
        test_y = rings.y[1:]
        test_vol = rings.vol
        if _ref is not None:
            ref_rings_outer = _calc_gamut_rings(_ref, [])
            ref_x = ref_rings_outer.x[1:]
            ref_y = ref_rings_outer.y[1:]

    # ── Set up axes ────────────────────────────────────────────────────────
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.get_figure()

    if clear_axes:
        ax.cla()

    ax.set_aspect("equal")

    # ── Max chroma (for auto primary_chroma) ──────────────────────────────
    max_chroma = float(np.sqrt(np.max(test_x ** 2 + test_y ** 2)))
    if _ref is not None and not intersection_plot:
        max_chroma = max(max_chroma, float(np.sqrt(np.max(ref_x ** 2 + ref_y ** 2))))

    _primary_chroma = max_chroma + 100 if primary_chroma == "auto" else float(primary_chroma)
    _ref_primary_chroma = _primary_chroma + 50 if ref_primary_chroma == "auto" else float(ref_primary_chroma)

    # ── Reference colour bands (intersection_plot only) ───────────────────
    if intersection_plot and show_ref_bands:
        _draw_bands(ax, rings, ref_x, ref_y, ref_band_chroma, ref_band_ls, ref_band_hue)

    # ── Test gamut colour bands ───────────────────────────────────────────
    if show_bands:
        _draw_bands(ax, rings, test_x, test_y, band_chroma, band_ls, band_hue)

    # ── Constant-chroma rings (behind gamut rings) ────────────────────────
    if chroma_rings:
        theta = np.linspace(0, 2 * np.pi, 361)
        for r in chroma_rings:
            ax.plot(r * np.sin(theta), r * np.cos(theta),
                    color="0.7", linewidth=0.8, zorder=0.5)

    # ── Main gamut ring lines ─────────────────────────────────────────────
    if ring_line:
        for i in range(rings.x.shape[0]):
            xi = np.append(rings.x[i], rings.x[i, 0])
            yi = np.append(rings.y[i], rings.y[i, 0])
            lw = 1.0 if i < rings.x.shape[0] - 1 else 1.5
            ax.plot(xi, yi, ring_line, linewidth=lw)

    # ── Intersection boundary line ────────────────────────────────────────
    if intersection_line and intersection_plot:
        for i in range(test_x.shape[0]):
            xi = np.append(test_x[i], test_x[i, 0])
            yi = np.append(test_y[i], test_y[i, 0])
            ax.plot(xi, yi, intersection_line, linewidth=1.0)

    # ── Per-ring reference overlay (ring_reference) ───────────────────────
    if ring_reference != "none" and _ref is not None and not intersection_plot:
        if ring_reference == "ref":
            sub_x, sub_y, _ = _calc_sub_rings(rings, _ref)
        else:  # "intersection"
            from cielab_gamut_tools.geometry.volume import intersect_gamuts
            isect = intersect_gamuts(test_gamut, _ref)
            sub_x, sub_y, _ = _calc_sub_rings(rings, isect)
        for i in range(sub_x.shape[0]):
            xi = np.append(sub_x[i], sub_x[i, 0])
            yi = np.append(sub_y[i], sub_y[i, 0])
            ax.plot(xi, yi, ref_line, linewidth=1.0)

    # ── L* ring labels ────────────────────────────────────────────────────
    all_l = list(l_rings) + [100]
    n_all = len(all_l)
    valid_indices = [i for i in l_label_indices if i < n_all]
    label_colors = _resolve_label_colors(l_label_colors, valid_indices, n_all)

    for j, li in enumerate(valid_indices):
        row = li + 1  # +1 to skip L*=0 row
        col = int(rings.x.shape[1] * 15 // 16)
        ax.text(
            rings.x[row, col], rings.y[row, col],
            f"L*={all_l[li]:.0f}",
            color=label_colors[j], fontsize=9,
            ha="center", va="center",
        )

    # ── Centre mark ───────────────────────────────────────────────────────
    if cent_mark:
        ax.plot(0, 0, cent_mark, markersize=cent_mark_size,
                markeredgewidth=1.5, zorder=5)

    # ── Reference outer ring ──────────────────────────────────────────────
    if _ref is not None and not intersection_plot and ref_line:
        ref_outer = _calc_gamut_rings(_ref, [])
        xi = np.append(ref_outer.x[-1], ref_outer.x[-1, 0])
        yi = np.append(ref_outer.y[-1], ref_outer.y[-1, 0])
        ax.plot(xi, yi, ref_line, linewidth=1.5)

    # ── Second reference outer ring ───────────────────────────────────────
    if _ref2 is not None and ring_reference == "none" and ref2_line:
        ref2_outer = _calc_gamut_rings(_ref2, [])
        xi = np.append(ref2_outer.x[-1], ref2_outer.x[-1, 0])
        yi = np.append(ref2_outer.y[-1], ref2_outer.y[-1, 0])
        ax.plot(xi, yi, ref2_line, linewidth=1.5)

    # ── Primary colour indicators ─────────────────────────────────────────
    n_prims = {"none": 0, "rgb": 3, "all": 6}[primaries]
    n_ref_prims = {"none": 0, "rgb": 3, "all": 6}[ref_primaries]

    _g = _unwrap(gamut)
    if _g.rgb is None:
        n_prims = 0
    if _ref is None or _ref.rgb is None:
        n_ref_prims = 0

    if n_prims > 0 or n_ref_prims > 0:
        _draw_primaries(
            ax, rings, _g, _ref,
            test_x, ref_x if (_ref is not None and not intersection_plot) else None,
            n_prims, n_ref_prims,
            primary_color, _primary_chroma, primary_origin,
            _ref_primary_chroma, ref_primary_origin,
        )

    # ── Axis padding, labels, title ───────────────────────────────────────
    ax.margins(0.05)
    ax.set_xlabel("a*$_{RSS}$")
    ax.set_ylabel("b*$_{RSS}$")

    gamut_title = getattr(_g, "title", None) or ""
    vol_label = orig_vol if orig_vol is not None else test_vol
    if gamut_title:
        ax.set_title(f"CIELab gamut rings\n{gamut_title}\nVolume = {vol_label:.0f}")
    else:
        ax.set_title(f"CIELab gamut rings\nVolume = {vol_label:.0f}")

    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _unwrap(g: "Gamut | None") -> "Gamut | None":
    """Return the underlying Gamut from a SyntheticGamut or Gamut, or None."""
    if g is None:
        return None
    if hasattr(g, "gamut"):
        return g.gamut
    return g


def _calc_gamut_rings(
    gamut: "Gamut",
    l_rings: list[float],
    l_steps: int = 100,
    h_steps: int = 360,
) -> _GamutRings:
    """
    Calculate ring x, y coordinates from the gamut cylindrical map.

    Matches calcGamutRings.m from gamut-volume-m. For each hue angle, the
    ring radius at a given L* level is chosen so that:
        area = sum_h(r² * dH / 2) = cumulative gamut volume up to L*

    Returns:
        _GamutRings with x/y shape (len(l_rings)+2, h_steps) — rows for
        L* = [0, l_rings..., 100].
    """
    from cielab_gamut_tools.geometry.volume import get_cylindrical_map

    cylmap, counts = get_cylindrical_map(gamut, l_steps, h_steps)
    l_steps = cylmap.shape[0]
    h_steps = cylmap.shape[1]

    dH = 2 * np.pi / h_steps
    dL = 100.0 / l_steps

    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]
    volmap = (
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask, axis=2)
        * dL * dH / 2
    )

    cumvol = np.cumsum(volmap, axis=0)
    r2_full = 2.0 * cumvol / dH

    L_grid = np.linspace(0.0, 100.0, l_steps + 1)
    r2_grid = np.vstack([np.zeros((1, h_steps)), r2_full])

    L_query = np.concatenate([[0.0], l_rings, [100.0]])
    idx = np.searchsorted(L_grid, L_query, side="right")
    idx = np.clip(idx, 1, len(L_grid) - 1)
    frac = (L_query - L_grid[idx - 1]) / (L_grid[idx] - L_grid[idx - 1])
    frac = np.clip(frac, 0.0, 1.0)

    r2_lo = r2_grid[idx - 1, :]
    r2_hi = r2_grid[idx, :]
    r2 = r2_lo + frac[:, np.newaxis] * (r2_hi - r2_lo)

    r = np.sqrt(np.maximum(r2, 0.0))

    midH = np.arange(dH / 2, 2 * np.pi, dH)
    ux = np.sin(midH)
    uy = np.cos(midH)

    x = r * ux
    y = r * uy

    return _GamutRings(
        x=x, y=y, r2=r2,
        ux=ux, uy=uy,
        vol=float(np.sum(volmap)),
        volmap=volmap,
        dH=dH, dL=dL,
        l_rings=list(l_rings),
    )


def _calc_sub_rings(
    rings: _GamutRings,
    sub_gamut: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Map sub_gamut's cumulative volume into the coordinate frame of rings.

    Matches calcSubRings() in PlotRings.m (lines 585-593). The sub-gamut's
    area at each ring level is clamped to the outer reference ring boundary.

    Returns:
        (x, y) arrays shape (n_bands, h_steps) — skips the L*=0 row — and
        the total volume of sub_gamut.
    """
    from cielab_gamut_tools.geometry.volume import get_cylindrical_map

    cylmap, counts = get_cylindrical_map(sub_gamut, l_steps, h_steps)
    dH = rings.dH
    dL = rings.dL

    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]
    volmap_sub = (
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask, axis=2)
        * dL * dH / 2
    )

    # r² at each L* grid point for sub_gamut
    r2_sub_full = 2.0 * np.cumsum(volmap_sub, axis=0) / dH   # (l_steps, h_steps)
    r2_sub_grid = np.vstack([np.zeros((1, h_steps)), r2_sub_full])  # (l_steps+1, h_steps)

    # Interpolate to the same L* query values as the outer rings
    L_grid = np.linspace(0.0, 100.0, l_steps + 1)
    L_query = np.concatenate([[0.0], rings.l_rings, [100.0]])
    idx = np.searchsorted(L_grid, L_query, side="right")
    idx = np.clip(idx, 1, len(L_grid) - 1)
    frac = np.clip((L_query - L_grid[idx - 1]) / (L_grid[idx] - L_grid[idx - 1]), 0.0, 1.0)
    ri2 = r2_sub_grid[idx - 1] + frac[:, None] * (r2_sub_grid[idx] - r2_sub_grid[idx - 1])

    rg2 = rings.r2  # outer reference r², shape (n_query, h_steps)

    # Clamp sub-gamut bands to outer ring: r = sqrt(min(rg2[n+1], (ri2[n+1]-ri2[n]) + rg2[n]))
    r = np.sqrt(np.minimum(rg2[1:], (ri2[1:] - ri2[:-1]) + rg2[:-1]))
    x = r * rings.ux
    y = r * rings.uy

    return x, y, float(volmap_sub.sum())


def _norm_range(band_ls: float | tuple | list, n: int) -> np.ndarray:
    """
    Interpolate lightness values across N bands.

    Matches normRange() in PlotRings.m (lines 603-613).
    - Scalar → repeated N times.
    - 2-element sequence → linearly interpolated from lo to hi.
    - N-element sequence → used as-is.
    """
    ls = np.asarray(band_ls, dtype=float).ravel()
    if ls.size == 1:
        return np.full(n, ls[0])
    steps = np.linspace(0.0, 1.0, n)
    src_steps = np.linspace(0.0, 1.0, ls.size)
    return np.interp(steps, src_steps, ls)


def _draw_bands(
    ax: "Axes",
    rings: _GamutRings,
    outer_x: np.ndarray,
    outer_y: np.ndarray,
    chroma: float,
    band_ls: float | tuple | list,
    band_hue: float | Literal["match"],
) -> None:
    """
    Draw coloured wedge fills between consecutive rings.

    For each band n, fills the region between rings.x[n]/rings.y[n] (inner)
    and outer_x[n]/outer_y[n] (outer). Each hue sector is one quad.
    Matches the triangle-strip patch approach in PlotRings.m lines 332-346.
    """
    from cielab_gamut_tools.colorspace.lab import lab_to_srgb_display
    from matplotlib.collections import PolyCollection

    n_bands = outer_x.shape[0]
    n_hue = outer_x.shape[1]
    ls_vals = _norm_range(band_ls, n_bands)

    # Precompute per-hue unit directions
    ux = rings.ux  # (h_steps,)
    uy = rings.uy

    for n in range(n_bands):
        inner_x = rings.x[n]     # (h_steps,)
        inner_y = rings.y[n]
        out_x = outer_x[n]
        out_y = outer_y[n]
        L = ls_vals[n]

        # Per-hue fill colour: Lab(L, chroma*ux, chroma*uy) → sRGB
        if band_hue == "match":
            a_vals = chroma * ux
            b_vals = chroma * uy
        else:
            angle_rad = np.deg2rad(band_hue)
            a_vals = np.full(n_hue, chroma * np.sin(angle_rad))
            b_vals = np.full(n_hue, chroma * np.cos(angle_rad))

        lab_pts = np.column_stack([np.full(n_hue, L), a_vals, b_vals])
        rgb = lab_to_srgb_display(lab_pts) / 255.0  # (h_steps, 3)
        rgb = np.clip(rgb, 0.0, 1.0)

        # Build quads: for each hue step i, quad = [inner[i], outer[i], outer[i+1], inner[i+1]]
        i0 = np.arange(n_hue)
        i1 = (i0 + 1) % n_hue

        verts = np.stack([
            np.column_stack([inner_x[i0], inner_y[i0]]),  # (h_steps, 2)
            np.column_stack([out_x[i0],   out_y[i0]]),
            np.column_stack([out_x[i1],   out_y[i1]]),
            np.column_stack([inner_x[i1], inner_y[i1]]),
        ], axis=1)  # (h_steps, 4, 2)

        coll = PolyCollection(verts, facecolors=rgb, edgecolors=rgb,
                              linewidths=0.5, antialiased=False)
        ax.add_collection(coll)


def _resolve_label_colors(
    colors_spec: str | list | None,
    valid_indices: list[int],
    n_all: int,
) -> list:
    """Resolve label colour specification to a list of matplotlib colour specs."""
    n = len(valid_indices)
    if n == 0:
        return []

    if colors_spec is None or (isinstance(colors_spec, str) and colors_spec == "default"):
        # Outermost label (index == n_all-1) is black; others are white
        return ["black" if li == n_all - 1 else "white" for li in valid_indices]

    if isinstance(colors_spec, str):
        return [colors_spec] * n

    if isinstance(colors_spec, np.ndarray) and colors_spec.ndim == 2:
        return [colors_spec[i] for i in range(min(n, len(colors_spec)))]

    if isinstance(colors_spec, (list, tuple)):
        if len(colors_spec) == 3 and not isinstance(colors_spec[0], (list, tuple, np.ndarray)):
            # Single RGB triplet as list
            return [colors_spec] * n
        return list(colors_spec)[:n]

    return ["white"] * n


def _draw_primaries(
    ax: "Axes",
    rings: _GamutRings,
    gamut: "Gamut",
    ref_gamut: "Gamut | None",
    test_x: np.ndarray,
    ref_x: "np.ndarray | None",
    n_prims: int,
    n_ref_prims: int,
    primary_color: str,
    primary_chroma: float,
    primary_origin: str,
    ref_primary_chroma: float,
    ref_primary_origin: str,
) -> None:
    """
    Draw primary colour arrow indicators. Matches PlotRings.m lines 413-537.
    """
    from cielab_gamut_tools.colorspace.lab import lab_to_srgb_display

    # R,G,B,C,M,Y as unit RGB triplets
    prims = np.vstack([np.eye(3), 1.0 - np.eye(3)])
    rgb_max = 1.0  # tesselation uses [0,1]

    use_output_col = (primary_color != "input")
    ring_origin = primary_origin in ("ring",)
    rring_origin = ref_primary_origin in ("ring",)

    h_steps = rings.x.shape[1]

    for n in range(max(n_prims, n_ref_prims)):
        ri = None  # index into ref_gamut arrays
        i = None   # index into gamut arrays

        # ── Reference primary ────────────────────────────────────────────
        if n < n_ref_prims and ref_gamut is not None and ref_gamut.rgb is not None:
            matches = np.where(
                np.all(np.isclose(ref_gamut.rgb, prims[n] * rgb_max, atol=1e-6), axis=1)
            )[0]
            if len(matches):
                ri = matches[0]
                rlab = ref_gamut.lab[ri]
                rcol = np.clip(lab_to_srgb_display(rlab[None]) / 255.0, 0, 1)[0]
                # Hue bin index (0-based, 360 steps, sin→a* axis)
                rhue = int(np.floor(0.5 + np.degrees(np.arctan2(rlab[1], rlab[2])) + 360) % 360)
                if ref_x is not None:
                    rring_chroma = float(np.sqrt(ref_x[-1, rhue] ** 2 + ref_x[-1, rhue] ** 2 + 1e-30))
                    # Compute from outer ref ring x/y
                    rring_chroma = float(np.hypot(ref_x[-1, rhue],
                                                   np.sqrt(np.maximum(0, rings.r2[-1, rhue]
                                                                       - ref_x[-1, rhue] ** 2))))
                else:
                    rring_chroma = 0.0
                rpt = rlab[1:3] * ref_primary_chroma / (np.linalg.norm(rlab[1:3]) + 1e-12)
                mpt = rpt * 0.9
                opt_r = (rlab[1:3] * rring_chroma / (np.linalg.norm(rlab[1:3]) + 1e-12)
                         if rring_origin else np.array([0.0, 0.0]))
                ax.plot([opt_r[0], mpt[0]], [opt_r[1], mpt[1]],
                        color=[0.7, 0.7, 0.7], linewidth=1.5)
                rvect = rpt - mpt
                ax.annotate("", xy=(rpt[0], rpt[1]), xytext=(mpt[0], mpt[1]),
                            arrowprops=dict(arrowstyle="-|>", color=rcol, lw=1.5))

        # ── Test gamut primary ───────────────────────────────────────────
        if n < n_prims and gamut.rgb is not None:
            matches = np.where(
                np.all(np.isclose(gamut.rgb, prims[n] * rgb_max, atol=1e-6), axis=1)
            )[0]
            if len(matches):
                i = matches[0]
                lab = gamut.lab[i]
                if use_output_col:
                    col = np.clip(lab_to_srgb_display(lab[None]) / 255.0, 0, 1)[0]
                else:
                    col = prims[n]
                hue = int(np.floor(0.5 + np.degrees(np.arctan2(lab[1], lab[2])) + 360) % 360)
                ring_chroma = float(np.sqrt(rings.x[-1, hue] ** 2 + rings.y[-1, hue] ** 2))
                pt = lab[1:3] * primary_chroma / (np.linalg.norm(lab[1:3]) + 1e-12)
                opt = (lab[1:3] * ring_chroma / (np.linalg.norm(lab[1:3]) + 1e-12)
                       if ring_origin else np.array([0.0, 0.0]))
                ax.annotate("", xy=(pt[0], pt[1]), xytext=(opt[0], opt[1]),
                            arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5))

        # ── Linking arc between test and reference primary ────────────────
        if ri is not None and i is not None:
            hue_start = int(np.floor(0.5 + np.degrees(np.arctan2(
                gamut.lab[i][1], gamut.lab[i][2])) + 360) % 360)
            hue_end = int(np.floor(0.5 + np.degrees(np.arctan2(
                ref_gamut.lab[ri][1], ref_gamut.lab[ri][2])) + 360) % 360)
            angles = np.arange(hue_start, hue_end + np.sign(hue_end - hue_start),
                               np.sign(hue_end - hue_start) or 1) / 180 * np.pi
            if len(angles) > 1:
                ax.plot(0.95 * primary_chroma * np.sin(angles),
                        0.95 * primary_chroma * np.cos(angles), ":k", linewidth=0.8)
