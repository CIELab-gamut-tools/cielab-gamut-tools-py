"""
Geometry utilities for gamut volume computation.

Provides RGB cube tesselation and cylindrical volume integration.
"""

from cielab_gamut_tools.geometry.tesselation import make_tesselation
from cielab_gamut_tools.geometry.volume import compute_volume

__all__ = ["make_tesselation", "compute_volume"]
