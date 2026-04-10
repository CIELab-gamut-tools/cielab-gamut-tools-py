"""
Tests for the Gamut class.
"""

from pathlib import Path

import numpy as np
import pytest

from cielab_gamut_tools.gamut import Gamut
from cielab_gamut_tools.synthetic import SyntheticGamut


SAMPLES_DIR = Path(__file__).parent / "data"


class TestGamutCreation:
    """Tests for Gamut construction."""

    def test_from_arrays(self):
        """Test creating Gamut from Lab and triangle arrays."""
        lab = np.array([
            [50, 0, 0],
            [50, 50, 0],
            [50, 0, 50],
        ], dtype=np.float64)
        triangles = np.array([[0, 1, 2]], dtype=np.int32)

        gamut = Gamut(lab, triangles)

        assert gamut.lab.shape == (3, 3)
        assert gamut.triangles.shape == (1, 3)

    @pytest.mark.skipif(
        not (SAMPLES_DIR / "sRGB.txt").exists(),
        reason="Sample file not available",
    )
    def test_from_cgats(self):
        """Test loading Gamut from CGATS file."""
        gamut = Gamut.from_cgats(SAMPLES_DIR / "sRGB.txt")
        assert gamut.lab.shape[1] == 3


class TestSyntheticGamut:
    """Tests for SyntheticGamut factory."""

    def test_srgb_primaries(self):
        """sRGB should have correct primaries."""
        from cielab_gamut_tools.synthetic import SRGB_PRIMARIES, D65_WHITE

        srgb = SyntheticGamut.srgb()

        np.testing.assert_allclose(srgb.primaries_xy, SRGB_PRIMARIES)
        np.testing.assert_allclose(srgb.white_xy, D65_WHITE)
        assert srgb.gamma == 2.2

    def test_bt2020_primaries(self):
        """BT.2020 should have correct primaries."""
        from cielab_gamut_tools.synthetic import BT2020_PRIMARIES, D65_WHITE

        bt2020 = SyntheticGamut.bt2020()

        np.testing.assert_allclose(bt2020.primaries_xy, BT2020_PRIMARIES)
        np.testing.assert_allclose(bt2020.white_xy, D65_WHITE)
        assert bt2020.gamma == 2.4

    def test_dci_p3_primaries(self):
        """DCI-P3 should have correct primaries and white."""
        from cielab_gamut_tools.synthetic import DCI_P3_PRIMARIES, DCI_WHITE

        dci_p3 = SyntheticGamut.dci_p3()

        np.testing.assert_allclose(dci_p3.primaries_xy, DCI_P3_PRIMARIES)
        np.testing.assert_allclose(dci_p3.white_xy, DCI_WHITE)
        assert dci_p3.gamma == 2.6

    def test_display_p3_primaries(self):
        """Display P3 should have P3 primaries with D65 white."""
        from cielab_gamut_tools.synthetic import DCI_P3_PRIMARIES, D65_WHITE

        display_p3 = SyntheticGamut.display_p3()

        np.testing.assert_allclose(display_p3.primaries_xy, DCI_P3_PRIMARIES)
        np.testing.assert_allclose(display_p3.white_xy, D65_WHITE)
        assert display_p3.gamma == 2.2

    def test_custom_gamut(self):
        """Test creating a custom gamut."""
        primaries = np.array([
            [0.64, 0.33],
            [0.30, 0.60],
            [0.15, 0.06],
        ])
        white = np.array([0.31, 0.33])

        custom = SyntheticGamut(primaries, white, gamma=2.0)

        np.testing.assert_allclose(custom.primaries_xy, primaries)
        np.testing.assert_allclose(custom.white_xy, white)
        assert custom.gamma == 2.0


class TestGamutVolume:
    """Tests for volume calculation."""

    def test_srgb_reference_volume(self):
        """sRGB should have volume approximately 830,732."""
        srgb = SyntheticGamut.srgb()
        volume = srgb.volume()

        # Allow 0.05% tolerance
        assert volume == pytest.approx(830732, rel=0.0005)

    def test_bt2020_larger_than_srgb(self):
        """BT.2020 should have larger volume than sRGB."""
        srgb = SyntheticGamut.srgb()
        bt2020 = SyntheticGamut.bt2020()

        assert bt2020.volume() > srgb.volume()


class TestGamutIntersection:
    """Tests for gamut intersection."""

    def test_intersection_commutative(self):
        """A ∩ B should equal B ∩ A."""
        srgb = SyntheticGamut.srgb()
        bt2020 = SyntheticGamut.bt2020()

        ab = srgb.intersect(bt2020).volume()
        ba = bt2020.intersect(srgb).volume()

        assert ab == pytest.approx(ba, rel=0.0005)

    def test_intersection_smaller_than_either(self):
        """Intersection volume should be <= min of both volumes."""
        srgb = SyntheticGamut.srgb()
        bt2020 = SyntheticGamut.bt2020()

        intersection = srgb.intersect(bt2020)
        min_vol = min(srgb.volume(), bt2020.volume())

        assert intersection.volume() <= min_vol * 1.0005  # Small tolerance

    def test_self_intersection_equals_self(self):
        """A ∩ A should equal A."""
        srgb = SyntheticGamut.srgb()

        self_intersection = srgb.intersect(srgb)

        assert self_intersection.volume() == pytest.approx(
            srgb.volume(), rel=0.001
        )
