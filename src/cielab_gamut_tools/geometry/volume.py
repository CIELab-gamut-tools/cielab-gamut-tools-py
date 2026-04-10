"""
Gamut volume computation via cylindrical integration.

The volume is computed by mapping the gamut surface to cylindrical
coordinates (L*, C*, h) using ray-triangle intersection, then integrating.

This implementation matches the algorithm in gamut-volume-m (MATLAB)
which is the reference implementation for IEC and ICDM standards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from cielab_gamut_tools.gamut import Gamut


def compute_volume(
    lab: NDArray[np.floating],
    triangles: NDArray[np.integer],
    l_steps: int = 100,
    h_steps: int = 360,
) -> float:
    """
    Compute gamut volume using cylindrical integration.

    The algorithm:
    1. For each (L*, h) grid cell, shoot a ray from origin in the hue direction
    2. Find all triangle intersections using ray-triangle intersection
    3. Record intersection distances and surface orientations
    4. Integrate: V = Σ sign × t² × ΔL × Δh / 2

    Args:
        lab: CIELab coordinates of surface vertices, shape (N, 3).
        triangles: Triangle vertex indices, shape (M, 3).
        l_steps: Number of L* discretization steps (default 100).
        h_steps: Number of hue angle steps (default 360).

    Returns:
        The gamut volume in CIELab cubic units.
    """
    # Build cylindrical map using ray-triangle intersection
    cylmap = _build_cylindrical_map(lab, triangles, l_steps, h_steps)

    # Integrate using cylindrical volume formula
    # V = Σ sign × t² × dL × dh / 2
    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    volume = 0.0
    for p in range(l_steps):
        for q in range(h_steps):
            cm = cylmap[p, q]
            if cm is not None and len(cm) > 0:
                # cm[:, 0] is sign, cm[:, 1] is t (chroma/distance)
                volume += np.sum(cm[:, 0] * (cm[:, 1] ** 2)) * dl * dh / 2

    return float(volume)


def _build_cylindrical_map(
    lab: NDArray[np.floating],
    triangles: NDArray[np.integer],
    l_steps: int,
    h_steps: int,
) -> NDArray:
    """
    Build cylindrical map using ray-triangle intersection.

    For each (L*, hue) grid cell, shoots a ray from the L* axis and finds
    all intersections with the triangulated gamut surface.

    This matches the algorithm in CIEtools/cielab_cylindrical_map.m

    Args:
        lab: CIELab coordinates, shape (N, 3) as [L*, a*, b*].
        triangles: Triangle indices, shape (M, 3).
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        Object array of shape (l_steps, h_steps), where each element is
        either None or an array of shape (K, 2) containing [sign, t] pairs
        for K intersections.
    """
    # Reorder to [a*, b*, L*] to match MATLAB's Z matrix
    Z = lab[:, [1, 2, 0]]

    # Get triangle vertices
    tri_v0 = Z[triangles[:, 0]]  # Shape (M, 3)
    tri_v1 = Z[triangles[:, 1]]
    tri_v2 = Z[triangles[:, 2]]

    # Find min/max L* for each triangle (L* is now column 2)
    min_L = np.minimum(np.minimum(tri_v0[:, 2], tri_v1[:, 2]), tri_v2[:, 2])
    max_L = np.maximum(np.maximum(tri_v0[:, 2], tri_v1[:, 2]), tri_v2[:, 2])

    # Define L* and Hue grid
    delta_hue = 2 * np.pi / h_steps
    L_edges = np.linspace(0, 100, l_steps + 1)
    hue_edges = np.linspace(0, 2 * np.pi, h_steps + 1)

    # Initialize cylindrical map as object array
    cylmap = np.empty((l_steps, h_steps), dtype=object)

    # For every step in L*
    for p in range(l_steps):
        L_mid = (L_edges[p] + L_edges[p + 1]) / 2

        # Find triangles that span this L* value
        ix = np.where((L_mid >= min_L) & (L_mid <= max_L))[0]

        if len(ix) == 0:
            for q in range(h_steps):
                cylmap[p, q] = None
            continue

        # Get vertices of relevant triangles
        vert0 = tri_v0[ix]  # Shape (n_relevant, 3)
        vert1 = tri_v1[ix]
        vert2 = tri_v2[ix]

        # Ray origin at (0, 0, L_mid) - replicated for each triangle
        orig = np.zeros((len(ix), 3))
        orig[:, 2] = L_mid

        # Edge vectors
        edge1 = vert1 - vert0
        edge2 = vert2 - vert0

        # Vector from vertex to origin
        o = orig - vert0

        # Pre-calculate cross products (these don't depend on ray direction)
        e2e1 = np.cross(edge2, edge1)
        e2o = np.cross(edge2, o)
        oe1 = np.cross(o, edge1)

        # Determinant component that doesn't involve direction
        # e2oe1 = dot(edge2, cross(o, edge1)) = dot(edge2, oe1)
        e2oe1 = np.sum(edge2 * oe1, axis=1)

        # Drop the L* coordinate as ray direction always has dL*=0
        # (ray is in the a*-b* plane at constant L*)
        e2e1_2d = e2e1[:, :2]
        e2o_2d = e2o[:, :2]
        oe1_2d = oe1[:, :2]

        # For every step in Hue
        for q in range(h_steps):
            hue_mid = (hue_edges[q] + hue_edges[q + 1]) / 2

            # Ray direction unit vector in a*-b* plane
            # Note: MATLAB uses [sin(h), cos(h)] which puts 0° along +b* axis
            dir_2d = np.array([np.sin(hue_mid), np.cos(hue_mid)])

            # Compute ray-triangle intersection using Möller-Trumbore algorithm
            # idet = 1 / dot(edge2 × edge1, dir)
            det = e2e1_2d @ dir_2d

            # Avoid division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                idet = np.where(np.abs(det) > 1e-10, 1.0 / det, 0.0)

            # Barycentric coordinates
            u = (e2o_2d @ dir_2d) * idet
            v = (oe1_2d @ dir_2d) * idet

            # Distance along ray (chroma value)
            t = e2oe1 * idet

            # Find triangles where ray passes within their edges
            # Triangle interior: u >= 0, v >= 0, u + v <= 1, t >= 0
            valid = (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0)

            # If no valid intersection found, try with tolerance
            if not np.any(valid):
                valid = (u >= -0.001) & (v >= -0.001) & (u + v <= 1.001) & (t >= 0)

            if not np.any(valid):
                cylmap[p, q] = None
                continue

            # Get sign (surface orientation) and distance for valid intersections
            signs = np.sign(idet[valid])
            distances = t[valid]

            # Build intersection array [sign, t]
            cm = np.column_stack([signs, distances])

            # Sort by distance
            sort_idx = np.argsort(cm[:, 1])
            cm = cm[sort_idx]

            # Check for surface parity errors (matching MATLAB logic)
            # This handles cases where rays graze edges
            # cm = cm(flip(cumsum(flip(cm(:,1))))*2-cm(:,1)==1,:)
            if len(cm) > 0:
                flipped_signs = cm[::-1, 0]
                cumsum_flipped = np.cumsum(flipped_signs)
                parity_check = cumsum_flipped[::-1] * 2 - cm[:, 0]
                keep = parity_check == 1
                cm = cm[keep]

            cylmap[p, q] = cm if len(cm) > 0 else None

    return cylmap


def get_cylindrical_map(
    gamut: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> NDArray:
    """
    Get the cylindrical map for a gamut.

    This is useful for gamut intersection calculations.

    Args:
        gamut: The gamut to map.
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        Cylindrical map array.
    """
    return _build_cylindrical_map(gamut.lab, gamut.triangles, l_steps, h_steps)


def intersect_gamuts(
    gamut_a: "Gamut",
    gamut_b: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> "Gamut":
    """
    Compute the intersection of two gamuts.

    The intersection is computed by taking the overlapping regions at each
    (L*, h) grid point from both gamuts' cylindrical maps.

    This matches the algorithm in IntersectGamuts.m from gamut-volume-m.

    Args:
        gamut_a: First gamut.
        gamut_b: Second gamut (can be Gamut or SyntheticGamut).
        l_steps: Number of L* bins (default 100).
        h_steps: Number of hue bins (default 360).

    Returns:
        A new Gamut representing the intersection.

    Note:
        The returned gamut has a pre-computed cylindrical map but no surface
        tesselation. It can be used with volume() and plot_rings() but not
        plot_surface().
    """
    from cielab_gamut_tools.gamut import Gamut

    # Get underlying Gamut if SyntheticGamut
    if hasattr(gamut_a, "gamut"):
        gamut_a = gamut_a.gamut
    if hasattr(gamut_b, "gamut"):
        gamut_b = gamut_b.gamut

    # Build cylindrical maps for both gamuts
    cylmap_a = _build_cylindrical_map(gamut_a.lab, gamut_a.triangles, l_steps, h_steps)
    cylmap_b = _build_cylindrical_map(gamut_b.lab, gamut_b.triangles, l_steps, h_steps)

    # Intersect the cylindrical maps cell by cell
    cylmap_intersected = np.empty((l_steps, h_steps), dtype=object)

    for p in range(l_steps):
        for q in range(h_steps):
            cylmap_intersected[p, q] = _intersect_cells(cylmap_a[p, q], cylmap_b[p, q])

    # Create a Gamut-like object with the intersected map
    # We use empty arrays for lab/triangles since we only have cylmap
    intersected = Gamut(
        lab=np.empty((0, 3)),
        triangles=np.empty((0, 3), dtype=np.int32),
    )

    # Store the pre-computed cylindrical map and parameters
    intersected._cylindrical_map = cylmap_intersected
    intersected._cylmap_l_steps = l_steps
    intersected._cylmap_h_steps = h_steps

    # Pre-compute volume since we have the cylmap
    intersected._volume = _integrate_cylmap(cylmap_intersected, l_steps, h_steps)

    return intersected


def _intersect_cells(
    cell_a: NDArray[np.floating] | None,
    cell_b: NDArray[np.floating] | None,
) -> NDArray[np.floating] | None:
    """
    Intersect two cylindrical map cells.

    Each cell contains [sign, distance] pairs representing ray intersections
    with the gamut surface. The intersection keeps only the regions where
    both gamuts overlap.

    This matches the local intersect() function in IntersectGamuts.m.

    Args:
        cell_a: Cell from first gamut, shape (K, 2) or None.
        cell_b: Cell from second gamut, shape (J, 2) or None.

    Returns:
        Intersected cell, shape (M, 2) or None.
    """
    # Handle empty cells
    if cell_a is None or len(cell_a) == 0:
        return None
    if cell_b is None or len(cell_b) == 0:
        return None

    # Fix surface parity errors (same as in _build_cylindrical_map)
    cell_a = _fix_parity(cell_a)
    cell_b = _fix_parity(cell_b)

    if len(cell_a) == 0 or len(cell_b) == 0:
        return None

    sa = len(cell_a)
    sb = len(cell_b)

    # Build combined array with columns: [sign, distance, in_a, in_b]
    # where in_a and in_b track which gamut each intersection belongs to
    combined = np.zeros((sa + sb, 4))

    # Add cell_a entries: columns [sign, distance, sign, 0]
    combined[:sa, 0] = cell_a[:, 0]  # sign
    combined[:sa, 1] = cell_a[:, 1]  # distance
    combined[:sa, 2] = cell_a[:, 0]  # in_a tracking

    # Add cell_b entries: columns [sign, distance, 0, sign]
    combined[sa:, 0] = cell_b[:, 0]  # sign
    combined[sa:, 1] = cell_b[:, 1]  # distance
    combined[sa:, 3] = cell_b[:, 0]  # in_b tracking

    # Sort by distance (descending, to match MATLAB)
    sort_idx = np.argsort(-combined[:, 1])
    combined = combined[sort_idx]

    # Compute cumulative sum of in_a and in_b (tracks "inside" state)
    cumsum_a = np.cumsum(combined[:, 2])
    cumsum_b = np.cumsum(combined[:, 3])

    # Take minimum - we're "inside" intersection only when inside both
    inside_both = np.minimum(cumsum_a, cumsum_b)

    # Keep entries where the inside state changes
    changes = np.diff(inside_both, prepend=0) != 0

    # Skip first entry (prepended 0 causes spurious change)
    result = combined[changes, :2]

    return result if len(result) > 0 else None


def _fix_parity(cell: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Fix surface parity errors in a cylindrical map cell.

    Removes entries that would cause incorrect inside/outside tracking
    due to rays grazing triangle edges.

    Args:
        cell: Cell array with [sign, distance] pairs.

    Returns:
        Fixed cell array.
    """
    if len(cell) == 0:
        return cell

    # MATLAB: cm = cm(flip(cumsum(flip(cm(:,1))))*2-cm(:,1)==1,:)
    flipped_signs = cell[::-1, 0]
    cumsum_flipped = np.cumsum(flipped_signs)
    parity_check = cumsum_flipped[::-1] * 2 - cell[:, 0]
    keep = parity_check == 1

    return cell[keep]


def _integrate_cylmap(
    cylmap: NDArray,
    l_steps: int,
    h_steps: int,
) -> float:
    """
    Integrate a cylindrical map to compute volume.

    Args:
        cylmap: Cylindrical map array of shape (l_steps, h_steps).
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        The integrated volume.
    """
    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    volume = 0.0
    for p in range(l_steps):
        for q in range(h_steps):
            cm = cylmap[p, q]
            if cm is not None and len(cm) > 0:
                volume += np.sum(cm[:, 0] * (cm[:, 1] ** 2)) * dl * dh / 2

    return float(volume)
