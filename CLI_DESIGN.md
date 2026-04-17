# CLI Design Plan for cielab-gamut-tools

## Overview

Command-line interface for gamut analysis, visualisation, and reporting. Designed for display
professionals who need quick, scriptable, standards-compliant analysis.

## Entry Points

Two registered `console_scripts` pointing to the same entry point — no extra code, just two
lines in `pyproject.toml`:

| Command | Purpose |
|---|---|
| `cielab-gamut-tools` | Canonical name — used in documentation, standards citations, packaging |
| `cielab-tools` | Short alias — everyday use |

```toml
# pyproject.toml
[project.scripts]
cielab-gamut-tools = "cielab_gamut_tools.cli:main"
cielab-tools       = "cielab_gamut_tools.cli:main"
```

The web UI (when implemented) is launched via a subcommand: `cielab-tools ui`.

## Command Groups

```
cielab-tools
├── calculate     # Analysis and metrics
├── plot          # Visualisation (2D/3D)
├── generate      # Create reference gamuts and test patterns
├── report        # [FUTURE] Automated report generation
└── about         # Standards compliance and citation information
```

---

## 1. CALCULATE - Analysis and Metrics

**Top-level command:** `cielab-tools calculate <metric> <file> [options]`

### Subcommands

#### `volume`
Calculate gamut volume.

```bash
# Basic volume
cielab-tools calculate volume display.txt
> Volume: 956 234 (ΔE*ab)³

# Multiple files — tabulated output
cielab-tools calculate volume display1.txt display2.txt display3.txt
> File          Volume (ΔE*ab)³
> display1.txt      956 234
> display2.txt      892 103
> display3.txt    1 024 567

# CSV output (for Excel / spreadsheet workflows)
cielab-tools calculate volume display1.txt display2.txt --format csv
> file,volume_dEab3
> display1.txt,956234
> display2.txt,892103

# JSON with metadata
cielab-tools calculate volume display.txt --json
> {"file": "display.txt", "volume": 956234, "unit": "deltaE_ab_cubed"}

# Standards-compliant JSON output
cielab-tools calculate volume display.txt --standard IDMS --json
> {
>   "file": "display.txt",
>   "volume": 956234,
>   "unit": "deltaE_ab_cubed",
>   "standard": "ICDM IDMS v1.3 §5.32.1",
>   "method": "cylindrical_integration",
>   "calculated": "2026-04-17T10:23:45Z"
> }
```

#### `coverage`
Calculate coverage of reference gamut(s).

```bash
# sRGB coverage
cielab-tools calculate coverage display.txt --reference srgb
> sRGB coverage: 98.3%
> Display volume:     956 234 (ΔE*ab)³
> sRGB volume:        830 331 (ΔE*ab)³
> Intersection:       816 236 (ΔE*ab)³

# Multiple references
cielab-tools calculate coverage display.txt --reference srgb,bt2020,dci-p3,adobe-rgb
> sRGB coverage:      98.3%
> BT.2020 coverage:   67.2%
> DCI-P3 coverage:    95.1%
> Adobe RGB coverage: 88.4%

# CSV output
cielab-tools calculate coverage display.txt --reference srgb,bt2020,dci-p3 --format csv
> reference,coverage_pct,dut_volume,ref_volume,intersection_volume
> sRGB,98.3,956234,830331,816236
> BT.2020,67.2,956234,1389765,642876
> DCI-P3,95.1,956234,924832,879955

# Custom reference from file
cielab-tools calculate coverage display.txt --reference custom_ref.txt

# Detailed JSON output
cielab-tools calculate coverage display.txt --reference srgb --json --standard IEC-62977
```

#### `compare`
Compare multiple displays.

