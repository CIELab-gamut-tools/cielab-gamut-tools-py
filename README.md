# cielab-gamut-tools

Calculate and visualize CIELab colour gamuts of displays.

This is a Python port of the [gamut-volume-m](https://github.com/CIELab-gamut-tools/gamut-volume-m) MATLAB library.

## Features

- Load gamut data from CGATS.17 ASCII files or RGB/XYZ matrices
- Support for emissive and reflective displays (IDMS v1.3 format)
- Calculate gamut volumes via cylindrical integration in CIELab space
- Compute gamut intersections for coverage analysis
- Generate synthetic reference gamuts (sRGB, BT.2020, DCI-P3, etc.)
- Visualize gamuts as 3D surfaces or 2D rings

## Installation

```bash
pip install cielab-gamut-tools
```

Or install from source:

```bash
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e .
```

## Quick Start

```python
from cielab_gamut_tools import Gamut, SyntheticGamut

# Load measured display gamut from CGATS file
display = Gamut.from_cgats("measurements.txt")

# Create standard reference gamuts
srgb = SyntheticGamut.srgb()
bt2020 = SyntheticGamut.bt2020()

# Calculate volumes
print(f"Display volume: {display.volume():.0f}")
print(f"sRGB volume: {srgb.volume():.0f}")

# Calculate sRGB coverage
intersection = display.intersect(srgb)
coverage = intersection.volume() / srgb.volume() * 100
print(f"sRGB coverage: {coverage:.1f}%")

# Visualize
display.plot_rings(reference=srgb)
```

## Reference Gamuts

The library includes built-in reference gamuts:

```python
srgb = SyntheticGamut.srgb()        # sRGB (D65, gamma 2.2)
bt2020 = SyntheticGamut.bt2020()    # BT.2020 (D65, gamma 2.4)
dci_p3 = SyntheticGamut.dci_p3()    # DCI-P3 (DCI white, gamma 2.6)
display_p3 = SyntheticGamut.display_p3()  # Display P3 (D65, gamma 2.2)
```

Or create custom gamuts:

```python
custom = SyntheticGamut(
    primaries_xy=[[0.68, 0.32], [0.265, 0.69], [0.15, 0.06]],
    white_xy=[0.3127, 0.329],
    gamma=2.2
)
```

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=cielab_gamut_tools --cov-report=term-missing

# Type checking
mypy src

# Linting
ruff check src tests
```

## Citation

If you use this software in academic work, please cite:

> Smith, E., et al. (2020). "Gamut volume calculation for display color characterization."
> Journal of the Society for Information Display.

## License

MIT License - see [LICENSE](LICENSE) for details.
