"""
Tests for colorspace conversion functions.
"""

import numpy as np
import pytest

from cielab_gamut_tools.colorspace.lab import (
    D50_WHITE_XYZ,
    lab_to_xyz,
    xy_to_XYZ,
    xyz_to_lab,
)
from cielab_gamut_tools.colorspace.adaptation import adapt_d65_to_d50, chromatic_adaptation
from cielab_gamut_tools.colorspace.srgb import srgb_gamma_decode, srgb_gamma_encode


class TestXyzToLab:
    """Tests for XYZ to CIELab conversion."""

    def test_d50_white_gives_l100(self):
        """D50 white point should convert to L*=100, a*=0, b*=0."""
        lab = xyz_to_lab(D50_WHITE_XYZ)
        assert lab[0] == pytest.approx(100.0, abs=0.001)
        assert lab[1] == pytest.approx(0.0, abs=0.001)
        assert lab[2] == pytest.approx(0.0, abs=0.001)

    def test_black_gives_l0(self):
        """Black (XYZ=0) should give L*=0."""
        lab = xyz_to_lab(np.array([0.0, 0.0, 0.0]))
        assert lab[0] == pytest.approx(0.0, abs=0.001)

    def test_batch_conversion(self):
        """Test conversion of multiple points at once."""
        xyz = np.array([
            [0.0, 0.0, 0.0],  # Black
            D50_WHITE_XYZ,     # White
        ])
        lab = xyz_to_lab(xyz)
        assert lab.shape == (2, 3)
        assert lab[0, 0] == pytest.approx(0.0, abs=0.001)
        assert lab[1, 0] == pytest.approx(100.0, abs=0.001)

    def test_known_red(self):
        """Test a known red color value."""
        # sRGB red (1,0,0) in XYZ (D50 adapted) approximately
        # These values should give a red color in Lab
        xyz_red = np.array([0.4360, 0.2225, 0.0139])
        lab = xyz_to_lab(xyz_red)
        # Red should have positive a* and positive/small b*
        assert lab[0] > 0  # L* > 0
        assert lab[1] > 0  # a* positive (toward red)


class TestLabToXyz:
    """Tests for CIELab to XYZ conversion."""

    def test_roundtrip_white(self):
        """White should round-trip correctly."""
        lab = xyz_to_lab(D50_WHITE_XYZ)
        xyz_back = lab_to_xyz(lab)
        np.testing.assert_allclose(xyz_back, D50_WHITE_XYZ, rtol=1e-5)

    def test_roundtrip_black(self):
        """Black should round-trip correctly."""
        xyz_black = np.array([0.0, 0.0, 0.0])
        lab = xyz_to_lab(xyz_black)
        xyz_back = lab_to_xyz(lab)
        np.testing.assert_allclose(xyz_back, xyz_black, atol=1e-10)

    def test_roundtrip_random(self):
        """Random XYZ values should round-trip correctly."""
        rng = np.random.default_rng(42)
        xyz = rng.random((100, 3)) * np.array([0.95, 1.0, 1.09])
        lab = xyz_to_lab(xyz)
        xyz_back = lab_to_xyz(lab)
        np.testing.assert_allclose(xyz_back, xyz, rtol=1e-5)


class TestXyToXYZ:
    """Tests for xy chromaticity to XYZ conversion."""

    def test_d65_white(self):
        """D65 white point xy should give expected XYZ."""
        d65_xy = np.array([0.31272, 0.32903])
        xyz = xy_to_XYZ(d65_xy, Y=1.0)
        # X = x/y, Z = (1-x-y)/y
        expected_X = d65_xy[0] / d65_xy[1]
        expected_Z = (1 - d65_xy[0] - d65_xy[1]) / d65_xy[1]
        assert xyz[0] == pytest.approx(expected_X, rel=1e-5)
        assert xyz[1] == pytest.approx(1.0, rel=1e-5)
        assert xyz[2] == pytest.approx(expected_Z, rel=1e-5)

    def test_with_luminance(self):
        """Test with non-unity luminance."""
        xy = np.array([0.3, 0.3])
        xyz = xy_to_XYZ(xy, Y=50.0)
        assert xyz[1] == pytest.approx(50.0)


class TestChromaticAdaptation:
    """Tests for Bradford chromatic adaptation."""

    def test_d65_to_d50_white(self):
        """D65 white adapted to D50 should give D50 white."""
        from cielab_gamut_tools.colorspace.adaptation import D65_XY, D50_XY

        d65_xyz = xy_to_XYZ(D65_XY)
        d50_xyz = adapt_d65_to_d50(d65_xyz)
        expected = xy_to_XYZ(D50_XY)
        np.testing.assert_allclose(d50_xyz, expected, rtol=1e-3)

    def test_identity_adaptation(self):
        """Adapting from an illuminant to itself should be identity."""
        from cielab_gamut_tools.colorspace.adaptation import D65_XY

        xyz = np.array([0.5, 0.5, 0.5])
        adapted = chromatic_adaptation(xyz, D65_XY, D65_XY)
        np.testing.assert_allclose(adapted, xyz, rtol=1e-10)

    def test_batch_adaptation(self):
        """Test adaptation of multiple points."""
        xyz = np.array([
            [0.5, 0.5, 0.5],
            [0.2, 0.3, 0.4],
        ])
        adapted = adapt_d65_to_d50(xyz)
        assert adapted.shape == xyz.shape


class TestSrgbGamma:
    """Tests for sRGB gamma encoding/decoding."""

    def test_black_unchanged(self):
        """Black (0) should remain 0."""
        assert srgb_gamma_encode(np.array([0.0]))[0] == pytest.approx(0.0)
        assert srgb_gamma_decode(np.array([0.0]))[0] == pytest.approx(0.0)

    def test_white_unchanged(self):
        """White (1) should remain 1."""
        assert srgb_gamma_encode(np.array([1.0]))[0] == pytest.approx(1.0)
        assert srgb_gamma_decode(np.array([1.0]))[0] == pytest.approx(1.0)

    def test_roundtrip(self):
        """Values should round-trip correctly."""
        linear = np.linspace(0, 1, 100)
        encoded = srgb_gamma_encode(linear)
        decoded = srgb_gamma_decode(encoded)
        np.testing.assert_allclose(decoded, linear, rtol=1e-5)

    def test_linear_region(self):
        """Small values should use linear encoding."""
        # Below ~0.0031308, encoding is linear: 12.92 * x
        val = 0.001
        encoded = srgb_gamma_encode(np.array([val]))[0]
        assert encoded == pytest.approx(12.92 * val, rel=1e-5)

    def test_encoding_expands_darks(self):
        """Gamma encoding should expand dark values (make them brighter)."""
        linear = np.array([0.5])
        encoded = srgb_gamma_encode(linear)
        # 0.5 linear should become > 0.5 encoded (perceptually mid-gray)
        assert encoded[0] > 0.5
