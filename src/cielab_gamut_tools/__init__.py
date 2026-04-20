"""
gamut-volume: Calculate and visualize CIELab gamut volumes of color displays.

This package provides tools for:
- Loading gamut data from CGATS.17 files or RGB/XYZ matrices
- Calculating gamut volumes via cylindrical integration in CIELab space
- Computing gamut intersections for coverage analysis
- Generating synthetic reference gamuts (sRGB, BT.2020, DCI-P3, etc.)
- Visualizing gamuts as 3D surfaces or 2D rings

Example usage:
    from cielab_gamut_tools import Gamut, SyntheticGamut

    # Load measured display gamut
    display = Gamut.from_cgats("measurements.txt")

    # Create sRGB reference
    srgb = SyntheticGamut.srgb()

    # Calculate volumes and coverage
    print(f"Display volume: {display.volume():.0f}")
    print(f"sRGB coverage: {display.intersect(srgb).volume() / srgb.volume() * 100:.1f}%")

    # Visualize
    display.plot_rings(reference=srgb)
"""

from cielab_gamut_tools.gamut import Gamut
from cielab_gamut_tools.measurement import make_rgb_signals
from cielab_gamut_tools.synthetic import SyntheticGamut

__version__ = "0.1.0"
__all__ = ["Gamut", "SyntheticGamut", "make_rgb_signals"]
