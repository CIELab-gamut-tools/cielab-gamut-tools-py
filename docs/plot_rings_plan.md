# `plot_rings` Feature Parity Plan

This document describes the full feature set of the MATLAB `PlotRings.m` reference
implementation and maps each feature to a proposed Python API. Features are grouped
by the parameter blocks in `PlotRings.m`. MATLAB line references are to
`gamut-volume-m/PlotRings.m` unless otherwise stated.

---

## Status summary

| Group | Feature | Status |
|---|---|---|
| Core rings | Ring line plot (test gamut) | **Done** |
| Core rings | Outer reference ring (dashed) | **Done** |
| Core rings | L* ring labels | **Done** |
| Core rings | Centre cross mark | **Done** |
| Core rings | Volume in title | **Done** |
| Core rings | Configurable `l_rings` / `ring_line` | **Done** |
| Colour bands | Test gamut colour bands | **Planned** |
| Colour bands | Reference colour bands | **Planned** |
| Reference | Per-ring reference/intersection overlay | **Planned** |
| Reference | Second reference gamut | **Planned** |
| Intersection | Intersection plot mode | **Planned** |
| Primaries | Primary colour arrow indicators | **Planned** (needs RGB data) |
| Decorations | Constant-chroma rings | **Planned** |
| Scatter | Scatter point data | **Planned** |
| Style | Configurable line styles | **Planned** |
| Style | Configurable label colours/indices | **Planned** |

---

## 1. Gamut ring format

### 1.1 `l_rings` — inner ring L* values
**MATLAB:** `LRings` parameter, default `10:10:90`. The outer ring at L*=100 is always
added. (PlotRings.m line 205, calcGamutRings.m line 37.)

**Python (current):** `l_rings: list[float] | None = None`, default
`np.arange(10, 100, 10)`. ✓ Matches MATLAB.

### 1.2 `ring_line` — line style for all gamut rings
**MATLAB:** `RingLine`, default `'k'`. (PlotRings.m line 54.)

**Python (planned):**
```python
ring_line: str = "k-"
```
Applied to every ring line including the outer one. Any matplotlib linestyle string.

### 1.3 `ref_line` — line style for the first reference outer ring
**MATLAB:** `RefLine`, default `'--k'`. Only the L*=100 ring is drawn for the reference
by default. (PlotRings.m line 55, lines 403–406.)

**Python (planned):**
```python
ref_line: str = "--k"
```

### 1.4 `ref2_line` — line style for the second reference outer ring
**MATLAB:** `Ref2Line`, default `':k'`. (PlotRings.m line 56, lines 408–411.)

**Python (planned):**
```python
ref2_line: str = ":k"
```

### 1.5 `l_label_indices` — which rings to label
**MATLAB:** `LLabelIndices`, default `[1, 5]` (1-indexed into `[LRings, 100]`).
(PlotRings.m lines 207, 365–386.)

**Python (planned):**
```python
l_label_indices: list[int] = [0, 4]   # 0-indexed, default labels L*=10 and L*=50
```
Pass `[]` to suppress all labels.

### 1.6 `l_label_colors` — label text colours
**MATLAB:** `LLabelColors`, default `'default'` which makes the outermost label black
and all others white. Also accepts a colour name, an `n×3` RGB matrix, or a cell array.
(PlotRings.m lines 208, 368–386.)

**Python (planned):**
```python
l_label_colors: str | list | None = "default"
# "default" → outermost label black, inner labels white
# A single matplotlib colour string → applied to all labels
# A list of matplotlib colour specs → one per label
```

---

## 2. Colour bands

The coloured wedge-shaped fills between consecutive rings give the plot its distinctive
appearance. The fill colour at each hue matches that hue's approximate sRGB colour at a
specified lightness, making it easy to read off hue angle.

Two independent sets of bands exist:
- **Test bands** — filled from each inner ring out to the test gamut boundary at that L* level.
- **Reference bands** — filled from the inner ring out to whichever gamut (test or reference) is larger at each hue, shown only where the reference extends beyond the test gamut. Only visible when `intersection_plot=True`.

