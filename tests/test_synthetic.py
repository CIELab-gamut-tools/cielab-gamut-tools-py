"""
Tests for synthetic gamut generation.
"""

import numpy as np
import pytest

from gamut_volume.synthetic import (
    SyntheticGamut,
    _build_rgb_to_xyz_matrix,
    SRGB_PRIMARIES,
    D65_WHITE,
)


class TestRgbToXyzMatrix:
    """Tests for RGB to XYZ matrix construction."""

    def test_white_maps_to_white(self):
        """RGB white (1,1,1) should map to the white point XYZ."""
        from gamut_volume.colorspace.lab import xy_to_XYZ

        M = _build_rgb_to_xyz_matrix(SRGB_PRIMARIES, D65_WHITE)
        rgb_white = np.array([1.0, 1.0, 1.0])
        xyz_white = rgb_white @ M.T

        expected = xy_to_XYZ(D65_WHITE)

        np.testing.assert_allclose(xyz_white, expected, rtol=1e-5)

    def test_black_maps_to_black(self):
        """RGB black (0,0,0) should map to XYZ (0,0,0)."""
        M = _build_rgb_to_xyz_matrix(SRGB_PRIMARIES, D65_WHITE)
        rgb_black = np.array([0.0, 0.0, 0.0])
        xyz_black = rgb_black @ M.T

        np.testing.assert_allclose(xyz_black, [0, 0, 0], atol=1e-10)

    def test_red_primary(self):
        """RGB red (1,0,0) should map to red primary XYZ."""
        from gamut_volume.colorspace.lab import xy_to_XYZ

        M = _build_rgb_to_xyz_matrix(SRGB_PRIMARIES, D65_WHITE)
        rgb_red = np.array([1.0, 0.0, 0.0])
        xyz_red = rgb_red @ M.T

        # The chromaticity should match the red primary
        xyz_sum = np.sum(xyz_red)
        if xyz_sum > 0:
            xy_result = xyz_red[:2] / xyz_sum
            np.testing.assert_allclose(xy_result, SRGB_PRIMARIES[0], rtol=1e-3)

    def test_matrix_shape(self):
        """Matrix should be 3x3."""
        M = _build_rgb_to_xyz_matrix(SRGB_PRIMARIES, D65_WHITE)
        assert M.shape == (3, 3)


class TestSyntheticGamutRgbToXyz:
    """Tests for SyntheticGamut RGB to XYZ conversion."""

    def test_srgb_red_chromaticity(self):
        """sRGB red should have correct chromaticity."""
        srgb = SyntheticGamut.srgb()

        # Linear RGB red
        rgb_red = np.array([[1.0, 0.0, 0.0]])
        xyz = srgb._rgb_to_xyz(rgb_red)

        # Check chromaticity
        xyz_sum = np.sum(xyz[0])
        xy = xyz[0, :2] / xyz_sum

        np.testing.assert_allclose(xy, SRGB_PRIMARIES[0], rtol=1e-3)

    def test_gamma_applied(self):
        """Gamma should be applied to RGB values."""
        # Create two gamuts with different gamma
        g22 = SyntheticGamut(SRGB_PRIMARIES, D65_WHITE, gamma=2.2)
        g10 = SyntheticGamut(SRGB_PRIMARIES, D65_WHITE, gamma=1.0)

        # Mid-gray RGB
        rgb = np.array([[0.5, 0.5, 0.5]])

        xyz_22 = g22._rgb_to_xyz(rgb)
        xyz_10 = g10._rgb_to_xyz(rgb)

        # Gamma 2.2 should produce darker (lower Y) result
        assert xyz_22[0, 1] < xyz_10[0, 1]

    def test_batch_conversion(self):
        """Test converting multiple RGB values at once."""
        srgb = SyntheticGamut.srgb()

        rgb = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])

        xyz = srgb._rgb_to_xyz(rgb)

        assert xyz.shape == (5, 3)
        # Black should be zero
        np.testing.assert_allclose(xyz[0], [0, 0, 0], atol=1e-10)
        # All XYZ values should be non-negative
        assert np.all(xyz >= -1e-10)
