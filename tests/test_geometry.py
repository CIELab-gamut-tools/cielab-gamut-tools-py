"""
Tests for geometry functions (tesselation and volume calculation).
"""

import numpy as np
import pytest

from cielab_gamut_tools.geometry.tesselation import make_tesselation


class TestMakeTesselation:
    """Tests for RGB cube tesselation."""

    def test_returns_correct_types(self):
        """Should return triangles and vertices arrays."""
        triangles, vertices = make_tesselation()
        assert isinstance(triangles, np.ndarray)
        assert isinstance(vertices, np.ndarray)

    def test_vertices_on_cube_surface(self):
        """All vertices should be on the RGB cube surface."""
        triangles, vertices = make_tesselation()

        # Each vertex should have at least one coordinate at 0 or 1
        on_surface = np.any(
            (vertices == 0) | (vertices == 1), axis=1
        )
        assert np.all(on_surface), "All vertices should be on cube surface"

    def test_vertices_in_unit_cube(self):
        """All vertices should be within [0, 1] range."""
        triangles, vertices = make_tesselation()

        assert np.all(vertices >= 0), "Vertices should be >= 0"
        assert np.all(vertices <= 1), "Vertices should be <= 1"

    def test_triangles_reference_valid_vertices(self):
        """Triangle indices should reference valid vertices."""
        triangles, vertices = make_tesselation()

        assert np.all(triangles >= 0)
        assert np.all(triangles < len(vertices))

    def test_triangles_have_three_vertices(self):
        """Each triangle should have exactly 3 vertex indices."""
        triangles, vertices = make_tesselation()
        assert triangles.shape[1] == 3

    def test_resolution_affects_count(self):
        """Higher resolution should produce more vertices and triangles."""
        tri_low, vert_low = make_tesselation(resolution=5)
        tri_high, vert_high = make_tesselation(resolution=10)

        assert len(vert_high) > len(vert_low)
        assert len(tri_high) > len(tri_low)

    def test_covers_all_faces(self):
        """Tesselation should cover all 6 faces of the cube."""
        triangles, vertices = make_tesselation()

        # Check that we have vertices on each face
        faces = [
            vertices[:, 0] == 0,  # R=0
            vertices[:, 0] == 1,  # R=1
            vertices[:, 1] == 0,  # G=0
            vertices[:, 1] == 1,  # G=1
            vertices[:, 2] == 0,  # B=0
            vertices[:, 2] == 1,  # B=1
        ]

        for i, face_mask in enumerate(faces):
            assert np.any(face_mask), f"Face {i} should have vertices"

    def test_corners_present(self):
        """All 8 cube corners should be present in vertices."""
        triangles, vertices = make_tesselation()

        corners = [
            [0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1],
            [1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1],
        ]

        for corner in corners:
            distances = np.linalg.norm(vertices - corner, axis=1)
            assert np.min(distances) < 0.01, f"Corner {corner} should be present"


class TestVolumeComputation:
    """Tests for gamut volume calculation."""

    def test_srgb_reference_volume(self):
        """
        sRGB synthetic gamut should have volume ~830,732.

        This is a known reference value from the MATLAB implementation.
        Allow 1% tolerance for numerical differences.
        """
        from cielab_gamut_tools.synthetic import SyntheticGamut

        srgb = SyntheticGamut.srgb()
        volume = srgb.volume()

        assert volume == pytest.approx(830732, rel=0.01)

    def test_volume_is_positive(self):
        """Gamut volume should always be positive."""
        from cielab_gamut_tools.synthetic import SyntheticGamut

        srgb = SyntheticGamut.srgb()
        assert srgb.volume() > 0

    def test_larger_gamut_larger_volume(self):
        """BT.2020 should have larger volume than sRGB."""
        from cielab_gamut_tools.synthetic import SyntheticGamut

        srgb = SyntheticGamut.srgb()
        bt2020 = SyntheticGamut.bt2020()

        assert bt2020.volume() > srgb.volume()
