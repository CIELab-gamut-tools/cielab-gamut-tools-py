"""
Tests for the Gamut class.
"""

from pathlib import Path

import numpy as np
import pytest

from cielab_gamut_tools.gamut import Gamut
from cielab_gamut_tools.io.cgats import read_cgats
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
        assert callable(srgb.gamma)

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
        assert callable(display_p3.gamma)

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


class TestGamutXyzRetention:
    """Tests that XYZ data is retained on Gamut objects."""

    def test_synthetic_gamut_has_xyz(self):
        """SyntheticGamut-built Gamut should have xyz populated."""
        srgb = SyntheticGamut.srgb()
        g = srgb.gamut
        assert g.xyz is not None
        assert g.xyz.shape == g.lab.shape

    def test_from_xyz_retains_xyz(self):
        """Gamut.from_xyz() should store the interpolated surface XYZ."""
        srgb = SyntheticGamut.srgb()
        g = srgb.gamut
        # Build a Gamut via from_xyz using the surface points directly
        g2 = Gamut.from_xyz(g.rgb, g.xyz)
        assert g2.xyz is not None
        assert g2.xyz.shape == (g2.lab.shape[0], 3)

    def test_from_lab_has_no_xyz(self, tmp_path):
        """Gamut loaded from a LAB-only file should have xyz=None."""
        from cielab_gamut_tools.io.cgats import write_cgats

        srgb = SyntheticGamut.srgb().gamut
        # Write envelope (LAB only, no XYZ)
        env = tmp_path / "env.txt"
        srgb.to_cgats(env, mode="envelope")

        g = Gamut.from_cgats(env)
        assert g.xyz is None


class TestGamutToCgats:
    """Tests for Gamut.to_cgats() and SyntheticGamut.to_cgats()."""

    def test_envelope_mode_creates_file(self, tmp_path):
        """to_cgats() should create a file."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out)
        assert out.exists()

    def test_envelope_mode_file_type_header(self, tmp_path):
        """Envelope mode should write IDMS_FILE_TYPE = CGE_ENVELOPE."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out, mode="envelope")
        lines = out.read_text().splitlines()
        assert "IDMS_FILE_TYPE\tCGE_ENVELOPE" in lines

    def test_envelope_mode_has_rgb_and_lab(self, tmp_path):
        """Envelope mode output should contain RGB and LAB columns."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out, mode="envelope")
        data = read_cgats(out)
        assert data.rgb is not None
        assert data.lab is not None
        assert data.xyz is None

    def test_measurement_mode_file_type_header(self, tmp_path):
        """Measurement mode should write IDMS_FILE_TYPE = CGE_MEASUREMENT."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "meas.txt"
        srgb.to_cgats(out, mode="measurement")
        lines = out.read_text().splitlines()
        assert "IDMS_FILE_TYPE\tCGE_MEASUREMENT" in lines

    def test_measurement_mode_has_rgb_and_xyz(self, tmp_path):
        """Measurement mode output should contain RGB and XYZ columns."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "meas.txt"
        srgb.to_cgats(out, mode="measurement")
        data = read_cgats(out)
        assert data.rgb is not None
        assert data.xyz is not None
        assert data.lab is None

    def test_all_mode_no_file_type_header(self, tmp_path):
        """'all' mode should not write an IDMS_FILE_TYPE header."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "all.txt"
        srgb.to_cgats(out, mode="all")
        lines = out.read_text().splitlines()
        assert not any("IDMS_FILE_TYPE" in l for l in lines)

    def test_all_mode_has_rgb_xyz_lab(self, tmp_path):
        """'all' mode output should contain RGB, XYZ, and LAB columns."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "all.txt"
        srgb.to_cgats(out, mode="all")
        data = read_cgats(out)
        assert data.rgb is not None
        assert data.xyz is not None
        assert data.lab is not None

    def test_rgb_scaled_to_255(self, tmp_path):
        """RGB values in output should be in [0, 255] range."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out, mode="envelope")
        data = read_cgats(out)
        assert data.rgb is not None
        assert data.rgb.max() <= 255.0
        assert data.rgb.min() >= 0.0

    def test_602_unique_surface_points(self, tmp_path):
        """to_cgats() must write 602 unique surface points, not 726 tessellation vertices.

        The tessellation internally stores 726 vertices (6 × 11² for the standard
        m=11 grid) with edge/corner vertices replicated across adjacent faces.
        CGATS output must deduplicate these to the 602 unique RGB values — equivalent
        to MATLAB's ``unique(rgb, 'rows')`` in make_rgb_signals.m.
        Measuring the same RGB value twice would waste metrologist time.
        """
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out, mode="envelope")
        data = read_cgats(out)
        assert data.lab is not None
        # Standard m=11 grid: 6m² − 12m + 8 = 602 unique surface points
        assert len(data.lab) == 602
        # Verify no duplicate RGB rows in the output
        assert data.rgb is not None
        unique_rgb = np.unique(data.rgb, axis=0)
        assert len(unique_rgb) == len(data.rgb), "Duplicate RGB values found in CGATS output"

    def test_title_as_description(self, tmp_path):
        """self.title should appear as the description line."""
        srgb = SyntheticGamut.srgb()  # title = "sRGB"
        out = tmp_path / "env.txt"
        srgb.to_cgats(out)
        lines = out.read_text().splitlines()
        assert "sRGB" in lines

    def test_custom_description_overrides_title(self, tmp_path):
        """Explicit description kwarg should take precedence over title."""
        srgb = SyntheticGamut.srgb()
        out = tmp_path / "env.txt"
        srgb.to_cgats(out, description="Custom description")
        lines = out.read_text().splitlines()
        assert "Custom description" in lines

    def test_invalid_mode_raises(self, tmp_path):
        """Unknown mode should raise ValueError."""
        srgb = SyntheticGamut.srgb()
        with pytest.raises(ValueError, match="mode"):
            srgb.to_cgats(tmp_path / "out.txt", mode="invalid")

    def test_measurement_mode_requires_xyz(self, tmp_path):
        """measurement/all mode on a LAB-only Gamut should raise ValueError."""
        # Build a Gamut without XYZ by loading a LAB envelope
        srgb = SyntheticGamut.srgb()
        env = tmp_path / "env.txt"
        srgb.to_cgats(env, mode="envelope")
        g = Gamut.from_cgats(env)

        assert g.xyz is None
        with pytest.raises(ValueError, match="xyz"):
            g.to_cgats(tmp_path / "out.txt", mode="measurement")


