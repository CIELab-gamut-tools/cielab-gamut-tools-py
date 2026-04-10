# CLAUDE.md - cielab-gamut-tools-py

Python implementation of gamut volume calculation for color displays. This is a port of the MATLAB library [cielab-gamut-tools-m](https://github.com/CIELab-gamut-tools/cielab-gamut-tools-m).

**IMPORTANT:** This code must produce results identical to the MATLAB reference (within numerical precision). The MATLAB code is incorporated into IEC and ICDM standards. Always match the MATLAB algorithm exactly.

## Implementation Status

### Working
- **SyntheticGamut**: sRGB, BT.2020, DCI-P3, Display P3, custom gamuts
- **Volume calculation**: Ray-triangle intersection algorithm matching MATLAB
- **Colorspace**: XYZ↔Lab, Bradford chromatic adaptation, sRGB gamma
- **Tesselation**: RGB cube surface with correct triangle winding
- **CGATS parsing**: Basic CGATS.17 file reading
- **All unit tests passing**

### Verified Results
- `SyntheticGamut.srgb().volume()` → 830,330 (MATLAB: 830,766, difference ~0.05%)

### Not Yet Implemented
1. **`_interpolate_xyz()`** in `gamut.py` - Required for `Gamut.from_cgats()` and `Gamut.from_xyz()` to work with measured data
2. **`intersect_gamuts()`** in `geometry/volume.py` - Gamut intersection
3. **Plotting functions** - `plot_surface()` and `plot_rings()` are stubbed but untested
4. **Performance optimization** - Volume calculation is slower than MATLAB due to Python loops

## Architecture

```
src/cielab_gamut_tools/
├── __init__.py           # Public API: Gamut, SyntheticGamut
├── gamut.py              # Gamut class - main entry point
├── synthetic.py          # SyntheticGamut factory for reference gamuts
├── io/
│   └── cgats.py          # CGATS.17 and IDMS v1.3 file parsing
├── colorspace/
│   ├── lab.py            # XYZ ↔ CIELab conversions (D50 reference)
│   ├── adaptation.py     # Bradford chromatic adaptation transform
│   └── srgb.py           # sRGB gamma encoding/decoding
├── geometry/
│   ├── tesselation.py    # RGB cube surface tesselation
│   └── volume.py         # Cylindrical coordinate mapping & integration
└── plotting/
    ├── surface.py        # 3D gamut surface visualization
    └── rings.py          # 2D gamut rings at L* slices
```

## Critical Implementation Details

### Tesselation (geometry/tesselation.py)

**Must match MATLAB exactly.** Key points:

1. **Vertex ordering for consistent winding:**
   - Bottom faces (value=0): `[Lower, J, K]`, `[K, Lower, J]`, `[J, K, Lower]`
   - Top faces (value=1): `[Upper, K, J]`, `[J, Upper, K]`, `[K, J, Upper]`
   - Note: J,K swapped to K,J for opposite faces - this ensures outward normals

2. **Column-major flattening:** Use `flatten('F')` to match MATLAB's `(:)` operator
   ```python
   J, K = np.meshgrid(gsv, gsv)
   J = J.flatten('F')  # Column-major like MATLAB
   K = K.flatten('F')
   ```

3. **Triangle indices:** `[m, m+n, m+1]` and `[m+n, m+n+1, m+1]` where `m = n*n*s + n*q + p`

### Volume Calculation (geometry/volume.py)

Uses ray-triangle intersection (Möller-Trumbore algorithm), NOT rasterization.

**Algorithm (matching `CIEtools/cielab_cylindrical_map.m`):**

1. Reorder Lab to `[a*, b*, L*]` to match MATLAB's Z matrix
2. For each L* slice (100 steps), find triangles spanning that L*
3. For each hue angle (360 steps), shoot ray from `(0, 0, L_mid)` in direction `(sin(h), cos(h), 0)`
4. Find ray-triangle intersections using Möller-Trumbore
5. Record `[sign(1/det), t]` for each intersection (sign indicates surface orientation)
6. Apply parity filter to handle edge cases
7. Integrate: `V = Σ sign × t² × dL × dh / 2`

**Key code patterns from MATLAB:**
```python
# Ray direction (note: sin,cos not cos,sin)
dir_2d = np.array([np.sin(hue_mid), np.cos(hue_mid)])

# Parity filter (matching MATLAB exactly)
flipped_signs = cm[::-1, 0]
cumsum_flipped = np.cumsum(flipped_signs)
parity_check = cumsum_flipped[::-1] * 2 - cm[:, 0]
keep = parity_check == 1
```

### RGB to XYZ Matrix (synthetic.py)

**Bug fix applied:** `_build_rgb_to_xyz_matrix()` must return `M` not `M.T`. The matrix is used as `rgb @ M.T` for row-vector multiplication.

### Chromatic Adaptation

Uses Bradford transform. Source white comes from the gamut's white point (e.g., D65 for sRGB), destination is always D50 for Lab conversion.

## Public API

```python
from cielab_gamut_tools import Gamut, SyntheticGamut

# Reference gamuts (WORKING)
srgb = SyntheticGamut.srgb()
bt2020 = SyntheticGamut.bt2020()
dci_p3 = SyntheticGamut.dci_p3()
custom = SyntheticGamut(primaries_xy, white_xy, gamma=2.2)

# Volume calculation (WORKING)
volume = srgb.volume()

# Load from CGATS file (NOT YET WORKING - needs _interpolate_xyz)
gamut = Gamut.from_cgats("measurements.txt")

# Intersection (NOT YET IMPLEMENTED)
intersection = gamut.intersect(srgb)
coverage = intersection.volume() / srgb.volume() * 100

# Visualization (UNTESTED)
gamut.plot_surface()
gamut.plot_rings(reference=srgb)
```

## Next Steps (Priority Order)

### 1. Implement `_interpolate_xyz()` in gamut.py

This function interpolates XYZ values from measured RGB/XYZ pairs to the tesselation vertices. The MATLAB approach:
- Uses the measured RGB values directly as the tesselation grid
- See `CIELabGamut.m` lines ~140: `make_tesselation(unique(gamut.RGB))`
- May need scattered interpolation (scipy) for arbitrary measurement grids

### 2. Optimize Volume Calculation Performance

Current implementation has nested Python loops (100 L* × 360 hue). Options:
- Vectorize the inner hue loop
- Use numba JIT compilation
- Parallelize with multiprocessing

### 3. Implement Gamut Intersection

See `IntersectGamuts.m` in MATLAB. Algorithm:
- Build cylindrical maps for both gamuts
- Take minimum chroma at each (L*, h) cell
- Create new gamut object from intersection map

### 4. Test and Fix Plotting

The plotting code is written but untested. May need fixes.

## Development

### Setup
```bash
cd cielab-gamut-tools-py
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### Commands
```bash
pytest                    # Run tests
pytest --cov=cielab_gamut_tools # With coverage
mypy src                  # Type checking
ruff check src tests      # Linting
```

### Quick Test
```python
from cielab_gamut_tools import SyntheticGamut
print(SyntheticGamut.srgb().volume())  # Should be ~830,330
```

## Reference Material

- **MATLAB implementation:** `../cielab-gamut-tools-m/`
- **Key MATLAB files:**
  - `SyntheticGamut.m` - Synthetic gamut creation
  - `CIELabGamut.m` - Gamut from measurements
  - `GetVolume.m` - Volume calculation entry point
  - `+CIEtools/cielab_cylindrical_map.m` - Core ray-triangle intersection
  - `+CIEtools/make_tesselation.m` - RGB cube tesselation
- **Publication:** Smith et al., Journal of the Society for Information Display, 2020
- **Standards:** IEC, ICDM (derived from this code)

## Testing Strategy

Extensive unit testing is a primary goal (improving on limited MATLAB testing).

### Test Categories
1. **Colorspace** - XYZ↔Lab round-trip, reference values, edge cases
2. **File I/O** - CGATS parsing, error handling
3. **Geometry** - Tesselation completeness, volume against MATLAB reference
4. **Gamut operations** - Volume, intersection properties
5. **Integration** - Full workflow comparison with MATLAB

### Reference Values
- sRGB volume: ~830,732 (from MATLAB)
- Sample files in `tests/data/` and `samples/`

## Package Configuration

- **Python:** ≥3.10
- **Package name:** `cielab-gamut-tools` (PyPI), import as `cielab_gamut_tools`
- **Build system:** hatchling with pyproject.toml
- **Layout:** src layout
