"""
Tests for RGB signal generation, Adobe RGB gamut, compute_rings(), and
plotting smoke tests.
"""

from __future__ import annotations

import numpy as np
import pytest


# ── Item 2: make_rgb_signals ───────────────────────────────────────────────

class TestMakeRgbSignals:

    def test_default_shape_m11(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=8)
        assert signals.shape == (602, 3)

    def test_standard_sizes(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        for m, expected_n in [(11, 602), (9, 386), (7, 218), (5, 98)]:
            signals = make_rgb_signals(m=m)
            assert signals.shape[0] == expected_n, f"m={m}: expected {expected_n} rows"

    def test_formula_matches(self):
        """n = 6m² − 12m + 8 for all tested m values."""
        from cielab_gamut_tools.measurement import make_rgb_signals
        for m in [5, 7, 9, 11]:
            expected = 6 * m * m - 12 * m + 8
            assert make_rgb_signals(m=m).shape[0] == expected

    def test_8bit_range(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=8)
        assert signals.min() >= 0
        assert signals.max() <= 255

    def test_10bit_range(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=10)
        assert signals.max() <= 1023

    def test_corners_present(self):
        """All 8 cube corners must appear in the 8-bit signal list."""
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=8)
        corners = [(0, 0, 0), (0, 0, 255), (0, 255, 0), (0, 255, 255),
                   (255, 0, 0), (255, 0, 255), (255, 255, 0), (255, 255, 255)]
        for corner in corners:
            assert any(np.all(signals == corner, axis=1)), f"Corner {corner} missing"

    def test_no_duplicates(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=8)
        unique = np.unique(signals, axis=0)
        assert len(unique) == len(signals), "Duplicate rows found"

    def test_lexicographic_order(self):
        """Rows must be in lexicographic (RGB) order — matches MATLAB unique."""
        from cielab_gamut_tools.measurement import make_rgb_signals
        signals = make_rgb_signals(m=11, bits=8).astype(int)
        for i in range(len(signals) - 1):
            a, b = signals[i].tolist(), signals[i + 1].tolist()
            assert a <= b, f"Row {i} out of order: {a} > {b}"

    def test_invalid_m(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        with pytest.raises(ValueError, match="m must be at least 2"):
            make_rgb_signals(m=1)

    def test_invalid_bits(self):
        from cielab_gamut_tools.measurement import make_rgb_signals
        with pytest.raises(ValueError, match="bits must be at least 1"):
            make_rgb_signals(bits=0)

    def test_public_api_import(self):
        from cielab_gamut_tools import make_rgb_signals
        assert callable(make_rgb_signals)


# ── Item 4: Adobe RGB ──────────────────────────────────────────────────────

class TestAdobeRgb:

    def test_creates_gamut(self):
        from cielab_gamut_tools import SyntheticGamut
        g = SyntheticGamut.adobe_rgb()
        assert g is not None

    def test_title(self):
        from cielab_gamut_tools import SyntheticGamut
        assert SyntheticGamut.adobe_rgb().title == "Adobe RGB (1998)"

    def test_volume_positive(self):
        from cielab_gamut_tools import SyntheticGamut
        assert SyntheticGamut.adobe_rgb().volume() > 0

    def test_volume_between_srgb_and_bt2020(self):
        """Adobe RGB is wider than sRGB and narrower than BT.2020."""
        from cielab_gamut_tools import SyntheticGamut
        srgb_vol = SyntheticGamut.srgb().volume()
        adobe_vol = SyntheticGamut.adobe_rgb().volume()
        bt2020_vol = SyntheticGamut.bt2020().volume()
        assert adobe_vol > srgb_vol
        assert adobe_vol < bt2020_vol

    def test_primaries_shape(self):
        from cielab_gamut_tools import SyntheticGamut
        g = SyntheticGamut.adobe_rgb()
        assert g.primaries_xy.shape == (3, 2)


# ── Item 3: compute_rings() ────────────────────────────────────────────────

class TestComputeRings:

    def test_shape(self):
        from cielab_gamut_tools import SyntheticGamut
        rings = SyntheticGamut.srgb().compute_rings()
        assert rings.shape == (100, 360)

    def test_non_negative(self):
        from cielab_gamut_tools import SyntheticGamut
        rings = SyntheticGamut.srgb().compute_rings()
        assert np.all(rings >= 0)

    def test_monotonically_increasing_in_L(self):
        """Cumulative ring radii must be non-decreasing along L*."""
        from cielab_gamut_tools import SyntheticGamut
        rings = SyntheticGamut.srgb().compute_rings()
        diffs = np.diff(rings, axis=0)
        assert np.all(diffs >= -1e-9), "Rings should be non-decreasing in L*"

    def test_outer_ring_matches_volume(self):
        """The area of the outer ring should equal the total gamut volume."""
        from cielab_gamut_tools import SyntheticGamut
        g = SyntheticGamut.srgb()
        rings = g.compute_rings()
        dh = 2 * np.pi / 360
        # Area = sum(r² * dh / 2)
        area = float(np.sum(rings[-1] ** 2) * dh / 2)
        assert area == pytest.approx(g.volume(), rel=0.01)

    def test_custom_resolution(self):
        from cielab_gamut_tools import SyntheticGamut
        rings = SyntheticGamut.srgb().compute_rings(l_steps=50, h_steps=180)
        assert rings.shape == (50, 180)

    def test_gamut_method_direct(self):
        from cielab_gamut_tools import SyntheticGamut
        g = SyntheticGamut.srgb().gamut
        rings = g.compute_rings()
        assert rings.shape == (100, 360)

    def test_intersection_rings_smaller(self):
        """sRGB ∩ sRGB rings should equal sRGB rings; sRGB ∩ BT.2020 ≤ sRGB."""
        from cielab_gamut_tools import SyntheticGamut
        srgb = SyntheticGamut.srgb()
        bt2020 = SyntheticGamut.bt2020()
        isect = srgb.intersect(bt2020)
        rings_srgb = srgb.compute_rings()
        rings_isect = isect.compute_rings()
        # Intersection must not exceed sRGB at any cell
        assert np.all(rings_isect <= rings_srgb + 1e-6)


# ── Item 6: Plotting smoke tests ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_agg_backend():
    """Ensure matplotlib uses a non-interactive backend for all tests here."""
    import matplotlib
    matplotlib.use("Agg")


class TestPlotSmoke:

    def test_plot_surface_returns_figure(self):
        import matplotlib.figure
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_surface()
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_rings_returns_figure(self):
        import matplotlib.figure
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_rings()
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_rings_with_reference(self):
        import matplotlib.figure
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_rings(reference=SyntheticGamut.bt2020())
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_rings_intersection_mode(self):
        import matplotlib.figure
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_rings(
            reference=SyntheticGamut.bt2020(),
            intersection_plot=True,
        )
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_rings_adobe_rgb(self):
        import matplotlib.figure
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.adobe_rgb().plot_rings(reference=SyntheticGamut.srgb())
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_surface_closes_cleanly(self):
        import matplotlib.pyplot as plt
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_surface()
        plt.close(fig)

    def test_plot_rings_closes_cleanly(self):
        import matplotlib.pyplot as plt
        from cielab_gamut_tools import SyntheticGamut
        fig = SyntheticGamut.srgb().plot_rings()
        plt.close(fig)
