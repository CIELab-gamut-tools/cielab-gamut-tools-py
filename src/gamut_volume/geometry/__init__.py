"""
Geometry utilities for gamut volume computation.

Provides RGB cube tesselation and cylindrical volume integration.
"""

from gamut_volume.geometry.tesselation import make_tesselation
from gamut_volume.geometry.volume import compute_volume

__all__ = ["make_tesselation", "compute_volume"]
