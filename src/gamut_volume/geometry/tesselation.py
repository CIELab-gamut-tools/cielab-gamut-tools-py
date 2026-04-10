"""
RGB cube surface tesselation.

Generates a triangulated mesh of the RGB cube surface for volume
computation and visualization.

This implementation matches the algorithm in gamut-volume-m (MATLAB)
which is the reference implementation for IEC and ICDM standards.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def make_tesselation(
    resolution: int = 10,
) -> tuple[NDArray[np.integer], NDArray[np.floating]]:
    """
    Generate a tesselation of the RGB cube surface.

    Creates a triangulated mesh covering all six faces of the unit RGB cube.
    Triangle winding is consistent so that surface normals point outward.

    This matches the algorithm in CIEtools/make_tesselation.m

    Args:
        resolution: Number of subdivisions per edge (default 10).
            The MATLAB default uses gsv = 0:0.1:1, giving 11 values
            and 10 subdivisions.

    Returns:
        A tuple of (triangles, vertices) where:
        - triangles: Triangle vertex indices, shape (M, 3)
        - vertices: RGB coordinates of vertices, shape (N, 3)
    """
    # Grid values along each edge (matches MATLAB's gsv = 0:0.1:1 for resolution=10)
    gsv = np.linspace(0, 1, resolution + 1)
    n = len(gsv)  # Number of grid points per edge

    # Build the reference RGB table
    # Create 2D grid of J, K values
    # Use column-major (Fortran) order to match MATLAB's flattening
    J, K = np.meshgrid(gsv, gsv)
    J = J.flatten('F')  # Column-major like MATLAB's (:)
    K = K.flatten('F')

    lower = np.zeros_like(J)
    upper = np.ones_like(J)

    # Build vertices for all 6 faces
    # MATLAB ordering ensures consistent triangle winding:
    # - Bottom surfaces (value=0): order is rotations of [Lower, J, K]
    # - Top surfaces (value=1): order is rotations of [Upper, K, J]
    # Note the reversal of J,K to K,J for top vs bottom - this ensures
    # outward-pointing normals on all faces.
    vertices = np.vstack([
        np.column_stack([lower, J, K]),  # R=0 face
        np.column_stack([K, lower, J]),  # G=0 face
        np.column_stack([J, K, lower]),  # B=0 face
        np.column_stack([upper, K, J]),  # R=1 face
        np.column_stack([J, upper, K]),  # G=1 face
        np.column_stack([K, J, upper]),  # B=1 face
    ])

    # Build triangulation
    # Each face has (n-1)^2 quads, each quad has 2 triangles
    # Total: 6 faces * (n-1)^2 * 2 = 12*(n-1)^2 triangles
    num_triangles = 12 * (n - 1) ** 2
    triangles = np.zeros((num_triangles, 3), dtype=np.int32)

    idx = 0
    for s in range(6):  # 6 faces
        for q in range(n - 1):
            for p in range(n - 1):
                # Base index for this quad
                m = n * n * s + n * q + p

                # Two triangles per quad, with consistent winding
                # Consider quad vertices: A=m, B=m+n, C=m+1, D=m+n+1
                #   A---B      Triangle 1: A-B-C (indices m, m+n, m+1)
                #   |   |      Triangle 2: B-D-C (indices m+n, m+n+1, m+1)
                #   C---D      Both triangles have same rotation (clockwise)
                triangles[idx] = [m, m + n, m + 1]
                triangles[idx + 1] = [m + n, m + n + 1, m + 1]
                idx += 2

    return triangles, vertices.astype(np.float64)
