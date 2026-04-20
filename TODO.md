# TODO

Work items identified from standards review (IDMS v1.3, IEC 62977-3-5, IEC 62906-6-1)
and design planning (CLI_DESIGN.md, ARCHITECTURE.md).

Items are grouped by area and ordered by priority within each group.

---

## Library — Core Gaps

These are missing pieces in the Python library itself, independent of the CLI.

### 1. CGATS writer ✅ DONE
**Completed.** The I/O layer is now fully general:

- `read_cgats()` returns `CgatsData(rgb, xyz, lab, metadata)` — detects all
  colorspace columns; any field is `None` if absent in the file.
- `write_cgats()` accepts `rgb=`, `xyz=`, `lab=` in any combination; writes
  whichever are provided in standard column order.
- `Gamut.from_cgats()` handles both CGE_MEASUREMENT (RGB+XYZ) and CGE_ENVELOPE
  (RGB+LAB) files. Missing RGB raises `ValueError` with `warnings.warn`.
- `Gamut.to_cgats(mode=)` — `"envelope"` (default), `"measurement"`, `"all"`.
  RGB is scaled to [0, 255] on output. XYZ is retained from construction.
- `SyntheticGamut.to_cgats()` delegates to the underlying `Gamut`.
- `_looks_like_field_names()` now requires at least one data column (RGB/XYZ/LAB)
  to match — avoids false positives on `KEYWORD SampleID` metadata lines.

### 2. RGB signal generator (`make_rgb_signals`) ✅ DONE
**Completed.** `make_rgb_signals(m=11, bits=8)` in
`src/cielab_gamut_tools/measurement.py`, exported from the top-level package.
Supports all standard grid sizes (m=5/7/9/11) and arbitrary bit depth. Deduplicates
tessellation vertices to the normative n = 6m²−12m+8 unique points in lexicographic
order, matching MATLAB's `unique(rgb,'rows')`.

### 3. `compute_rings()` — public method ✅ DONE
**Completed.** `Gamut.compute_rings(l_steps=100, h_steps=360)` and
`SyntheticGamut.compute_rings()` added. Backed by
`compute_cylindrical_rings()` in `src/cielab_gamut_tools/geometry/volume.py`.
Returns a `(l_steps, h_steps)` array of C\*_RSS values (non-decreasing along L*,
outer ring area equals total gamut volume).

The intersection ring offset rendering (IEC 62906-6-1 Formula 3) is not yet
implemented — deferred until the standard's Annex A.3.3 can be verified.

### 4. Adobe RGB in `SyntheticGamut` ✅ DONE
**Completed.** `SyntheticGamut.adobe_rgb()` added to `synthetic.py`. Primaries,
white point (D65), and gamma (2.2) match IEC 62906-6-1 Table B.1. Volume falls
between sRGB and BT.2020 as expected.

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

### 6. Interactive test of `plot_rings()` and `plot_surface()` ✅ DONE
**Completed.** Smoke tests added in `tests/test_measurement.py`: figure creation
without error for `plot_surface()`, `plot_rings()`, `plot_rings()` with reference,
intersection-plot mode, and Adobe RGB. All pass with the Agg backend.

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

### F5. Intersection gamut serialisation (CGE_CYLMAP)

An intersected `Gamut` has no RGB surface mapping — it exists only as a cylindrical
map. To save/restore intersection results without recomputing, a flat serialisation
of the cylindrical map is needed. Proposed CGATS-style format:

```
IDMS_FILE_TYPE   CGE_CYLMAP
BEGIN_DATA_FORMAT
SampleID LAB_L HUE CHROMA DIRECTION
END_DATA_FORMAT
```

Where `DIRECTION = +1` means the ray exits the gamut body at that point (outward
surface hit) and `-1` means it enters (inward). `CHROMA` is the radial distance from
the achromatic axis. `LAB_L` and `HUE` are the L* level and hue angle (degrees) for
that cylindrical map cell. Each cell may contribute 0–4 rows (MAX_K = 4).

This format is sufficient to reconstruct volume, ring plots, and coverage without
re-running the full ray-triangle intersection. Any result produced without RGB data
is non-standards-compliant and should be flagged as such.

### F4. Bundled pre-computed cylindrical maps
Shipping `.pkl` files for the five named reference gamuts would speed up repeated
`calculate coverage` runs by skipping the cylmap build step. Worth profiling the
actual saving before adding build complexity.
