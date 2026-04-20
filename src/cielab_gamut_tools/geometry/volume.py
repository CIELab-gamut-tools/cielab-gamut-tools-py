"""
Gamut volume computation via cylindrical integration.

The volume is computed by mapping the gamut surface to cylindrical
coordinates (L*, C*, h) using ray-triangle intersection, then integrating.

This implementation matches the algorithm in gamut-volume-m (MATLAB)
which is the reference implementation for IEC and ICDM standards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numba
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from cielab_gamut_tools.gamut import Gamut

# Maximum number of intersections stored per (L*, hue) cell after parity
# filtering.  Most cells yield 0 (below the gamut's black level) or 1 (the
# ray origin on the L* axis is inside the gamut and exits the surface once).
# Occasionally 2 (origin outside the gamut — enters then exits).  4 is a
# conservative upper bound that covers all observed edge cases.
_MAX_K: int = 4


@numba.njit(cache=True)
def _process_hue_loop_nb(
    all_t: NDArray,
    all_idet: NDArray,
    valid: NDArray,
) -> tuple[NDArray, NDArray]:
    """
    JIT-compiled inner hue loop: collect, sort, and parity-filter intersections.

    Replaces the Python for-loop over all h_steps hue angles.  For each hue,
    extracts the valid ray-triangle intersection results from the pre-computed
    batched matrices, sorts by distance, applies the parity filter (matching
    the MATLAB cielab_cylindrical_map.m logic), and writes to a dense output.

    Args:
        all_t: Intersection distances, shape (n_tri, h_steps), float64.
        all_idet: Inverse determinants (sign encodes surface orientation),
            shape (n_tri, h_steps), float64.
        valid: Boolean hit mask, shape (n_tri, h_steps).

    Returns:
        result: Dense array shape (h_steps, 4, 2).
                result[q, j] = [sign, distance] for j-th intersection at hue q.
        counts: Number of valid intersections per hue, shape (h_steps,), int64.
    """
    n_tri = all_t.shape[0]
    h_steps = all_t.shape[1]

    result = np.zeros((h_steps, 4, 2))
    counts = np.zeros(h_steps, dtype=np.int64)

    # Pre-allocate temp buffers (max possible size is n_tri per hue)
    temp_s = np.empty(n_tri)   # signs
    temp_d = np.empty(n_tri)   # distances
    cs_right = np.empty(n_tri) # cumulative sum from right for parity filter

    for q in range(h_steps):
        # Collect valid intersections for this hue angle
        k = 0
        for i in range(n_tri):
            if valid[i, q]:
                idet_val = all_idet[i, q]
                # Match np.sign() exactly: 1, -1, or 0
                if idet_val > 0.0:
                    temp_s[k] = 1.0
                elif idet_val < 0.0:
                    temp_s[k] = -1.0
                else:
                    temp_s[k] = 0.0
                temp_d[k] = all_t[i, q]
                k += 1

        if k == 0:
            continue

        # Insertion sort by distance ascending (k is typically 1-4)
        for i in range(1, k):
            ks = temp_s[i]
            kd = temp_d[i]
            j = i - 1
            while j >= 0 and temp_d[j] > kd:
                temp_s[j + 1] = temp_s[j]
                temp_d[j + 1] = temp_d[j]
                j -= 1
            temp_s[j + 1] = ks
            temp_d[j + 1] = kd

        # Parity filter: keep entry i where (cumsum of signs from i to end)*2 - sign == 1
        # Matches MATLAB: cm = cm(flip(cumsum(flip(cm(:,1))))*2 - cm(:,1) == 1, :)
        cs = 0.0
        for i in range(k - 1, -1, -1):
            cs += temp_s[i]
            cs_right[i] = cs

        n_kept = 0
        for i in range(k):
            if cs_right[i] * 2.0 - temp_s[i] == 1.0:
                if n_kept < 4:
                    result[q, n_kept, 0] = temp_s[i]
                    result[q, n_kept, 1] = temp_d[i]
                    n_kept += 1

        counts[q] = n_kept

    return result, counts


@numba.njit(cache=True)
def _intersect_all_cells_nb(
    cylmap_a: NDArray,
    counts_a: NDArray,
    cylmap_b: NDArray,
    counts_b: NDArray,
) -> tuple[NDArray, NDArray]:
    """
    JIT-compiled full intersection of two cylindrical maps.

    Replaces the Python double-loop over all (L*, hue) cells in intersect_gamuts.
    For each cell, combines entries from both gamuts, sorts by distance
    (descending), streams through tracking the inside/outside state for each
    gamut, and records transitions — matching IntersectGamuts.m.

    Args:
        cylmap_a: First gamut map, shape (l_steps, h_steps, max_k, 2).
        counts_a: Hit counts for first gamut, shape (l_steps, h_steps).
        cylmap_b: Second gamut map, shape (l_steps, h_steps, max_k, 2).
        counts_b: Hit counts for second gamut, shape (l_steps, h_steps).

    Returns:
        cylmap_out: Intersected map, shape (l_steps, h_steps, max_k, 2).
        counts_out: Hit counts for intersection, shape (l_steps, h_steps).
    """
    l_steps = cylmap_a.shape[0]
    h_steps = cylmap_a.shape[1]
    max_k = cylmap_a.shape[2]

    cylmap_out = np.zeros((l_steps, h_steps, max_k, 2))
    counts_out = np.zeros((l_steps, h_steps), dtype=np.int64)

    # Pre-allocate combined buffer: at most max_k entries from each gamut
    combined = np.zeros((2 * max_k, 4))

    for p in range(l_steps):
        for q in range(h_steps):
            ca = counts_a[p, q]
            cb = counts_b[p, q]

            if ca == 0 or cb == 0:
                continue

            n = ca + cb

            # Fill combined: columns are [sign, distance, in_a, in_b]
            for i in range(ca):
                combined[i, 0] = cylmap_a[p, q, i, 0]
                combined[i, 1] = cylmap_a[p, q, i, 1]
                combined[i, 2] = cylmap_a[p, q, i, 0]
                combined[i, 3] = 0.0
            for i in range(cb):
                combined[ca + i, 0] = cylmap_b[p, q, i, 0]
                combined[ca + i, 1] = cylmap_b[p, q, i, 1]
                combined[ca + i, 2] = 0.0
                combined[ca + i, 3] = cylmap_b[p, q, i, 0]

            # Insertion sort by distance descending (n <= 2*max_k, typically 2)
            for i in range(1, n):
                k0 = combined[i, 0]
                k1 = combined[i, 1]
                k2 = combined[i, 2]
                k3 = combined[i, 3]
                j = i - 1
                while j >= 0 and combined[j, 1] < k1:
                    combined[j + 1, 0] = combined[j, 0]
                    combined[j + 1, 1] = combined[j, 1]
                    combined[j + 1, 2] = combined[j, 2]
                    combined[j + 1, 3] = combined[j, 3]
                    j -= 1
                combined[j + 1, 0] = k0
                combined[j + 1, 1] = k1
                combined[j + 1, 2] = k2
                combined[j + 1, 3] = k3

            # Stream through tracking inside state; record where min changes.
            # Equivalent to: changes = np.diff(np.minimum(cumsum_a, cumsum_b),
            #                                  prepend=0) != 0
            cs_a = 0.0
            cs_b = 0.0
            prev_inside = 0.0
            n_kept = 0

            for i in range(n):
                cs_a += combined[i, 2]
                cs_b += combined[i, 3]
                inside = cs_a if cs_a < cs_b else cs_b  # min(cs_a, cs_b)
                if inside != prev_inside and n_kept < max_k:
                    cylmap_out[p, q, n_kept, 0] = combined[i, 0]
                    cylmap_out[p, q, n_kept, 1] = combined[i, 1]
                    n_kept += 1
                prev_inside = inside

            counts_out[p, q] = n_kept

    return cylmap_out, counts_out


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
    cylmap, counts = _build_cylindrical_map(lab, triangles, l_steps, h_steps)
    return _integrate_cylmap(cylmap, counts, l_steps, h_steps)


def _build_cylindrical_map(
    lab: NDArray[np.floating],
    triangles: NDArray[np.integer],
    l_steps: int,
    h_steps: int,
) -> tuple[NDArray[np.floating], NDArray[np.integer]]:
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
        Tuple of (cylmap, counts) where:
        - cylmap: Dense intersection array, shape (l_steps, h_steps, _MAX_K, 2).
                  cylmap[p, q, j] = [sign, distance] for j-th intersection.
        - counts: Number of valid intersections per cell, shape (l_steps, h_steps).
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

    # Define L* and hue grids; precompute all ray directions: (h_steps, 2)
    # Note: MATLAB uses [sin(h), cos(h)] which puts 0° along the +b* axis
    L_edges = np.linspace(0, 100, l_steps + 1)
    hue_edges = np.linspace(0, 2 * np.pi, h_steps + 1)
    hue_mids = (hue_edges[:-1] + hue_edges[1:]) / 2
    all_dirs = np.column_stack([np.sin(hue_mids), np.cos(hue_mids)])

    # Dense output arrays (zeros = empty cells, no sentinel needed)
    cylmap = np.zeros((l_steps, h_steps, _MAX_K, 2))
    counts = np.zeros((l_steps, h_steps), dtype=np.int64)

    # For every step in L*
    for p in range(l_steps):
        L_mid = (L_edges[p] + L_edges[p + 1]) / 2

        # Find triangles that span this L* value
        ix = np.where((L_mid >= min_L) & (L_mid <= max_L))[0]

        if len(ix) == 0:
            continue  # counts[p, :] already 0

        # Get vertices of relevant triangles
        vert0 = tri_v0[ix]  # Shape (n_relevant, 3)
        vert1 = tri_v1[ix]
        vert2 = tri_v2[ix]

        # Ray origin at (0, 0, L_mid)
        orig = np.array([0.0, 0.0, L_mid])

        # Edge vectors and origin offset
        edge1 = vert1 - vert0
        edge2 = vert2 - vert0
        o = orig - vert0

        # Cross products (don't depend on ray direction)
        e2e1 = np.cross(edge2, edge1)  # (n_tri, 3)
        e2o = np.cross(edge2, o)       # (n_tri, 3)
        oe1 = np.cross(o, edge1)       # (n_tri, 3)

        # Determinant component that doesn't involve direction
        e2oe1 = np.sum(edge2 * oe1, axis=1)  # (n_tri,)

        # Drop the L* coordinate — ray direction always has dL*=0
        e2e1_2d = e2e1[:, :2]  # (n_tri, 2)
        e2o_2d = e2o[:, :2]
        oe1_2d = oe1[:, :2]

        # Batch all h_steps hue directions in one matrix multiply: (n_tri, h_steps)
        all_dets = e2e1_2d @ all_dirs.T    # (n_tri, h_steps)
        all_u_num = e2o_2d @ all_dirs.T    # (n_tri, h_steps)
        all_v_num = oe1_2d @ all_dirs.T    # (n_tri, h_steps)

        with np.errstate(divide='ignore', invalid='ignore'):
            all_idet = np.where(np.abs(all_dets) > 1e-10, 1.0 / all_dets, 0.0)

        all_u = all_u_num * all_idet        # (n_tri, h_steps)
        all_v = all_v_num * all_idet        # (n_tri, h_steps)
        all_t = e2oe1[:, None] * all_idet   # (n_tri, h_steps)

        # Validity masks: (n_tri, h_steps)
        valid_strict = (all_u >= 0) & (all_v >= 0) & (all_u + all_v <= 1) & (all_t >= 0)
        valid_loose = (all_u >= -0.001) & (all_v >= -0.001) & (all_u + all_v <= 1.001) & (all_t >= 0)

        # Per hue: use strict mask where it has any hits, loose otherwise
        has_strict = valid_strict.any(axis=0)  # (h_steps,)
        valid = np.where(has_strict[None, :], valid_strict, valid_loose)  # (n_tri, h_steps)

        # JIT-compiled inner loop: parity filter and population of dense output
        slice_result, slice_counts = _process_hue_loop_nb(
            np.ascontiguousarray(all_t),
            np.ascontiguousarray(all_idet),
            np.ascontiguousarray(valid),
        )
        cylmap[p] = slice_result
        counts[p] = slice_counts

    return cylmap, counts


def get_cylindrical_map(
    gamut: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> tuple[NDArray[np.floating], NDArray[np.integer]]:
    """
    Get the cylindrical map for a gamut, building and caching it if needed.

    Args:
        gamut: The gamut to map.
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        Tuple of (cylmap, counts) — see _build_cylindrical_map for shapes.
    """
    if gamut._cylindrical_map is None:
        cylmap, counts = _build_cylindrical_map(
            gamut.lab, gamut.triangles, l_steps, h_steps
        )
        gamut._cylindrical_map = cylmap
        gamut._cylmap_counts = counts
    return gamut._cylindrical_map, gamut._cylmap_counts  # type: ignore[return-value]


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

    # Build cylindrical maps for both gamuts (cached on the gamut objects)
    cylmap_a, counts_a = get_cylindrical_map(gamut_a, l_steps, h_steps)
    cylmap_b, counts_b = get_cylindrical_map(gamut_b, l_steps, h_steps)

    # Intersect the cylindrical maps (JIT-compiled double loop)
    cylmap_intersected, counts_intersected = _intersect_all_cells_nb(
        cylmap_a, counts_a, cylmap_b, counts_b,
    )

    # Create a Gamut-like object with the intersected map
    # We use empty arrays for lab/triangles since we only have cylmap
    intersected = Gamut(
        lab=np.empty((0, 3)),
        triangles=np.empty((0, 3), dtype=np.int32),
    )

    # Store the pre-computed cylindrical map and parameters
    intersected._cylindrical_map = cylmap_intersected
    intersected._cylmap_counts = counts_intersected
    intersected._cylmap_l_steps = l_steps
    intersected._cylmap_h_steps = h_steps

    # Pre-compute volume since we have the cylmap
    intersected._volume = _integrate_cylmap(
        cylmap_intersected, counts_intersected, l_steps, h_steps
    )

    return intersected


def compute_cylindrical_rings(
    gamut: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> NDArray[np.floating]:
    """
    Compute the C*_RSS gamut ring radii at each (L*, hue) grid point.

    This is a normative metric in IDMS v1.3, IEC 62977-3-5, and IEC 62906-6-1.
    The ring radius at L* level *l* and hue *h* is defined as:

    .. code-block:: none

        C*_RSS(l, h) = sqrt(2 × cumsum_l(V(l, h)) / Δh)

    where the cumulative sum is taken over L* from 0 upward, matching
    ``calcGamutRings.m`` from the MATLAB reference.

    Args:
        gamut: The gamut to compute rings for.
        l_steps: Number of L* bins (default 100).
        h_steps: Number of hue bins (default 360).

    Returns:
        Array of shape ``(l_steps, h_steps)`` containing C*_RSS values.
        Row 0 is the cumulative ring at the first L* level (~L*=1); the
        last row (index ``l_steps-1``) is the overall gamut outer ring at
        ~L*=100.
    """
    cylmap, counts = get_cylindrical_map(gamut, l_steps, h_steps)

    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]
    volmap = (
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask, axis=2)
        * dl * dh / 2
    )  # (l_steps, h_steps)

    cumvol = np.cumsum(volmap, axis=0)  # (l_steps, h_steps)
    r2 = 2.0 * cumvol / dh
    return np.sqrt(np.maximum(r2, 0.0))


def _integrate_cylmap(
    cylmap: NDArray[np.floating],
    counts: NDArray[np.integer],
    l_steps: int,
    h_steps: int,
) -> float:
    """
    Integrate a cylindrical map to compute volume.

    Args:
        cylmap: Dense array, shape (l_steps, h_steps, _MAX_K, 2).
        counts: Hit counts per cell, shape (l_steps, h_steps).
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        The integrated volume.
    """
    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    # Build mask to exclude unused slots: True where intersection j exists
    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]  # (l_steps, h_steps, _MAX_K)

    # cylmap[..., 0] = signs, cylmap[..., 1] = distances
    return float(
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask) * dl * dh / 2
    )


def _warmup_numba() -> None:
    """
    Trigger JIT compilation of Numba functions at import time.

    With cache=True, Numba writes compiled bytecode to __pycache__ on first
    run and loads it on subsequent runs.  Calling both functions here with
    minimal dummy arrays means the cache-load cost (~50 ms) is paid at import
    rather than during the first real computation.
    """
    _process_hue_loop_nb(
        np.zeros((1, 1)),
        np.zeros((1, 1)),
        np.zeros((1, 1), dtype=np.bool_),
    )
    _intersect_all_cells_nb(
        np.zeros((1, 1, _MAX_K, 2)),
        np.zeros((1, 1), dtype=np.int64),
        np.zeros((1, 1, _MAX_K, 2)),
        np.zeros((1, 1), dtype=np.int64),
    )


_warmup_numba()