```bash
# Compare volumes
cielab-tools calculate compare display1.txt display2.txt display3.txt
> Gamut Comparison:
> display1.txt: 956 234
> display2.txt: 892 103  (−6.7% vs display1)
> display3.txt: 1 024 567 (+7.2% vs display1)

# CSV output
cielab-tools calculate compare display1.txt display2.txt display3.txt --format csv
> file,volume_dEab3,delta_pct_vs_first
> display1.txt,956234,0.0
> display2.txt,892103,-6.7
> display3.txt,1024567,7.2

# Compare coverage against a reference
cielab-tools calculate compare display1.txt display2.txt --reference srgb
> sRGB Coverage Comparison:
> display1.txt: 98.3%  (intersection: 816 236)
> display2.txt: 94.1%  (intersection: 781 420)

# Matrix comparison (all pairwise intersections)
cielab-tools calculate compare display1.txt display2.txt display3.txt --matrix
> Pairwise Intersections (% of row gamut covered by column):
>              display1  display2  display3
> display1         100%      89%      92%
> display2          87%     100%      85%
> display3          91%      88%     100%

# Matrix as CSV
cielab-tools calculate compare display1.txt display2.txt display3.txt --matrix --format csv
```

### Common Options

- `--output <file>`: Write results to file (inferred format from extension, or use `--format`)
- `--format <format>`: Output format: `text` (default), `json`, `csv`
- `--standard <std>`: Append standards traceability metadata — see [Standards Compliance](#standards-compliance)
- `--reference <gamut>`: Reference gamut(s): `srgb`, `bt2020`, `dci-p3`, `display-p3`,
  `adobe-rgb`, or a path to a CGATS file
- `--precision <n>`: Decimal places for numeric output (default: 1)
- `--quiet`: Output values only, no labels (for scripting/piping)

### Standards Compliance

**All calculations are standards-compliant by design.** This implementation is the Python
port of the MATLAB reference code on which the following standards are based:

| Flag value | Standard |
|---|---|
| `IDMS` | ICDM Information Display Measurements Standard v1.3, §5.32 |
| `IEC-62977` | IEC 62977-3-5 — Electronic displays: Colour capabilities |
| `IEC-62906` | IEC 62906-6-1 — Displays: Colour gamut intersection visualisation |

When `--standard` is supplied:
- Adds the full standard name and version to output metadata
- Includes method, calculation timestamp, and algorithm reference
- JSON output provides a complete traceability record
- Warns if input data does not meet standard requirements (e.g. fewer than 602 patches)

For complete standards compliance information: `cielab-tools about`

---

## 2. PLOT - Visualisation

**Top-level command:** `cielab-tools plot <type> <file> [options]`

### Subcommands

#### `rings` (2D gamut boundaries at L* slices — gamut ring diagram)

The gamut ring diagram is a normative visualisation defined in IDMS §5.32.3 and
IEC 62906-6-1. Each ring represents the gamut boundary at a 10-unit L* interval; ring area
is proportional to gamut volume for that slice.

```bash
# Preview (opens window)
cielab-tools plot rings display.txt --show

# Save to file
cielab-tools plot rings display.txt --output figure.png

# With reference overlay
cielab-tools plot rings display.txt --reference srgb --output figure.eps --dpi 300

# Intersection rendering (reference in grey, DUT intersection highlighted)
cielab-tools plot rings display.txt --reference srgb --mode intersection --output rings.pdf

# Multiple references, publication style
cielab-tools plot rings display.txt --reference srgb,bt2020 \
  --style publication \
  --colourmap viridis \
  --labels "Test Display,sRGB,BT.2020" \
  --output figure.eps
```

#### `surface` (3D gamut surface in CIELab)

```bash
# Interactive preview
cielab-tools plot surface display.txt --show

# Fixed viewpoint for publication
cielab-tools plot surface display.txt \
  --output surface.png \
  --elevation 30 \
  --azimuth 45 \
  --dpi 300

# With reference overlay
cielab-tools plot surface display.txt --reference srgb \
  --opacity 0.7 \
  --output comparison.png

# Multiple displays
cielab-tools plot surface display1.txt display2.txt display3.txt \
  --labels "Display A,Display B,Display C" \
  --output multi_surface.png
```

#### `comparison` (Side-by-side or overlay)

```bash
# Side-by-side rings
cielab-tools plot comparison display1.txt display2.txt \
  --type rings \
  --layout grid \
  --output comparison.png

# Overlay multiple surfaces
cielab-tools plot comparison display1.txt display2.txt display3.txt \
  --type surface \
  --overlay \
  --opacity 0.5 \
  --output overlay.png
```

### Common Options

- `--output <file>`: Output file (png, pdf, eps, svg, tiff)
- `--dpi <n>`: Resolution for raster formats (default: 150; publication: 300–600)
- `--show`: Open interactive preview window
- `--reference <gamut>`: Overlay reference gamut(s)
- `--mode <mode>`: Ring diagram mode: `outline` (default), `intersection`,
  `intersection-borders`
- `--style <style>`: Style preset: `default`, `publication`, `presentation`
- `--colour/--color`: Colour scheme (both spellings accepted)
- `--colourmap/--colormap <cmap>`: Colour map
- `--labels <labels>`: Comma-separated legend labels
- `--title <title>`: Plot title
- `--no-legend`: Hide legend
- `--figsize <w,h>`: Figure size in inches (e.g. `8,6`)

### 3D Plot Specific Options

- `--elevation <deg>`: Camera elevation angle (default: 30)
- `--azimuth <deg>`: Camera azimuth angle (default: 45)
- `--opacity <val>`: Surface opacity 0–1 (default: 0.8)
- `--wireframe`: Render as wireframe

### Style Presets

**`publication`**: High-DPI, clean styling, vector formats preferred
- White background, clear typography, thick lines, standard scientific colormaps
- Axis labels at standard font sizes

**`presentation`**: Bold colours, legible from distance
- High contrast, larger fonts, vibrant colours

**`default`**: Matplotlib defaults

---

## 3. GENERATE - Create Reference Data

**Top-level command:** `cielab-tools generate <type> [options]`

### Subcommands

#### `test-pattern`
Generate the RGB input signal values for display measurement, as specified in IDMS §5.32
(Code 1: `make_rgb_signals.m`). Output is a list of RGB values to programme into the
measurement instrument or test pattern generator.

```bash
# Standard 602-point reference set (11×11 grid per face, m=11)
cielab-tools generate test-pattern --output test_pattern.txt

# Smaller sets (with caution — results must be reported as estimates)
cielab-tools generate test-pattern --grid 9   # 386 points (9×9, m=9)
cielab-tools generate test-pattern --grid 7   # 218 points (7×7, m=7)
cielab-tools generate test-pattern --grid 5   # 98 points  (5×5, m=5)

# Specify bit depth (default: 8-bit, 0–255)
cielab-tools generate test-pattern --grid 11 --bits 10 --output pattern_10bit.txt

# CSV output (for import into measurement software)
cielab-tools generate test-pattern --format csv --output pattern.csv
```

**Note:** The 602-point set (m=11) is the normative reference. Smaller sets introduce
additional uncertainty. If a smaller set is measured, XYZ interpolation to 602 points must
be performed before analysis — see `generate interpolate`.

#### `reference`
Generate a reference gamut as a CGATS gamut envelope file (Lab values), or the corresponding
synthetic XYZ measurements. Uses `SyntheticGamut` to compute perfectly ideal primaries.

```bash
# Generate sRGB gamut envelope (Lab CGATS — the standard output format)
cielab-tools generate reference srgb --output srgb_envelope.txt

# Generate multiple references
cielab-tools generate reference srgb,bt2020,dci-p3,display-p3,adobe-rgb \
  --output-dir ./references/

# Custom reference from primaries
cielab-tools generate reference custom \
  --primaries 0.68,0.32,0.265,0.69,0.15,0.06 \
  --white 0.3127,0.329 \
  --gamma 2.2 \
  --output custom_envelope.txt

# Generate synthetic XYZ measurements (input-side CGATS, before Lab conversion)
cielab-tools generate reference srgb --format xyz --output srgb_xyz.txt

# Pre-calculated cylindrical map (for faster repeated calculations)
cielab-tools generate reference srgb --format cylmap --output srgb_cylmap.pkl
```

**Output format:** Default is a CGATS 17 gamut envelope file containing CIELab D50
coordinates — the device-independent format defined by IDMS §5.32 (Code 5). This file
can be used directly as a `--reference` argument in `calculate` and `plot` commands.

### Options

- `--output <file>`: Output file
- `--output-dir <dir>`: Directory for multiple files
- `--format <format>`: Output format: `cgats` (default), `xyz`, `csv`, `cylmap`
- `--grid <m>`: Grid divisions per edge for test pattern (default: 11 → 602 points)
- `--bits <n>`: Signal bit depth for test pattern (default: 8)
- `--primaries <x1,y1,x2,y2,x3,y3>`: RGB primary chromaticities (xy)
- `--white <x,y>`: White point chromaticity
- `--gamma <value>`: Gamma value

---

## 4. REPORT - Future Feature

> **Status: Not yet implemented. Planned for a future release.**

The goal is to provide standardised, document-quality analysis reports combining computed
metrics and publication-quality figures, driven by a YAML configuration file. Output formats
under consideration include PDF, HTML, and Markdown.

The exact schema, template design, and output formats are TBD and will be informed by
requirements from standards committee members and early users. The `report` command group is
reserved in the CLI structure to avoid future breaking changes.

Anticipated capabilities:
- YAML-configured reports (metrics + plots in one pass)
- Batch processing across a directory of CGATS files
- Built-in templates (quick, standard, publication, comparison)
- Standards-compliant metadata embedded in output

---

## 5. UI - Web Interface

> **Status: Not yet implemented. Planned for a future release.**

```bash
cielab-tools ui          # launches browser-based interface on localhost
```

See `ARCHITECTURE.md` for the proposed design (FastAPI + Vue 3 + Plotly.js for interactive
display, matplotlib for publication export).

---

## Global Commands and Options

### `about` Command

Display information about the tool, standards compliance, and citation.

```bash
cielab-tools about

> cielab-gamut-tools 1.0.0
>
> Python implementation of CIELab gamut volume calculation.
> Port of the MATLAB reference implementation on which the following
> IEC TC110 and ICDM standards are based.
>
> Standards Compliance:
>   • ICDM Information Display Measurements Standard (IDMS) v1.3, §5.32
>     Color Gamut Envelope — Color Capability
>   • IEC 62977-3-5 — Electronic displays:
>     Evaluation of optical performance — Colour capabilities
>   • IEC 62906-6-1 — Displays:
>     Colour gamut intersection visualisation method
>   [Final publication numbers subject to IEC TC110 ballot]
>
> Citation:
>   Smith, E., et al. (2020). "Gamut volume calculation for display
>   colour characterisation." Journal of the Society for Information Display.
>
> Algorithm:
>   Cylindrical integration in CIELab space via Möller-Trumbore
>   ray-triangle intersection. Bradford chromatic adaptation to D50.
>   Reference implementation: cielab-gamut-tools-m (MATLAB/Octave).
>
> Repository: https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py
> Documentation: https://cielab-gamut-tools.readthedocs.io
> License: MIT
```

### Global Options (All Commands)

- `--verbose, -v`: Verbose output during execution
- `--quiet, -q`: Minimal output — values only, for scripting
- `--version`: Show version number only
- `--help, -h`: Show help

---

## Configuration File

**`~/.config/cielab-gamut/config.yaml`** (optional)

```yaml
# Default reference gamuts
default_references: [srgb, bt2020]

# Default standard
default_standard: IDMS

# Plot defaults
plot:
  default_style: publication
  default_dpi: 300
  default_colourmap: viridis

# Calculation defaults
calculate:
  precision: 1
  output_format: text
```

---

## Implementation Notes

### CLI Framework: Typer
- Type-safe with auto-generated help text
- Subcommand groups map cleanly to this structure
- Excellent error messages; plays well with `rich` for formatted output

### Language and Spelling

**IMPORTANT: Standards Compliance**
- IEC and ISO standards use **British English** throughout
- All output (especially with `--standard` flag) must use British spelling:
  - "colour" not "color"
  - "analyse" not "analyze"
  - "characterisation" not "characterization"
- **Input parameters**: Accept BOTH spellings for user convenience via Typer aliases:
  - `--color`/`--colour`
  - `--colormap`/`--colourmap`

### Standards Traceability

The list of compliant standards is maintained in `STANDARDS.md` in the repository root.
Both the `about` command and `--standard` metadata read from the same source. Version numbers
and scope statements are to be confirmed with the relevant standards committees (IEC TC110,
ICDM) once final publication occurs.

### Named Reference Gamuts

| ID | Full name | White point |
|---|---|---|
| `srgb` | IEC sRGB / BT.709 | D65 |
| `bt2020` | ITU-R BT.2020 | D65 |
| `dci-p3` | DCI-P3 | DCI white (0.314, 0.351) |
| `display-p3` | Display P3 | D65 |
| `adobe-rgb` | Adobe RGB (1998) | D65 |

### Dependencies

- **Core**: numpy, scipy, matplotlib, numba (already present)
- **CLI**: typer, rich
- **Config**: pyyaml
- **UI** *(optional extra)*: fastapi, uvicorn — `pip install cielab-gamut-tools[ui]`
- **Reports** *(future)*: TBD — candidates include reportlab, weasyprint

### File Format Support

**Input:**
- CGATS.17 format 2 (current) — XYZ measurements or Lab gamut envelope
- IDMS v1.3 variant (current)
- Raw XYZ/RGB (planned)

**Output:**
- CGATS.17 format 2 (planned — needed for `generate reference` and interop)
- Text (human-readable)
- JSON (machine-readable, standards-compliant metadata)
- CSV (spreadsheet / Excel compatible)

---

## Example Workflows

### Quick Analysis
```bash
# Volume only
cielab-tools calculate volume display.txt

# Volume, scripting-friendly
volume=$(cielab-tools calculate volume display.txt --quiet)
echo "Volume: $volume"
```

### Coverage Table for Excel
```bash
# Single display against all standard references, CSV to file
cielab-tools calculate coverage display.txt \
  --reference srgb,bt2020,dci-p3,adobe-rgb \
  --format csv \
  --output coverage.csv
```

### Batch Volume Survey
```bash
# All CGATS files in a directory → CSV summary
for f in displays/*.txt; do
  cielab-tools calculate volume "$f" --format csv --quiet
done > all_volumes.csv
```

### Publication Figure
```bash
# High-quality gamut ring diagram
cielab-tools plot rings display.txt \
  --reference srgb,bt2020 \
  --style publication \
  --mode intersection \
  --output figure1.eps \
  --dpi 600 \
  --labels "Test Display,sRGB,BT.2020"
```

### Generate Measurement Pattern
```bash
# Generate the 602 RGB values to measure on the display
cielab-tools generate test-pattern --format csv --output patch_list.csv

# After measurement, calculate the gamut envelope
cielab-tools generate reference srgb --output srgb_ref.txt  # reference to compare against
cielab-tools calculate coverage measured_display.txt --reference srgb_ref.txt
```

---

## Next Steps

1. **Confirm standards references**
   - Obtain final publication numbers from IEC TC110 once ballots close
   - Create `STANDARDS.md` with scope statements and input data requirements per standard

2. **Implement library gaps first** (see `TODO.md`)
   - CGATS writer
   - `make_rgb_signals` equivalent
   - `compute_rings()` public method
   - Adobe RGB in `SyntheticGamut`

3. **Implement CLI**
   - Set up Typer with command groups
   - `about` command first (no library deps)
   - `calculate volume`, `calculate coverage`, `calculate compare`
   - `plot rings`, `plot surface`
   - `generate test-pattern`, `generate reference`

4. **Testing**
   - Unit tests for each CLI command
   - Integration tests with sample CGATS files
   - Verify `--standard` metadata is correct and complete

5. **Documentation**
   - Update README with CLI examples
   - Document British English conventions

---

## Questions for Review

1. **Standards numbers**: Please confirm final IEC TC110 publication numbers and dates for
   IEC 62977-3-5 and IEC 62906-6-1 once available, for use in `about` output and metadata.

2. **Report formats** *(future planning)*: When the `report` command is designed, are PDF
   and HTML sufficient, or is Word/Excel output needed for committee workflows?

3. **Batch workflow**: Any specific needs beyond glob patterns — e.g. watching a folder,
   integration with measurement instrument software?

4. **Pre-computed reference data**: Would bundling pre-calculated cylindrical maps for the
   five named reference gamuts meaningfully speed up common user workflows?
