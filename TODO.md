# TODO

Work items identified from standards review (IDMS v1.3, IEC 62977-3-5, IEC 62906-6-1)
and design planning (CLI_DESIGN.md, ARCHITECTURE.md).

Items are grouped by area and ordered by priority within each group.

---

## Library — Core Gaps

These are missing pieces in the Python library itself, independent of the CLI.

### 1. CGATS writer
**Priority: High — blocks `generate reference` and interop workflows.**

The library can read CGATS 17 format 2 but cannot write it. The standards define a
specific output format for the gamut envelope (CIELab D50 coordinates, with header
metadata). This is equivalent to `writeCGATS.m` in the MATLAB reference code and to
IDMS Code 5 (`Reference_sRGB_IEC_61966-2.1_gamut_envelope.txt`).

Required fields in output file:
- `SAMPLE_ID`, `LAB_L`, `LAB_A`, `LAB_B`
- Header: originator, description, creation date, number of samples
- Optionally: source RGB values (`RGB_R`, `RGB_G`, `RGB_B`)

Add to: `src/cielab_gamut_tools/io/cgats.py`

### 2. RGB signal generator (`make_rgb_signals`)
**Priority: High — needed for end-to-end measurement workflow.**

Generate the ordered set of RGB input signal values for display measurement. This is
the normative first step in all three standards (IDMS §5.32, IEC 62977-3-5 Annex A,
IEC 62906-6-1 Annex A.2), equivalent to IDMS Code 1 (`make_rgb_signals.m`).

The set is defined by grid divisions `m` per cube edge:
```
n = 6m² − 12m + 8
```
Standard sizes:
| m  | n    | Name |
|----|------|------|
| 11 | 602  | Normative reference set |
|  9 | 386  | Reduced (estimate only) |
|  7 | 218  | Reduced (estimate only) |
|  5 |  98  | Reduced (estimate only) |

Output: ordered array of (R, G, B) signal values, in the tessellation order that the
analysis code expects. Must support arbitrary bit depth (default 8-bit, 0–255).

Add to: `src/cielab_gamut_tools/io/` or a new `src/cielab_gamut_tools/measurement.py`

### 3. `compute_rings()` — public method
**Priority: Medium — needed for CLI `calculate` output and future `report` command.**

The gamut ring diagram is a normative metric in all three standards, not just a
visualisation. The ring radius per (L*, h) cell is defined as:

```
C*_RSS(L*, h) = sqrt(2 × cumsum(V(l, h)) / Δh)
```

Currently the ring data is computed internally inside `plot_rings()` but is not
exposed as a public API. A `Gamut.compute_rings()` method should return the (100, 360)
C\*_RSS array so it can be output as CSV/JSON by the CLI and consumed by the future
report system without going through matplotlib.

The intersection ring offset rendering (IEC 62906-6-1 Formula 3) should also be
implemented here and verified against the normative MATLAB code in Annex A.3.3 of
that standard.

Add to: `src/cielab_gamut_tools/gamut.py` (public method) and
`src/cielab_gamut_tools/geometry/volume.py` (underlying calculation)

### 4. Adobe RGB in `SyntheticGamut`
**Priority: Low — trivial addition.**

Adobe RGB (1998) is the worked example in IEC 62906-6-1 (Table B.1), which provides
a full 602-point CGATS reference dataset for it. Add as a named factory method
alongside `srgb()`, `bt2020()` etc.

Primary chromaticities (xy):
- R: (0.640, 0.330)   G: (0.210, 0.710)   B: (0.150, 0.060)
- White: D65 (0.3127, 0.3290)
- Gamma: 2.2

Add to: `src/cielab_gamut_tools/synthetic.py`

### 5. Sub-602-point XYZ interpolation — standards-compliant path
**Priority: Low — current method works; this is a compliance note.**

The current `_interpolate_xyz()` uses scipy scattered interpolation, which is more
general than the normative method. The standards specify:

