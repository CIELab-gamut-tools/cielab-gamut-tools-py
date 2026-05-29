# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Python implementation of gamut volume calculation for color displays. This is a port of the MATLAB library [cielab-gamut-tools-m](https://github.com/CIELab-gamut-tools/cielab-gamut-tools-m).

**IMPORTANT:** This code must produce results identical to the MATLAB reference (within numerical precision). The MATLAB code is incorporated into IEC and ICDM standards. Always match the MATLAB algorithm exactly.

**WORKFLOW:** Work directly in the main project folder (`cielab-gamut-tools-py/`), not in git worktrees. This is a single-developer project — worktrees add complexity without benefit.

## Development Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Test
pytest                                             # all tests
pytest tests/test_gamut.py                         # single file
pytest tests/test_gamut.py::TestVolume             # single class
pytest tests/test_gamut.py::TestVolume::test_srgb  # single test
pytest --cov=cielab_gamut_tools                    # with coverage

# Lint / format
ruff check src tests
ruff format src tests
mypy src

# UI frontend (requires Node.js)
make ui                                            # build frontend → ui/dist/
cd src/cielab_gamut_tools/ui/frontend
npm run dev                                        # dev server: Vite :5173 + Python API :8000
```

The test suite runs in ~700 ms (Numba JIT warms up at import).

`npm run dev` starts both servers via `concurrently` (Vite on port 5173 proxying `/api` to the
Python server on port 8000). Use this for UI development; changes to `.vue`/`.js` files hot-reload
instantly. `make ui` runs `npm run build` which compiles to `ui/dist/` — this is the static bundle
served by `cgt ui` and bundled into the Python wheel.

## Architecture

```
src/cielab_gamut_tools/
├── __init__.py           # Public API: Gamut, SyntheticGamut, make_rgb_signals
├── gamut.py              # Gamut class — volume, intersect, plot, to_cgats
├── synthetic.py          # SyntheticGamut factory for reference gamuts
├── measurement.py        # make_rgb_signals(m, bits) — normative test signal set
├── io/
│   └── cgats.py          # CGATS.17 / IDMS v1.3 reader + writer
├── colorspace/
│   ├── lab.py            # XYZ ↔ CIELab (D50 reference)
│   ├── adaptation.py     # Bradford chromatic adaptation
│   └── srgb.py           # sRGB piecewise gamma
├── geometry/
│   ├── tesselation.py    # RGB cube surface tesselation
│   └── volume.py         # Cylindrical map, ray-triangle intersection, Numba JIT
├── plotting/
│   ├── surface.py        # 3D gamut surface (matplotlib)
│   └── rings.py          # 2D C*_RSS rings plot
└── cli/
    ├── __init__.py       # Exports main()
    ├── _app.py           # Typer app, --version, command groups
    ├── _resolve.py       # resolve_gamut(): file path or named gamut → Gamut
    └── commands/
        ├── about.py      # about command
        ├── calculate.py  # volume, coverage, compare subcommands
        ├── plot.py       # rings, surface subcommands
        └── generate.py   # rgb-signals, synthetic subcommands
```

### Data flow for a measured display

1. `Gamut.from_cgats(path)` reads RGB + XYZ (or RGB + LAB) from a CGATS file
2. `from_xyz()`: expands measurements to the 726-vertex tessellation via exact RGB lookup (`_expand_colordata_to_tesselation`), extracts the measured white point, applies Bradford CAT from measured white to a luminance-scaled D50, converts to CIELab
3. `_from_lab_and_rgb()`: used when file has LAB directly; same tessellation expansion, no colorspace conversion
4. `volume()` / `intersect()` build a cylindrical map (cached on the `Gamut` object) then integrate

## Public API

```python
from cielab_gamut_tools import Gamut, SyntheticGamut, make_rgb_signals

