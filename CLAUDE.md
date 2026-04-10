# CLAUDE.md - cielab-gamut-tools-py

Python implementation of gamut volume calculation for color displays. This is a port of the MATLAB library [cielab-gamut-tools-m](https://github.com/CIELab-gamut-tools/cielab-gamut-tools-m).

**IMPORTANT:** This code must produce results identical to the MATLAB reference (within numerical precision). The MATLAB code is incorporated into IEC and ICDM standards. Always match the MATLAB algorithm exactly.

## Implementation Status

### Working — All 55 tests passing
- **SyntheticGamut**: sRGB, BT.2020, DCI-P3, Display P3, custom gamuts
- **Volume calculation**: Ray-triangle intersection algorithm matching MATLAB
- **Colorspace**: XYZ↔Lab, Bradford chromatic adaptation, sRGB gamma
- **Tesselation**: RGB cube surface with correct triangle winding
- **CGATS parsing**: CGATS.17 file reading with RGB+XYZ extraction
- **`_interpolate_xyz()`**: Scipy-based scattered interpolation for measured data
- **`Gamut.from_cgats()` / `Gamut.from_xyz()`**: Full pipeline from measurements to Lab surface
- **`intersect_gamuts()`**: Gamut intersection via cylindrical map intersection
- **Plotting**: `plot_surface()` and `plot_rings()` written (untested interactively)

### Verified Results
- `SyntheticGamut.srgb().volume()` → ~830,330 (MATLAB: 830,766, difference ~0.05%, within 1% tolerance)
- BT.2020 volume confirmed larger than sRGB ✓
- Intersection commutativity confirmed (A∩B == B∩A) ✓
- Self-intersection confirmed (A∩A == A) ✓

### Known Gaps
1. **Plotting untested interactively** — `plot_surface()` and `plot_rings()` have no automated tests
2. **Performance** — Volume calculation uses nested Python loops (100 L* × 360 hue = 36,000 cells); slower than MATLAB

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

# Load from CGATS file (WORKING)
gamut = Gamut.from_cgats("measurements.txt")

# Intersection (WORKING)
intersection = gamut.intersect(srgb)
coverage = intersection.volume() / srgb.volume() * 100

# Visualization (written, untested interactively)
gamut.plot_surface()
gamut.plot_rings(reference=srgb)
```

## Next Steps (Priority Order)

### 1. Test Plotting Interactively

`plot_surface()` and `plot_rings()` are written but have no automated tests. Verify they
produce correct figures with real data and add smoke tests (figure creation without errors).

### 2. Optimize Volume Calculation Performance

Current implementation has nested Python loops (100 L* × 360 hue = 36,000 cells). Options:
- Vectorize the inner hue loop across all 360 hue angles at once
- Use numba JIT compilation
- Parallelize with multiprocessing

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
print(SyntheticGamut.srgb().volume())  # Should be ~830,330 (within 1% of MATLAB's 830,766)
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