- **General case** (IDMS §5.32, IEC 62977-3-5 Clause 6.6.1): linear interpolation in
  XYZ space to produce the full 602-point set, then tessellate and convert to Lab.
  Smaller grids must be reported as estimates with stated uncertainty.

- **8-point special case** (IEC 62977-3-5 Annex A.2): a specific 6-sub-gamut linear
  decomposition for displays that satisfy Grassmann additivity. Only valid when
  channel independence is confirmed at all viewing directions.

Action: Document the divergence in code comments and user-facing docs. Consider adding
a `method='linear'` option to `_interpolate_xyz()` that uses the normative linear
approach for transparency. The 8-point path is a lower priority given its limited
applicability.

---

## Library — Testing Gaps

### 6. Interactive test of `plot_rings()` and `plot_surface()`
**Priority: Medium — noted in CLAUDE.md as a known gap.**

Both plotting functions are written but have no automated or interactive test. Verify
they produce correct figures with real CGATS data. Add smoke tests (figure creation
without error) to the test suite. See `CLAUDE.md` §Known Gaps.

---

## CLI — Implementation

These depend on the library items above. Implement in the order listed.

### 7. CLI skeleton — Typer structure and `about` command
Set up the Typer app with command groups (`calculate`, `plot`, `generate`, `report`
stub, `ui` stub). Implement `about` first as it has no library dependencies and
validates the structure.

Add: `src/cielab_gamut_tools/cli/` package

### 8. `calculate volume` and `calculate coverage`
Wrap existing `Gamut.volume()` and `Gamut.intersect()`. Support `--format text/json/csv`
and `--standard` metadata. Multiple file support with tabulated output.

### 9. `calculate compare`
Pairwise comparison including `--matrix` mode.

### 10. `plot rings` and `plot surface`
Wrap existing plotting functions. Add `--mode intersection` for ring diagram (uses
`compute_rings()` from item 3). Support all style presets and output formats.

### 11. `generate test-pattern`
Wrap the RGB signal generator from item 2. Support `--grid`, `--bits`, `--format csv`.

### 12. `generate reference`
Wrap `SyntheticGamut` + `Gamut.to_cgats()` (needs CGATS writer from item 1).
Support all five named gamuts and custom primaries.

### 13. CSV output — all `calculate` commands
Ensure `--format csv` produces clean, header-rowed output suitable for direct import
into Excel. Use consistent column naming across all subcommands.

---

## Documentation

### 14. `STANDARDS.md`
Create a standards reference document listing:
- Full names, numbers, and scope of each standard
- IEC TC110 publication status (CDV numbers currently; update when final)
- Input data requirements per standard (602 points, Bradford CAT, etc.)
- Citation text for use in papers and reports

Confirm final IEC TC110 publication numbers with standards committee before finalising.

### 15. Update `CLAUDE.md`
Once items 1–5 above are implemented, update the Implementation Status section and
Known Gaps list.

---

## Future Features (not yet scheduled)

### F1. Web UI
See `ARCHITECTURE.md`. FastAPI + Vue 3 + Plotly.js. Requires CLI to be stable first.

### F2. Report generation (`report` command)
YAML-configured PDF/HTML reports. Details and format TBD with standards committee
and early users. Requires `compute_rings()` (item 3) and CGATS writer (item 1).

### F3. Multi-viewing-direction workflow
IEC 62977-3-5 §6.6.2 specifies CGV at multiple viewing angles (±15°, ±30°, ±45°,
±60° H; ±15°, ±30° V). The library correctly computes volume from any XYZ dataset;
the multi-direction workflow is a measurement and data-organisation concern rather
than an algorithmic one. A CLI workflow (batch CGATS files → volume vs. angle table)
would be useful for TV/monitor off-axis characterisation.

### F4. Bundled pre-computed cylindrical maps
Shipping `.pkl` files for the five named reference gamuts would speed up repeated
`calculate coverage` runs by skipping the cylmap build step. Worth profiling the
actual saving before adding build complexity.