### 2.1 `show_bands` — enable test gamut colour bands
**MATLAB:** `ShowBands`, default `true`. (PlotRings.m lines 83–84, 332–346.)

**Python (planned):**
```python
show_bands: bool = True
```

### 2.2 `band_chroma` — saturation of band hue colours
**MATLAB:** `BandChroma`, default `50`. Set to `0` for monochrome bands.
(PlotRings.m lines 87–88.)

**Python (planned):**
```python
band_chroma: float = 50.0
```
The Lab `a*` and `b*` components of the fill colour are scaled to this chroma value
before converting to sRGB via `lab_to_srgb`.

### 2.3 `band_ls` — lightness of bands (per band or range)
**MATLAB:** `BandLs`, default `[20, 90]`. If a 2-element vector, linearly interpolates
across all bands (inner bands dark, outer bands light). If `N`-element, one value per
band. (PlotRings.m lines 89–94, `normRange` helper lines 603–613.)

**Python (planned):**
```python
band_ls: float | list[float] = (20.0, 90.0)
# 2-element tuple → linearly interpolated across all bands
# list of N values → one per band (must match number of bands)
```

### 2.4 `band_hue` — hue of band fill colour
**MATLAB:** `BandHue`, default `'match'` (hue matches the hue angle of the chart sector).
Can also be a fixed hue angle (degrees, 0 = `a*=1, b*=0`, 90 = `a*=0, b*=1`).
(PlotRings.m lines 95–101.)

**Python (planned):**
```python
band_hue: float | Literal["match"] = "match"
```

### 2.5 `show_ref_bands` — enable reference colour bands
**MATLAB:** `ShowRefBands`, default `true`. Only active when `intersection_plot=True`.
Shows where the reference gamut extends beyond the test gamut. (PlotRings.m lines 103–107,
315–329.)

**Python (planned):**
```python
show_ref_bands: bool = True
```

### 2.6 `ref_band_chroma`, `ref_band_ls`, `ref_band_hue`
**MATLAB:** `RefBandChroma` (default `0`), `RefBandLs` (default `[30, 98]`),
`RefBandHue` (default `'match'`). Same semantics as the test-gamut equivalents.
(PlotRings.m lines 108–117.)

**Python (planned):**
```python
ref_band_chroma: float = 0.0
ref_band_ls: float | list[float] = (30.0, 98.0)
ref_band_hue: float | Literal["match"] = "match"
```

### Implementation notes for colour bands
- **Triangulation:** MATLAB fills bands using a triangle strip. For each band between
  ring `n` and ring `n+1`, the inner and outer boundary points are interleaved:
  `xc = reshape([x_inner; x_outer], [], 1)` and a triangle index array
  `TRI = [1:lim; 2:lim 1; 3:lim 1:2]` (PlotRings.m lines 320–329).
  In Python, use `matplotlib.patches.Polygon` or `ax.fill` per sector, or build a
  `PolyCollection` over all sectors at once for performance.
- **Colour per vertex:** MATLAB uses `patch(..., 'FaceVertexCData', rgb, 'FaceColor',
  'interp')` so the colour smoothly interpolates across the hue angle.
  In Python, the closest equivalent is a `PolyCollection` with per-face colours
  (not per-vertex interpolation). For reasonable `h_steps=360`, per-sector fills
  are visually indistinguishable from the MATLAB output.
- **`lab_to_srgb`:** Requires a Python equivalent of MATLAB's `lab2srgb`. The existing
  `colorspace` module has `xyz_to_lab` and `lab_to_xyz` (implicitly); add
  `lab_to_srgb(lab) → ndarray` that converts via XYZ → linear RGB → gamma-encoded sRGB,
  clamped to [0, 1]. Used only for display colours, not gamut calculation.

---

## 3. Reference gamut options

### 3.1 `reference` (second positional argument)
**MATLAB:** `ref` optional positional argument. (PlotRings.m line 197.)