class TestGamutFromCgatsLab:
    """Tests for Gamut.from_cgats() with LAB envelope files."""

    def test_from_cgats_lab_produces_gamut(self, tmp_path):
        """Loading a CGE_ENVELOPE file should return a valid Gamut."""
        srgb = SyntheticGamut.srgb()
        env = tmp_path / "env.txt"
        srgb.to_cgats(env, mode="envelope")

        g = Gamut.from_cgats(env)

        assert g.lab.shape[1] == 3
        assert g.triangles.shape[1] == 3

    def test_from_cgats_lab_volume_close_to_original(self, tmp_path):
        """Volume from a re-loaded LAB envelope should match the original."""
        srgb = SyntheticGamut.srgb()
        env = tmp_path / "env.txt"
        srgb.to_cgats(env, mode="envelope")

        g = Gamut.from_cgats(env)

        assert g.volume() == pytest.approx(srgb.volume(), rel=0.001)

    def test_from_cgats_lab_without_rgb_raises(self, tmp_path):
        """A LAB file without RGB should warn and raise ValueError."""
        from cielab_gamut_tools.io.cgats import write_cgats

        lab = np.array([[0.0, 0.0, 0.0], [50.0, 10.0, -10.0]])
        out = tmp_path / "lab_no_rgb.txt"
        write_cgats(out, lab=lab)  # no rgb

        with pytest.warns(UserWarning, match="RGB"):
            with pytest.raises(ValueError):
                Gamut.from_cgats(out)

    def test_from_cgats_xyz_priority_over_lab(self, tmp_path):
        """When both XYZ and LAB are present, XYZ path should be used."""
        from cielab_gamut_tools.io.cgats import write_cgats

        srgb = SyntheticGamut.srgb().gamut
        rgb_255 = np.round(srgb.rgb * 255)
        out = tmp_path / "both.txt"
        write_cgats(out, rgb=rgb_255, xyz=srgb.xyz, lab=srgb.lab)

        g = Gamut.from_cgats(out)

        # XYZ path re-derives Lab; result should still be close
        assert g.xyz is not None  # XYZ path was taken
        assert g.volume() == pytest.approx(srgb.volume(), rel=0.001)

    def test_from_cgats_reference_envelope(self):
        """Load the IDMS reference sRGB CGE_ENVELOPE and check volume."""
        ref = Path(
            "standards/IDMS 5.32-code/"
            "Reference_sRGB_IEC_61966-2-1_cge_envelope.txt"
        )
        if not ref.exists():
            pytest.skip("Reference envelope file not available")

        g = Gamut.from_cgats(ref)

        assert g.xyz is None  # envelope file has no XYZ
        # Volume should be within 1% of the MATLAB reference
        assert g.volume() == pytest.approx(830732, rel=0.01)
