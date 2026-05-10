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
pytest                                       # all tests
pytest tests/test_gamut.py                   # single file
pytest tests/test_gamut.py::TestVolume       # single class
pytest tests/test_gamut.py::TestVolume::test_srgb  # single test
pytest --cov=cielab_gamut_tools              # with coverage

# Lint / format
ruff check src tests                         # lint
ruff format src tests                        # format
mypy src                                     # type check
```

The test suite runs in ~700 ms (Numba JIT warms up at import).

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
        ├── plot.py       # stub (not implemented)
        └── generate.py   # stub (not implemented)
```

### Data flow for a measured display

1. `Gamut.from_cgats(path)` reads RGB + XYZ (or RGB + LAB) from a CGATS file
2. `from_xyz()`: interpolates XYZ to the 726-vertex tessellation, applies Bradford D65→D50, converts to CIELab
3. `_from_lab_and_rgb()`: used when file has LAB directly; same tessellation reconstruction, no colorspace conversion
4. `volume()` / `intersect()` build a cylindrical map (cached on the `Gamut` object) then integrate

## Public API

```python
from cielab_gamut_tools import Gamut, SyntheticGamut, make_rgb_signals

# Reference gamuts
srgb   = SyntheticGamut.srgb()
bt2020 = SyntheticGamut.bt2020()
dci_p3 = SyntheticGamut.dci_p3()
display_p3 = SyntheticGamut.display_p3()
adobe_rgb  = SyntheticGamut.adobe_rgb()
custom = SyntheticGamut(primaries_xy, white_xy, gamma=2.2)

# Load from file
gamut = Gamut.from_cgats("measurements.txt")

# Volume and coverage
volume   = srgb.volume()                                   # ~830,330
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

Everything in the library is implemented and tested. Known gaps:

1. **Intersection ring offset** — `compute_rings()` does not implement the IEC 62906-6-1 Formula 3 intersection ring offset variant; deferred until Annex A.3.3 can be verified against MATLAB
2. **CLI `plot` subcommands** — `plot rings` and `plot surface` are scaffolded but not implemented; need to wrap `Gamut.plot_rings()` / `Gamut.plot_surface()` with `--output`, `--show`, `--reference`, `--dpi` flags
3. **CLI `generate` subcommands** — `generate test-pattern` (wraps `make_rgb_signals`) and `generate reference` (wraps `SyntheticGamut` + `to_cgats`) are scaffolded but not implemented

### Verified results
- `SyntheticGamut.srgb().volume()` → ~830,330 (MATLAB: 830,766, ~0.05% difference, within 1% tolerance)
- BT.2020 volume > sRGB ✓
- Intersection commutativity: A∩B == B∩A ✓
- Self-intersection: A∩A == A ✓

## Critical Implementation Details

### 726 vs 602 vertices — do not confuse these counts

`make_tesselation()` produces **726 vertices** for the standard m=11 grid (6 × 11² = 726). Edge and corner vertices are replicated across adjacent faces so each face's triangle strip is self-contained. This matches MATLAB exactly.

**CGATS files must contain only 602 unique surface points** (6m² − 12m + 8 = 602 for m=11). The MATLAB reference deduplicates in `make_rgb_signals.m` with `unique(rgb,'rows')`.

In Python: `Gamut.to_cgats()` applies `np.unique(rgb_out, axis=0)` before writing. The internal `self.lab`, `self.rgb`, `self.xyz` arrays remain 726 entries. **Never remove the deduplication step from `to_cgats()`.**

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
5. JIT loop: collect valid hits, sort by distance, apply parity filter
6. Integrate: `V = Σ sign × t² × dL × dh / 2` (vectorised `np.sum`)

**Cylindrical map format:**
```python
cylmap:  np.ndarray  shape (l_steps, h_steps, MAX_K, 2)  # [...,0]=sign, [...,1]=distance
counts:  np.ndarray  shape (l_steps, h_steps)             # valid entries per cell
```
`MAX_K = 4`. Cached on the `Gamut` object and shared between `volume()` and `intersect()` calls.

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

Bradford transform. Source white from the gamut's white point (D65 for sRGB/BT.2020/etc.), destination always D50 for Lab conversion.

### RGB to XYZ Matrix (synthetic.py)

`_build_rgb_to_xyz_matrix()` returns `M` (not `M.T`). Used as `rgb @ M.T` for row-vector multiplication.

## Performance

~37× speedup over the original implementation. Optimisations in `geometry/volume.py`:
1. Cylindrical map cached on `Gamut` object
2. Vectorised hue loop: all 360 directions batched into a single matrix multiply per L* slice
3. Numba JIT `_process_hue_loop_nb`: per-cell hit-collect/sort/parity loop
4. Numba JIT `_intersect_all_cells_nb`: full 36,000-cell intersection double-loop, pre-allocated temp buffer
5. Vectorised integration: single `np.sum` over masked dense array
6. Numba warm-up at import: both JIT functions called with minimal dummy arrays at module load

## CLI

Two entry points for the same Typer app: `cielab-tools` and `cielab-gamut-tools`.

- `about` — standards compliance info, citation, algorithm description
- `calculate volume <gamut>...` — `--format text/json/csv`, `--standard`, `--quiet`
- `calculate coverage <dut> --reference <ref>[,<ref>...]` — single-ref verbose or multi-ref table
- `calculate compare <gamut>...` — volume+delta (default), `--reference` coverage mode, `--matrix` pairwise N×N table

Named gamuts accepted everywhere: `srgb`, `bt.2020`, `dci-p3`, `display-p3`, `adobe-rgb`.

`_resolve.py` resolves a CLI argument to a `Gamut`: file path first, then named gamut, two-part error if neither matches.

## Reference Material

- **MATLAB implementation:** `../cielab-gamut-tools-m/` (also referred to as `gamut-volume-m/` in test fixtures)
- **Key MATLAB files:** `SyntheticGamut.m`, `CIELabGamut.m`, `GetVolume.m`, `+CIEtools/cielab_cylindrical_map.m`, `+CIEtools/make_tesselation.m`
- **Publication:** Smith et al., Journal of the Society for Information Display, 2020
- **Standards:** IDMS v1.3, IEC 62977-3-5, IEC 62906-6-1

## Package Configuration

- **Python:** ≥3.10; **build:** hatchling; **layout:** src
- **Dependencies:** numpy, matplotlib, scipy, numba ≥0.57, typer ≥0.9, rich ≥13.0
- **Dev dependencies:** pytest, pytest-cov, mypy (strict), ruff, hypothesis