**Python (current):** `reference: Gamut | None = None`. ✓

### 3.2 `reference2` — second reference gamut
**MATLAB:** `ref2` optional positional argument. Its outer (L*=100) ring is drawn with
`Ref2Line` style. (PlotRings.m lines 198, 408–411.)

**Python (planned):**
```python
reference2: Gamut | None = None
```

### 3.3 `ring_reference` — per-ring reference overlay
**MATLAB:** `RingReference`, default `'none'`. Options:
- `'none'` — only outer ring of reference shown (current behaviour).
- `'ref'` — all inner rings of the reference gamut are drawn inside the test rings.
- `'intersection'` — all inner rings show the intersection of test and reference.

Uses `calcSubRings` (PlotRings.m lines 585–593) which maps the sub-gamut's cumulative
volume into the coordinate system of the outer reference rings, clamping to the outer
ring boundary. (PlotRings.m lines 78–79, 274–287.)

**Python (planned):**
```python
ring_reference: Literal["none", "ref", "intersection"] = "none"
```

Requires implementing `_calc_sub_rings(outer_rings, sub_gamut)` matching
`calcSubRings` in PlotRings.m:
```
r = sqrt(min(r2_outer[1:], (r2_sub[1:] - r2_sub[:-1]) + r2_outer[:-1]))
```

### 3.4 `intersection_plot` — full intersection plot mode
**MATLAB:** `IntersectionPlot`, default `false`. When true, the reference gamut rings
form the outer boundary and the test gamut's area is shown inside them. Forces
`intersect_gamuts=True`. (PlotRings.m lines 67–69, 260–287.)

**Python (planned):**
```python
intersection_plot: bool = False
```

### 3.5 `intersect_gamut` — pre-intersect the test gamut
**MATLAB:** `IntersectGamuts`, default `false`. If `true`, the displayed test gamut is
replaced by `IntersectGamuts(test, ref)` before plotting (but the original volume is
retained for the title). (PlotRings.m lines 70–73, 261–268.)

**Python (planned):**
```python
intersect_gamut: bool = False
```

### 3.6 `intersection_line` — line style for the intersection boundary
**MATLAB:** `IntersectionLine`, default `''` (no line). Only drawn when
`intersection_plot=True`. (PlotRings.m lines 69, 354–357.)

**Python (planned):**
```python
intersection_line: str = ""   # empty = no line drawn
```

---

## 4. Primary colour indicators

Arrows pointing outward from the plot at the hue angle of each primary colour (R, G, B
and optionally C, M, Y). Arrowhead colour approximates the actual observed primary
colour in sRGB.

**Prerequisite:** The Python `Gamut` class currently does not store the original RGB
measurement data. These features require adding a `rgb` attribute (shape `(N, 3)`) and
a `lab` attribute to `Gamut` (or at least caching the full Lab array of measured patches,
not just the surface tessellation). The MATLAB gamut struct carries `.RGB`, `.LAB`, and
`.RGBmax` fields for exactly this purpose.

### 4.1 `primaries` — which test gamut primaries to show
**MATLAB:** `Primaries`, default `'rgb'`. Options: `'none'`, `'rgb'` (R, G, B only),
`'all'` (R, G, B, C, M, Y). (PlotRings.m lines 140, 415–422.)

**Python (planned):**
```python
primaries: Literal["none", "rgb", "all"] = "rgb"
```

