"""
Gamut volume computation via cylindrical integration.

The volume is computed by mapping the gamut surface to cylindrical
coordinates (L*, C*, h) using ray-triangle intersection, then integrating.

This implementation matches the algorithm in gamut-volume-m (MATLAB)
which is the reference implementation for IEC and ICDM standards.

## Cylindrical map storage format

The cylmap is stored on each Gamut object in a packed variable-length format:

    counts:  uint8  (l_steps, h_steps)        — post-filter intersection count per cell
    chroma:  float32 [sum(counts)]             — distances only, outside-in per cell,
                                                 cells in row-major order
    offsets: int32  [l_steps × h_steps]       — prefix-sum of counts for O(1) cell access

**Implicit sign convention:** entries are stored in outside-in order (descending
distance from the L* axis).  The parity filter guarantees the outermost crossing
always faces outward (+1).  Therefore:

    sign = +1  if position-within-cell is even   (outward / exit)
    sign = −1  if position-within-cell is odd    (inward / entry)

No sign column is stored.  Callers reconstruct signs from position.

For computation (volume, rings, intersection), the packed format is unpacked
on demand to a dense float64 array of shape (l_steps, h_steps, max_k, 2)
where max_k = counts.max() — data-driven, not a fixed constant.  This array
stores explicit [sign, distance] pairs and is consumed by the existing
vectorised NumPy operations unchanged.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numba
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from cielab_gamut_tools.gamut import Gamut


@numba.njit(cache=True)
def _process_hue_loop_nb(
    all_t: NDArray,
    all_idet: NDArray,
    valid: NDArray,
) -> tuple[NDArray, NDArray, int]:
    """
    JIT-compiled inner hue loop: collect, sort, parity-filter, and pack intersections.

    For each hue angle, extracts valid ray-triangle intersections, sorts
    ascending (inside-out), applies the parity filter (matching MATLAB
    cielab_cylindrical_map.m), then reverses the kept entries to outside-in
    order before writing to the flat output buffer.

    The working buffer is sized to h_steps × n_tri — the absolute maximum
    possible before the parity filter — so no truncation occurs.

    Args:
        all_t: Intersection distances, shape (n_tri, h_steps), float64.
        all_idet: Inverse determinants (sign encodes surface orientation),
            shape (n_tri, h_steps), float64.
        valid: Boolean hit mask, shape (n_tri, h_steps).

    Returns:
        chroma_buf: float32 flat buffer, length h_steps × n_tri.  First
            n_written entries are valid; cells packed in hue order, each
            cell's entries in outside-in (descending t) order.
        counts: Number of parity-filtered intersections per hue, shape
            (h_steps,), int64.
        n_written: Total entries written to chroma_buf.
    """
    n_tri = all_t.shape[0]
    h_steps = all_t.shape[1]

    # Pre-allocate: absolute worst case is n_tri hits per hue angle (before
    # parity filter).  After filtering the actual count is almost always 1–4.
    chroma_buf = np.zeros(h_steps * n_tri, dtype=np.float32)
    counts = np.zeros(h_steps, dtype=np.int64)
    n_written = 0

    temp_s = np.empty(n_tri)    # signs
    temp_d = np.empty(n_tri)    # distances
    cs_right = np.empty(n_tri)  # cumulative sum from right for parity filter

    for q in range(h_steps):
        # Collect valid intersections for this hue angle
        k = 0
        for i in range(n_tri):
            if valid[i, q]:
                idet_val = all_idet[i, q]
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

        # Insertion sort ascending (inside-out: smallest t first)
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

        # Write kept distances ascending into chroma_buf, then reverse in-place
        # so the cell's entries end up in outside-in (descending t) order.
        cell_start = n_written
        for i in range(k):
            if cs_right[i] * 2.0 - temp_s[i] == 1.0:
                chroma_buf[n_written] = temp_d[i]
                n_written += 1

        n_kept = n_written - cell_start

        # Reverse for outside-in ordering
        lo = cell_start
        hi = n_written - 1
        while lo < hi:
            tmp = chroma_buf[lo]
            chroma_buf[lo] = chroma_buf[hi]
            chroma_buf[hi] = tmp
            lo += 1
            hi -= 1

        counts[q] = n_kept

    return chroma_buf, counts, n_written


@numba.njit(cache=True)
def _intersect_all_cells_nb(
    cylmap_a: NDArray,
    counts_a: NDArray,
    cylmap_b: NDArray,
    counts_b: NDArray,
) -> tuple[NDArray, NDArray]:
    """
    JIT-compiled full intersection of two cylindrical maps.

    Takes dense (l_steps, h_steps, max_k, 2) inputs; the output depth is
    max_k_a + max_k_b, which is an absolute upper bound on any cell's
    intersection count, so no truncation is possible.

    Args:
        cylmap_a: First gamut map, shape (l_steps, h_steps, max_k_a, 2).
        counts_a: Hit counts for first gamut, shape (l_steps, h_steps), int64.
        cylmap_b: Second gamut map, shape (l_steps, h_steps, max_k_b, 2).
        counts_b: Hit counts for second gamut, shape (l_steps, h_steps), int64.

    Returns:
        cylmap_out: Intersected map, shape (l_steps, h_steps, max_k_a+max_k_b, 2).
        counts_out: Hit counts for intersection, shape (l_steps, h_steps), int64.
    """
    l_steps = cylmap_a.shape[0]
    h_steps = cylmap_a.shape[1]
    max_k_a = cylmap_a.shape[2]
    max_k_b = cylmap_b.shape[2]
    max_k_out = max_k_a + max_k_b

    cylmap_out = np.zeros((l_steps, h_steps, max_k_out, 2))
    counts_out = np.zeros((l_steps, h_steps), dtype=np.int64)

    # Combined buffer: at most max_k_a + max_k_b entries from both gamuts
    combined = np.zeros((max_k_a + max_k_b, 4))

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

            # Insertion sort descending by distance (outside-in)
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

            # Stream outside-in tracking inside state; record where min(cs_a, cs_b) changes.
            cs_a = 0.0
            cs_b = 0.0
            prev_inside = 0.0
            n_kept = 0

            for i in range(n):
                cs_a += combined[i, 2]
                cs_b += combined[i, 3]
                inside = cs_a if cs_a < cs_b else cs_b
                if inside != prev_inside:
                    cylmap_out[p, q, n_kept, 0] = combined[i, 0]
                    cylmap_out[p, q, n_kept, 1] = combined[i, 1]
                    n_kept += 1
                prev_inside = inside

            counts_out[p, q] = n_kept

    return cylmap_out, counts_out


# ---------------------------------------------------------------------------
# Pack / unpack helpers
# ---------------------------------------------------------------------------

def _make_offsets(flat_counts: NDArray[np.integer]) -> NDArray[np.int32]:
    """Prefix-sum offset array: offsets[i] = starting index in chroma for cell i."""
    return np.concatenate([[0], np.cumsum(flat_counts)[:-1]]).astype(np.int32)


def _pack_cylmap(
    cylmap: NDArray[np.floating],
    counts: NDArray[np.integer],
) -> tuple[NDArray[np.float32], NDArray[np.int32]]:
    """
    Pack a dense (l_steps, h_steps, max_k, 2) cylmap to (chroma, offsets).

    Only distances (column 1) are stored; signs are implicit from position
    (even index within cell = outward = +1, odd = inward = -1).  Entries
    are in outside-in order, matching what _process_hue_loop_nb produces.

    Args:
        cylmap: Dense array, shape (l_steps, h_steps, max_k, 2).
        counts: Valid entry counts per cell, shape (l_steps, h_steps).

    Returns:
        chroma: float32 flat array of distances, length sum(counts).
        offsets: int32 prefix-sum array, length l_steps * h_steps.
    """
    l_steps, h_steps = counts.shape
    flat_counts = counts.ravel().astype(np.int64)
    n_cells = l_steps * h_steps
    total = int(flat_counts.sum())

    offsets = _make_offsets(flat_counts)

    if total == 0:
        return np.zeros(0, dtype=np.float32), offsets

    cylmap_flat = cylmap.reshape(n_cells, -1, 2)

    # Build (cell_index, within_cell_index) for every element in chroma
    cell_of_element = np.repeat(np.arange(n_cells), flat_counts)
    cum_counts = np.concatenate([[0], np.cumsum(flat_counts)])
    within_cell = np.arange(total) - np.repeat(cum_counts[:-1], flat_counts)

    chroma = cylmap_flat[cell_of_element, within_cell, 1].astype(np.float32)
    return chroma, offsets


def _unpack_cylmap(
    counts: NDArray[np.integer],
    chroma: NDArray[np.float32],
    offsets: NDArray[np.int32],
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """
    Unpack stored (counts, chroma, offsets) to a dense (l, h, max_k, 2) array.

    max_k = counts.max() — data-driven, no fixed constant.  Signs are
    reconstructed from position: even = +1 (outward), odd = -1 (inward).

    Args:
        counts: uint8 (l_steps, h_steps).
        chroma: float32 flat distances array.
        offsets: int32 prefix-sum array, length l_steps * h_steps.

    Returns:
        cylmap: float64 (l_steps, h_steps, max_k, 2) with [sign, distance].
        counts_int64: counts cast to int64 for JIT compatibility.
    """
    l_steps, h_steps = counts.shape
    max_k = int(counts.max()) if counts.size > 0 and int(counts.max()) > 0 else 1
    n_cells = l_steps * h_steps
    flat_counts = counts.ravel().astype(np.int64)
    total = len(chroma)

    cylmap = np.zeros((n_cells, max_k, 2))

    if total > 0:
        # Sign channel: even position within cell = +1, odd = -1
        k_idx = np.arange(max_k)
        k_mask = k_idx[None, :] < flat_counts[:, None]        # (n_cells, max_k)
        sign_pattern = np.where(k_idx % 2 == 0, 1.0, -1.0)
        cylmap[:, :, 0] = np.where(k_mask, sign_pattern[None, :], 0.0)

        # Distance channel: scatter chroma into correct (cell, within_cell) slots
        cell_of_element = np.repeat(np.arange(n_cells), flat_counts)
        cum_counts = np.concatenate([[0], np.cumsum(flat_counts)])
        within_cell = np.arange(total) - np.repeat(cum_counts[:-1], flat_counts)
        cylmap[cell_of_element, within_cell, 1] = chroma

    return cylmap.reshape(l_steps, h_steps, max_k, 2), flat_counts.reshape(l_steps, h_steps)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def compute_volume(
    lab: NDArray[np.floating],
    triangles: NDArray[np.integer],
    l_steps: int = 100,
    h_steps: int = 360,
) -> float:
    """
    Compute gamut volume using cylindrical integration.

    Args:
        lab: CIELab coordinates of surface vertices, shape (N, 3).
        triangles: Triangle vertex indices, shape (M, 3).
        l_steps: Number of L* discretization steps (default 100).
        h_steps: Number of hue angle steps (default 360).

    Returns:
        The gamut volume in CIELab cubic units.
    """
    counts, chroma, offsets = _build_cylindrical_map(lab, triangles, l_steps, h_steps)
    cylmap, counts_int = _unpack_cylmap(counts, chroma, offsets)
    return _integrate_cylmap(cylmap, counts_int, l_steps, h_steps)


def _build_cylindrical_map(
    lab: NDArray[np.floating],
    triangles: NDArray[np.integer],
    l_steps: int,
    h_steps: int,
) -> tuple[NDArray[np.uint8], NDArray[np.float32], NDArray[np.int32]]:
    """
    Build cylindrical map using ray-triangle intersection.

    For each (L*, hue) grid cell, shoots a ray from the L* axis and finds
    all intersections with the triangulated gamut surface.

    This matches the algorithm in CIEtools/cielab_cylindrical_map.m.

    Args:
        lab: CIELab coordinates, shape (N, 3) as [L*, a*, b*].
        triangles: Triangle indices, shape (M, 3).
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        counts:  uint8 (l_steps, h_steps) — parity-filtered intersection count.
        chroma:  float32 [sum(counts)] — distances, outside-in per cell, row-major.
        offsets: int32 [l_steps * h_steps] — prefix-sum for O(1) cell access.
    """
    # Reorder to [a*, b*, L*] to match MATLAB's Z matrix
    Z = lab[:, [1, 2, 0]]

    tri_v0 = Z[triangles[:, 0]]
    tri_v1 = Z[triangles[:, 1]]
    tri_v2 = Z[triangles[:, 2]]

    min_L = np.minimum(np.minimum(tri_v0[:, 2], tri_v1[:, 2]), tri_v2[:, 2])
    max_L = np.maximum(np.maximum(tri_v0[:, 2], tri_v1[:, 2]), tri_v2[:, 2])

    # L* and hue grids; ray directions: (h_steps, 2)
    # [sin(h), cos(h)] puts 0° along +b* axis, matching MATLAB
    L_edges = np.linspace(0, 100, l_steps + 1)
    hue_edges = np.linspace(0, 2 * np.pi, h_steps + 1)
    hue_mids = (hue_edges[:-1] + hue_edges[1:]) / 2
    all_dirs = np.column_stack([np.sin(hue_mids), np.cos(hue_mids)])

    counts = np.zeros((l_steps, h_steps), dtype=np.uint8)
    chroma_parts: list[NDArray[np.float32]] = []

    for p in range(l_steps):
        L_mid = (L_edges[p] + L_edges[p + 1]) / 2

        ix = np.where((L_mid >= min_L) & (L_mid <= max_L))[0]
        if len(ix) == 0:
            continue

        vert0 = tri_v0[ix]
        vert1 = tri_v1[ix]
        vert2 = tri_v2[ix]

        orig = np.array([0.0, 0.0, L_mid])
        edge1 = vert1 - vert0
        edge2 = vert2 - vert0
        o = orig - vert0

        e2e1 = np.cross(edge2, edge1)
        e2o = np.cross(edge2, o)
        oe1 = np.cross(o, edge1)
        e2oe1 = np.sum(edge2 * oe1, axis=1)

        e2e1_2d = e2e1[:, :2]
        e2o_2d = e2o[:, :2]
        oe1_2d = oe1[:, :2]

        all_dets = e2e1_2d @ all_dirs.T
        all_u_num = e2o_2d @ all_dirs.T
        all_v_num = oe1_2d @ all_dirs.T

        with np.errstate(divide='ignore', invalid='ignore'):
            all_idet = np.where(np.abs(all_dets) > 1e-10, 1.0 / all_dets, 0.0)

        all_u = all_u_num * all_idet
        all_v = all_v_num * all_idet
        all_t = e2oe1[:, None] * all_idet

        valid_strict = (all_u >= 0) & (all_v >= 0) & (all_u + all_v <= 1) & (all_t >= 0)
        valid_loose = (
            (all_u >= -0.001) & (all_v >= -0.001) & (all_u + all_v <= 1.001) & (all_t >= 0)
        )

        has_strict = valid_strict.any(axis=0)
        valid = np.where(has_strict[None, :], valid_strict, valid_loose)

        chroma_slice, slice_counts, n_written = _process_hue_loop_nb(
            np.ascontiguousarray(all_t),
            np.ascontiguousarray(all_idet),
            np.ascontiguousarray(valid),
        )

        if int(slice_counts.max()) > 255:
            raise RuntimeError(
                f"Intersection count {int(slice_counts.max())} at L* slice {p} "
                "exceeds uint8 maximum (255). This is geometrically impossible "
                "for any real gamut surface."
            )

        counts[p] = slice_counts.astype(np.uint8)

        if n_written > 0:
            chroma_parts.append(chroma_slice[:n_written].copy())

    chroma = (
        np.concatenate(chroma_parts).astype(np.float32)
        if chroma_parts
        else np.zeros(0, dtype=np.float32)
    )
    offsets = _make_offsets(counts.ravel().astype(np.int64))

    _check_cylmap_parity(counts)

    return counts, chroma, offsets


def _check_cylmap_parity(counts: NDArray[np.integer]) -> None:
    """
    Verify the per-slice parity invariant.

    Within each L* slice every ray originates from the same point (L*, 0, 0),
    which is either inside or outside the gamut cross-section at that level.
    All 360 intersection counts in a slice must therefore share the same parity.
    A mix of odd and even counts means a gap or self-intersection in the
    tessellation.
    """
    l_steps = counts.shape[0]
    for p in range(l_steps):
        parities = counts[p] % 2   # 0 or 1 per hue
        if int(parities.max()) != int(parities.min()):
            warnings.warn(
                f"Parity violation at L* slice {p}: rays yielded mixed odd/even "
                "intersection counts.  This may indicate a gap or self-intersection "
                "in the gamut surface tessellation.  Volume result may be slightly "
                "inaccurate at this slice (MATLAB silently ignores this condition).",
                stacklevel=4,
            )


# ---------------------------------------------------------------------------
# Cache / retrieve
# ---------------------------------------------------------------------------

def get_cylindrical_map(
    gamut: "Gamut",
    l_steps: int = 100,
    h_steps: int = 360,
) -> tuple[NDArray[np.floating], NDArray[np.int64]]:
    """
    Get the cylindrical map for a gamut, building and caching if needed.

    The packed (counts, chroma, offsets) format is cached on the gamut object.
    This function unpacks to a dense (l_steps, h_steps, max_k, 2) array on
    each call — the unpack is O(sum(counts)) and takes < 1 ms in practice.

    Args:
        gamut: The gamut to map.
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        cylmap: float64 (l_steps, h_steps, max_k, 2) with [sign, distance].
        counts: int64 (l_steps, h_steps).
    """
    if gamut._cylmap_counts is None:
        counts, chroma, offsets = _build_cylindrical_map(
            gamut.lab, gamut.triangles, l_steps, h_steps
        )
        gamut._cylmap_counts = counts
        gamut._cylmap_chroma = chroma
        gamut._cylmap_offsets = offsets

    return _unpack_cylmap(
        gamut._cylmap_counts,   # type: ignore[arg-type]
        gamut._cylmap_chroma,   # type: ignore[arg-type]
        gamut._cylmap_offsets,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Intersection
# ---------------------------------------------------------------------------

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
        A new Gamut representing the intersection.  It has a pre-computed
        cylindrical map but no surface tessellation; volume() and plot_rings()
        work, plot_surface() does not.
    """
    from cielab_gamut_tools.gamut import Gamut

    if hasattr(gamut_a, "gamut"):
        gamut_a = gamut_a.gamut
    if hasattr(gamut_b, "gamut"):
        gamut_b = gamut_b.gamut

    cylmap_a, counts_a = get_cylindrical_map(gamut_a, l_steps, h_steps)
    cylmap_b, counts_b = get_cylindrical_map(gamut_b, l_steps, h_steps)

    cylmap_int, counts_int = _intersect_all_cells_nb(
        cylmap_a, counts_a, cylmap_b, counts_b,
    )

    intersected = Gamut(
        lab=np.empty((0, 3)),
        triangles=np.empty((0, 3), dtype=np.int32),
    )

    chroma_int, offsets_int = _pack_cylmap(cylmap_int, counts_int)
    intersected._cylmap_counts = counts_int.astype(np.uint8)
    intersected._cylmap_chroma = chroma_int
    intersected._cylmap_offsets = offsets_int
    intersected._volume = _integrate_cylmap(cylmap_int, counts_int, l_steps, h_steps)

    return intersected