# Reference gamuts
srgb       = SyntheticGamut.srgb()
bt2020     = SyntheticGamut.bt2020()
dci_p3     = SyntheticGamut.dci_p3()
display_p3 = SyntheticGamut.display_p3()
adobe_rgb  = SyntheticGamut.adobe_rgb()
custom     = SyntheticGamut(primaries_xy, white_xy, gamma=2.2)

# Load from file
gamut = Gamut.from_cgats("measurements.txt")

# Volume and coverage
volume   = srgb.volume()                                    # ~830,807
coverage = gamut.intersect(srgb).volume() / srgb.volume() * 100

# Normative ring metric
rings = gamut.compute_rings()          # (100, 360) C*_RSS array

# Measurement signals
signals = make_rgb_signals(m=11, bits=8)   # (602, 3) uint16

# Visualization
gamut.plot_surface()
gamut.plot_rings(reference=srgb)
```

## Implementation Status

The library and all CLI commands are fully implemented with no known gaps.

### Verified results
- `SyntheticGamut.srgb().volume()` → ~830,807 (MATLAB: 830,766, ~0.005% difference, within 1% tolerance)
- All three computation paths (direct, from measurement CGATS, from envelope CGATS) give identical results ✓
- Absolute-luminance measurements (Y ≈ 100 cd/m²) normalised correctly against their own white point ✓
- Reflective display (E Ink Sample 4) volume → ~1,776 (MATLAB: 1,776) ✓ — requires `ILLUMINATION_PERFECT_DIFFUSE_REFLECTOR_XYZ` white-point override
- BT.2020 volume > sRGB ✓
- Intersection commutativity: A∩B == B∩A ✓
- Self-intersection: A∩A == A ✓

## Critical Implementation Details

### 726 vs 602 vertices — do not confuse these counts

`make_tesselation()` produces **726 vertices** for the standard m=11 grid (6 × 11² = 726). Edge and corner vertices are replicated across adjacent faces so each face's triangle strip is self-contained. This matches MATLAB exactly.

**CGATS files must contain only 602 unique surface points** (6m² − 12m + 8 = 602 for m=11). The MATLAB reference deduplicates with `unique(rgb,'rows')` in `make_rgb_signals.m`.

In Python: `Gamut.to_cgats()` applies `np.unique(rgb_out, axis=0)` before writing. The internal `self.lab`, `self.rgb`, `self.xyz` arrays remain 726 entries. **Never remove the deduplication step from `to_cgats()`.**

### Expanding 602 measurements to 726 tessellation vertices

`_expand_colordata_to_tesselation()` in `gamut.py` matches MATLAB's `map_rows.m`. It first tries an exact integer-space RGB lookup (rounds both the measured grid and the tessellation vertices, matches rows exactly) — the correct path for all standards-compliant 602-point files. If any tessellation vertex has no exact match (non-standard grids), it falls back to scipy `LinearNDInterpolator` + nearest-neighbour for out-of-hull points.

### White-point normalization in from_xyz()

Matches MATLAB `make_gamut_envelope.m`. The measured white point is the XYZ row where all RGB channels are at their maximum. D50 is scaled to the same luminance: `d50_scaled = D50_WHITE_XYZ * white_xyz[1]`. Bradford CAT is applied from the measured white to `d50_scaled`, and `xyz_to_lab()` uses `d50_scaled` as its reference white. For normalised synthetic data (Y_white = 1) this is a no-op.

**Reflective display override (IDMS v1.3 §5.4):** When the CGATS metadata contains `ILLUMINATION_PERFECT_DIFFUSE_REFLECTOR_XYZ`, that value replaces the RGB-derived white point. For reflective displays (e-paper, print) the perfect diffuse reflector is the correct reference white — the display's maximum RGB patch (Y ≈ 24 for a typical e-paper) is far dimmer than the paper white (Y = 100), so using the RGB-derived white inflates all L* values by ~2× and the volume by ~4×. The override is applied in `from_xyz()` after the RGB-based detection, so emissive displays without the keyword are unaffected.

### Tesselation (geometry/tesselation.py)

1. **Vertex ordering for consistent winding:**
   - Bottom faces (value=0): `[Lower, J, K]`, `[K, Lower, J]`, `[J, K, Lower]`
   - Top faces (value=1): `[Upper, K, J]`, `[J, Upper, K]`, `[K, J, Upper]`

2. **Column-major flattening** to match MATLAB's `(:)` operator:
   ```python
   J, K = np.meshgrid(gsv, gsv)
   J = J.flatten('F')
   K = K.flatten('F')
   ```

3. **Triangle indices:** `[m, m+n, m+1]` and `[m+n, m+n+1, m+1]` where `m = n*n*s + n*q + p`

### Volume Calculation (geometry/volume.py)

Uses Möller-Trumbore ray-triangle intersection, NOT rasterization.

**Algorithm (matching `CIEtools/cielab_cylindrical_map.m`):**

1. Reorder Lab to `[a*, b*, L*]` to match MATLAB's Z matrix
2. For each L* slice (100 steps), find triangles spanning that L*
3. Batch all 360 ray directions into a single matrix multiply: `e2e1_2d @ all_dirs.T`
4. Pass `(n_tri, 360)` arrays to `_process_hue_loop_nb` (Numba JIT)
5. JIT loop: collect valid hits, sort ascending, apply parity filter, reverse to outside-in
6. Integrate: `V = Σ sign × t² × dL × dh / 2` (vectorised `np.sum`)

**Cylindrical map — storage format (cached on `Gamut` object):**
```python
_cylmap_counts:  uint8   (l_steps, h_steps)      # parity-filtered intersection count per cell
_cylmap_chroma:  float32 [sum(counts)]            # distances only, outside-in per cell, row-major
_cylmap_offsets: int32   [l_steps × h_steps]      # prefix-sum of counts for O(1) cell access
```

Signs are **implicit**: position within a cell determines sign (even index = outward = +1, odd = inward = −1). This is guaranteed by the parity filter: the outermost retained crossing always faces outward. Storing distances only halves memory and simplifies the UI transfer format.

**Cylindrical map — computation format (unpacked on demand):**
```python
cylmap:  float64  (l_steps, h_steps, max_k, 2)   # [...,0]=sign (explicit), [...,1]=distance
counts:  int64    (l_steps, h_steps)
```
`max_k = counts.max()` — data-driven, not a fixed constant. `_unpack_cylmap()` reconstructs explicit signs from position. `get_cylindrical_map()` always returns this dense form; callers are unchanged. The unpack is O(sum(counts)) and takes < 1 ms.

**No hard intersection limit.** `_process_hue_loop_nb` pre-allocates its working buffer to `h_steps × n_tri` (the absolute maximum before parity filtering). `_intersect_all_cells_nb` outputs to a buffer of depth `max_k_a + max_k_b` (a tight upper bound). The only ceiling is the number of triangles spanning a given L* slice.

**Parity invariant (checked after every build):** Within each L* slice all 360 rays originate from the same point (L*, 0, 0), which is either inside or outside the gamut cross-section. All intersection counts in a slice must therefore share the same parity. `_check_cylmap_parity()` issues a `warnings.warn` on violation (MATLAB silently ignores this condition; the volume result may be slightly inaccurate at the affected slice).

**Parity filter (matching MATLAB exactly):**
```python
flipped_signs  = cm[::-1, 0]
cumsum_flipped = np.cumsum(flipped_signs)
parity_check   = cumsum_flipped[::-1] * 2 - cm[:, 0]
keep = parity_check == 1
```

**Ray direction convention (sin,cos not cos,sin — puts 0° along +b* axis):**
```python
dir_2d = np.array([np.sin(hue_mid), np.cos(hue_mid)])
```

### Chromatic Adaptation

Bradford transform. Source white is the measured display white point; destination is the luminance-scaled D50. For synthetic gamuts (normalised, Y=1) the scaling is a no-op.

### RGB to XYZ Matrix (synthetic.py)

`_build_rgb_to_xyz_matrix()` returns `M` (not `M.T`). Used as `rgb @ M.T` for row-vector multiplication.

## Performance

~37× speedup over the original implementation. Optimisations in `geometry/volume.py`:
1. Packed cylmap cached on `Gamut` object (built once; unpack to dense is < 1 ms)
2. Vectorised hue loop: all 360 directions batched into a single matrix multiply per L* slice
3. Numba JIT `_process_hue_loop_nb`: per-cell hit-collect/sort/parity/pack loop; working buffer sized to `h_steps × n_tri` (no fixed limit)
4. Numba JIT `_intersect_all_cells_nb`: full 36,000-cell intersection double-loop; output depth `max_k_a + max_k_b` (no truncation possible)
5. Vectorised integration: single `np.sum` over masked dense array; `max_k` is `counts.max()` so the array is as small as the data allows
6. Numba warm-up at import: both JIT functions called with minimal dummy arrays at module load

## CLI

Two entry points for the same Typer app: `cielab-tools` and `cielab-gamut-tools`.

- `about` — standards compliance info, citation, algorithm description
- `calculate volume <gamut>...` — `--format text/json/csv`, `--standard`, `--quiet`
- `calculate coverage <dut> --reference <ref>[,<ref>...]` — single-ref verbose or multi-ref table
- `calculate compare <gamut>...` — volume+delta (default), `--reference` coverage mode, `--matrix` pairwise N×N table
- `plot rings <gamut>` — `--reference`, `--intersection`, `--output`, `--show`, `--dpi`
- `plot surface <gamut>...` — multiple gamuts overlaid on shared axes; `--output`, `--show`, `--dpi`, `--alpha`
- `generate rgb-signals` — `--grid`, `--bits`, `--format csv/cgats`
- `generate synthetic [gamut]` — `--primaries`, `--white`, `--gamma`, `--mode envelope/measurement/all`, `--output`

Named gamuts accepted everywhere: `srgb`, `bt.2020`, `dci-p3`, `display-p3`, `adobe-rgb`.

`_resolve.py` resolves a CLI argument to a `Gamut`: file path first, then named gamut, two-part error if neither matches.

## Reference Material

- **MATLAB implementation:** `../cielab-gamut-tools-m/` (also referred to as `gamut-volume-m/` in test fixtures)
- **Key MATLAB files:** `SyntheticGamut.m`, `CIELabGamut.m`, `GetVolume.m`, `make_gamut_envelope.m`, `map_rows.m`, `+CIEtools/cielab_cylindrical_map.m`, `+CIEtools/make_tesselation.m`
- **Gamut volume paper:** E. Smith, R. L. Heckaman, K. Lang, J. Penczek, J. Bergquist — JSID 28(6), 2020, 548–556. https://doi.org/10.1002/jsid.918
- **Gamut rings paper:** K. Masaoka, F. Jiang, M. D. Fairchild, R. L. Heckaman — JSID 28(3), 2020, 273–286. https://doi.org/10.1002/jsid.852
- **Gamut ring intersection paper:** K. Masaoka, E. Smith, K. Lang, B. Berkeley, J. Bergquist, J. Penczek — JSID 33(4), 2025, 231–245. https://doi.org/10.1002/jsid.2031
- **Standards:** IDMS v1.3, IEC 62977-3-5, IEC 62906-6-1

## Package Configuration

- **Python:** ≥3.10; **build:** hatchling; **layout:** src
- **Dependencies:** numpy, matplotlib, scipy, numba ≥0.57, typer ≥0.9, rich ≥13.0
- **Dev dependencies:** pytest, pytest-cov, mypy (strict), ruff, hypothesis