### 4.2 `primary_color` — how to colour the arrows
**MATLAB:** `PrimaryColor` / `PrimaryColour`, default `'output'` (arrow colour matches
the gamut's Lab value converted to sRGB). `'input'` uses the nominal primary colour
(pure R, G, B etc.). (PlotRings.m lines 143–148, 499–505.)

**Python (planned):**
```python
primary_color: Literal["input", "output"] = "output"
```

### 4.3 `primary_chroma` — radial distance of the arrowhead
**MATLAB:** `PrimaryChroma`, default `950`. `'auto'` sets it to `max_ring_chroma + 100`.
(PlotRings.m lines 147–149, 300–304.)

**Python (planned):**
```python
primary_chroma: float | Literal["auto"] = 950.0
```

### 4.4 `primary_origin` — where the arrow starts
**MATLAB:** `PrimaryOrigin`, default `'centre'`. `'ring'` starts the arrow at the outer
ring boundary at that hue. (PlotRings.m lines 150–151, 519–525.)

**Python (planned):**
```python
primary_origin: Literal["centre", "ring"] = "centre"
```

### 4.5 `ref_primaries`, `ref_primary_chroma`, `ref_primary_origin`
**MATLAB:** `RefPrimaries` (default `'none'`), `RefPrimaryChroma` (default `'auto'`),
`RefPrimaryOrigin` (default `'ring'`). Same semantics as test primaries; drawn as grey
lines with coloured arrowheads, with a dotted arc linking test and reference primary
arrows when both are shown. (PlotRings.m lines 154–163, 451–490.)

**Python (planned):**
```python
ref_primaries: Literal["none", "rgb", "all"] = "none"
ref_primary_chroma: float | Literal["auto"] = "auto"
ref_primary_origin: Literal["centre", "ring"] = "ring"
```

### Implementation notes for primaries
- Arrows are drawn with `ax.annotate` or `ax.quiver`.
- Finding a primary: scan `gamut.rgb` for the row where one channel is 1 and the others
  are 0 (for R, G, B) or one is 0 and the others are 1 (for C, M, Y). The corresponding
  Lab row gives the arrow direction. See PlotRings.m lines 453–458 and 494–498.
- The dotted arc linking test and reference primary arrows: drawn as
  `plot(0.95*chroma*sin(angles), 0.95*chroma*cos(angles), ':k')`.
  (PlotRings.m lines 532–535.)

---

## 5. Decorations

### 5.1 `cent_mark` — centre cross marker
**MATLAB:** `CentMark`, default `'+k'`. Set to `None` to suppress.
(PlotRings.m lines 119–120, 390–392.)

**Python (current):** Hardcoded `"+k"`. Planned:
```python
cent_mark: str | None = "+k"
cent_mark_size: float = 20.0
```

### 5.2 `chroma_rings` — constant-chroma reference circles
**MATLAB:** `ChromaRings`, default `[]` (none). Draws grey circles at the given C* radii,
plotted behind the gamut rings at `z=-2`. (PlotRings.m lines 127–128, 395–399.)

**Python (planned):**
```python
chroma_rings: list[float] = []
```
Drawn as grey circles (`color="0.7"`) behind the rings.

---

## 6. Scatter point data

**MATLAB:** `ScatterData`, an `N×3` matrix of L*, a*, b* data. Each point is mapped into
the ring coordinate system — its contribution to the ring area at its hue and L* is
computed and used to derive a radius, then plotted as an image with transparency
proportional to log-density. (PlotRings.m lines 166–168, 551–574.)

This is a complex feature involving 2D density estimation on a non-linear grid.

**Python (planned):**
```python
scatter_data: np.ndarray | None = None   # shape (N, 3): [L*, a*, b*]
```

Implementation should match the MATLAB binning and density-to-alpha mapping closely
(log scale: `alpha = (log(density) + 2) / (log(max_density) + 2)`).

---

## 7. Proposed unified Python API

Pulling all the above together, the full signature for `plot_rings` would be:

```python
def plot_rings(
    gamut: Gamut,
    reference: Gamut | None = None,
    reference2: Gamut | None = None,
    *,
    # Ring format
    l_rings: list[float] | None = None,          # default: 10:10:90
    l_label_indices: list[int] = [0, 4],          # 0-indexed into [l_rings..., 100]
    l_label_colors: str | list | None = "default",
    ring_line: str = "k",
    ref_line: str = "--k",
    ref2_line: str = ":k",
    # Colour bands
    show_bands: bool = True,
    band_chroma: float = 50.0,
    band_ls: float | tuple[float, float] | list[float] = (20.0, 90.0),
    band_hue: float | Literal["match"] = "match",
    show_ref_bands: bool = True,
    ref_band_chroma: float = 0.0,
    ref_band_ls: float | tuple[float, float] | list[float] = (30.0, 98.0),
    ref_band_hue: float | Literal["match"] = "match",
    # Reference options
    ring_reference: Literal["none", "ref", "intersection"] = "none",
    intersection_plot: bool = False,
    intersect_gamut: bool = False,
    intersection_line: str = "",
    # Primary indicators
    primaries: Literal["none", "rgb", "all"] = "rgb",
    primary_color: Literal["input", "output"] = "output",
    primary_chroma: float | Literal["auto"] = 950.0,
    primary_origin: Literal["centre", "ring"] = "centre",
    ref_primaries: Literal["none", "rgb", "all"] = "none",
    ref_primary_chroma: float | Literal["auto"] = "auto",
    ref_primary_origin: Literal["centre", "ring"] = "ring",
    # Decorations
    cent_mark: str | None = "+k",
    cent_mark_size: float = 20.0,
    chroma_rings: list[float] = [],
    # Scatter
    scatter_data: np.ndarray | None = None,
    # Axes
    ax: Axes | None = None,
    clear_axes: bool = True,
) -> Figure:
```

The `Gamut.plot_rings()` method passes all keyword arguments through to this function.

---

## 8. Implementation order (suggested)

1. **Colour bands** (§2) — highest visual impact, no prerequisites beyond what exists.
   Requires adding `lab_to_srgb()` to `colorspace/`.
2. **Configurable line styles and label options** (§1.2–1.6) — low effort, high
   completeness value.
3. **Constant-chroma rings** (§5.2) — trivial to add.
4. **Centre mark options** (§5.1) — trivial.
5. **Second reference gamut** (§3.2) — small addition to existing reference logic.
6. **Per-ring reference/intersection overlay** (§3.3) — requires `_calc_sub_rings`.
7. **Intersection plot mode** (§3.4–3.6) — builds on §3.3.
8. **Primary colour indicators** (§4) — requires adding `rgb` storage to `Gamut`.
9. **Scatter point data** (§6) — complex, low priority.

---

## 9. Internal helper needed: `_calc_sub_rings`

Several features (§3.3, §3.4) need the MATLAB `calcSubRings` function, which maps one
gamut's cumulative volume into the coordinate frame of another gamut's rings:

```
# Python equivalent of calcSubRings(rings, sub_gamut)
# rings: the outer reference ring structure
# sub_gamut: the gamut whose area is to be shown within the reference rings
r2_sub = 2 * cumsum(volmap_sub, axis=0) / dH          # sub gamut r² at each L*
ri2 = interp(L_query, L_grid, vstack([zeros, r2_sub])) # at ring L* levels
rg2 = rings.r2                                          # outer reference r²
r = sqrt(minimum(rg2[1:], (ri2[1:] - ri2[:-1]) + rg2[:-1]))
```

This is PlotRings.m lines 585–593 (`calcSubRings` local function).

---

## 10. Internal helper needed: `lab_to_srgb`

Colour bands require converting Lab (L*, a*, b*) → sRGB [0, 255]. The MATLAB `lab2srgb`
is the inverse of the measurement pipeline. In Python:

```python
# colorspace/lab.py (new function)
def lab_to_srgb(lab: ndarray) -> ndarray:
    """Convert CIELab (D50) to sRGB [0, 255], clamped."""
    xyz_d50 = lab_to_xyz(lab)                  # existing inverse of xyz_to_lab
    xyz_d65 = adapt_d50_to_d65(xyz_d50)        # Bradford adaptation (inverse of current)
    linear = xyz_to_srgb_linear(xyz_d65)       # 3×3 matrix multiply
    srgb = srgb_gamma_encode(linear)           # existing srgb.py
    return np.clip(srgb * 255, 0, 255)
```

Relevant MATLAB: `CIEtools/lab2srgb.m` (or equivalent, referenced at PlotRings.m
lines 325, 342).