# ---------------------------------------------------------------------------
# Integration / rings
# ---------------------------------------------------------------------------

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
    """
    cylmap, counts = get_cylindrical_map(gamut, l_steps, h_steps)

    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]
    volmap = (
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask, axis=2)
        * dl * dh / 2
    )

    cumvol = np.cumsum(volmap, axis=0)
    r2 = 2.0 * cumvol / dh
    return np.sqrt(np.maximum(r2, 0.0))


def _integrate_cylmap(
    cylmap: NDArray[np.floating],
    counts: NDArray[np.integer],
    l_steps: int,
    h_steps: int,
) -> float:
    """
    Integrate a dense cylindrical map to compute volume.

    Args:
        cylmap: Dense array, shape (l_steps, h_steps, max_k, 2).
        counts: Hit counts per cell, shape (l_steps, h_steps).
        l_steps: Number of L* bins.
        h_steps: Number of hue bins.

    Returns:
        The integrated volume.
    """
    dh = 2 * np.pi / h_steps
    dl = 100.0 / l_steps

    k_range = np.arange(cylmap.shape[2])
    mask = k_range[None, None, :] < counts[:, :, None]

    return float(
        np.sum(cylmap[:, :, :, 0] * cylmap[:, :, :, 1] ** 2 * mask) * dl * dh / 2
    )


# ---------------------------------------------------------------------------
# Numba warm-up
# ---------------------------------------------------------------------------

def _warmup_numba() -> None:
    """
    Trigger JIT compilation of Numba functions at import time.

    With cache=True Numba writes compiled bytecode to __pycache__ on the
    first run and reloads it on subsequent runs.  Calling both functions here
    with minimal dummy arrays means the cache-load cost (~50 ms) is paid at
    import rather than during the first real computation.
    """
    _process_hue_loop_nb(
        np.zeros((1, 1)),
        np.zeros((1, 1)),
        np.zeros((1, 1), dtype=np.bool_),
    )
    _intersect_all_cells_nb(
        np.zeros((1, 1, 1, 2)),
        np.zeros((1, 1), dtype=np.int64),
        np.zeros((1, 1, 1, 2)),
        np.zeros((1, 1), dtype=np.int64),
    )


_warmup_numba()
