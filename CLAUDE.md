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

### Performance
Full test suite runs in ~700 ms. Intersection tests run in ~50–100 ms each.
Original unoptimised implementation took ~26 s for the same tests (~37× improvement).

Optimisations applied (in order):
1. **Cylindrical map caching** — cached on the `Gamut` object; shared between `volume()` and `intersect()` calls
2. **Vectorised hue loop** — all 360 ray directions batched into a single matrix multiply per L* slice (`e2e1_2d @ all_dirs.T`), replacing a 360-iteration Python loop
3. **Numba JIT: inner hue loop** — `_process_hue_loop_nb` compiles the per-cell collect/sort/parity-filter loop to native code; cylmap format changed from Python object array to dense `(l_steps, h_steps, MAX_K, 2)` float64 array + `(l_steps, h_steps)` int64 count array
4. **Numba JIT: intersection loop** — `_intersect_all_cells_nb` compiles the full 36,000-cell `intersect_gamuts` double-loop to native code, with a pre-allocated temp buffer to avoid per-cell heap allocation
5. **Vectorised integration** — `_integrate_cylmap` is a single `np.sum` over a masked dense array; no loop
6. **Numba warm-up at import** — both JIT functions are called with minimal dummy arrays at module load time, so cache-load cost is paid at import rather than on the first real computation

### Known Gaps
1. **Plotting untested interactively** — `plot_surface()` and `plot_rings()` have no automated tests

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
3. Batch all 360 ray directions into a single matrix multiply per slice
4. Pass resulting `(n_tri, 360)` arrays to `_process_hue_loop_nb` (Numba JIT)
5. JIT loop: for each hue, collect valid hits, sort by distance, apply parity filter
6. Integrate: `V = Σ sign × t² × dL × dh / 2` (fully vectorised, no loop)

**Cylindrical map format:**
```python
cylmap:  np.ndarray  shape (l_steps, h_steps, MAX_K, 2)  # [..., 0]=sign, [..., 1]=distance
counts:  np.ndarray  shape (l_steps, h_steps)             # valid entries per cell
```
`MAX_K = 4`. Most cells have 0 (below black level) or 1 (origin inside gamut, single
surface exit) valid intersection after parity filtering; rarely 2.

**Parity filter (matching MATLAB exactly):**
```python
# keep entry i where (cumsum of signs from i to end) * 2 - sign == 1
flipped_signs = cm[::-1, 0]
cumsum_flipped = np.cumsum(flipped_signs)
parity_check = cumsum_flipped[::-1] * 2 - cm[:, 0]
keep = parity_check == 1
```

**Key ray direction convention (note: sin,cos not cos,sin):**
```python
dir_2d = np.array([np.sin(hue_mid), np.cos(hue_mid)])  # puts 0° along +b* axis
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

## Next Steps

### Test Plotting Interactively

`plot_surface()` and `plot_rings()` are written but have no automated tests. Verify they
produce correct figures with real data and add smoke tests (figure creation without errors).

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
- **Dependencies:** numpy, matplotlib, scipy, numba (≥0.57)
- **Build system:** hatchling with pyproject.toml
- **Layout:** src layout
