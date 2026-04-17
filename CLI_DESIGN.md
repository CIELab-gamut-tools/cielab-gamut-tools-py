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
├── generate      # Create reference gamuts and data
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
> Volume: 956234 (CIELab ΔE*ab units³)

# Multiple files
cielab-tools calculate volume display1.txt display2.txt display3.txt
> display1.txt: 956234
> display2.txt: 892103
> display3.txt: 1024567

# With metadata output
cielab-tools calculate volume display.txt --json
> {"file": "display.txt", "volume": 956234, "unit": "deltaE_ab_cubed"}

# Standards-compliant output
cielab-tools calculate volume display.txt --standard IEC --json
> {
>   "file": "display.txt",
>   "volume": 956234,
>   "unit": "deltaE_ab_cubed",
>   "standard": "IEC 61966-2-1:2024",
>   "method": "cylindrical_integration",
>   "calculated": "2026-04-16T10:23:45Z"
> }
```

#### `coverage`
Calculate coverage of reference gamut(s).

```bash
# sRGB coverage
cielab-tools calculate coverage display.txt --reference srgb
> sRGB coverage: 98.3%
> Display volume: 956234
> sRGB volume:    830331
> Intersection:   816236

# Multiple references
cielab-tools calculate coverage display.txt --reference srgb,bt2020,dci-p3
> sRGB coverage:   98.3%
> BT.2020 coverage: 67.2%
> DCI-P3 coverage:  95.1%

# Custom reference from file
cielab-tools calculate coverage display.txt --reference custom.txt

# Detailed output
cielab-tools calculate coverage display.txt --reference srgb --json --standard ICDM
```

#### `compare`
Compare multiple displays.

```bash
# Compare volumes
cielab-tools calculate compare display1.txt display2.txt display3.txt
> Gamut Comparison:
> display1.txt: 956234
> display2.txt: 892103 (-6.7% vs display1)
> display3.txt: 1024567 (+7.2% vs display1)

# Compare coverage against a reference
cielab-tools calculate compare display1.txt display2.txt --reference srgb
> sRGB Coverage Comparison:
> display1.txt: 98.3% (intersection: 816236)
> display2.txt: 94.1% (intersection: 781420)

# Matrix comparison (all pairwise intersections)
cielab-tools calculate compare display1.txt display2.txt display3.txt --matrix
> Pairwise Intersections:
>              display1  display2  display3
> display1         100%      89%      92%
> display2          87%     100%      85%
> display3          91%      88%     100%
```

### Common Options

- `--output <file>`: Write results to file (CSV, JSON, or TXT)
- `--format <format>`: Output format (text, json, csv)
- `--standard <standard>`: Compliance standard (IEC, ICDM)
- `--reference <gamut>`: Reference gamut(s) (srgb, bt2020, dci-p3, display-p3, or file path)
- `--precision <n>`: Decimal places for output (default: 1)
- `--quiet`: Only output values (for scripting)

### Standards Compliance

**All calculations are standards-compliant by design.** This implementation is based on the
MATLAB reference code used in IEC and ICDM standards.

When `--standard` flag is used with output:
- Adds standard version numbers to metadata
- Includes traceability information (standard name, method, calculation timestamp)
- JSON output includes full compliance documentation
- Warnings if input data doesn't meet standard requirements (e.g., measurement density, white point)

**Supported standards** (to be documented from standards committee work):
- `IEC`: IEC 61966 series
- `ICDM`: ICDM display metrology specifications

For complete standards compliance information, use: `cielab-tools about`

---

## 2. PLOT - Visualisation

**Top-level command:** `cielab-tools plot <type> <file> [options]`

### Subcommands

#### `rings` (2D gamut boundaries at L* slices)

```bash
# Preview (opens window)
cielab-tools plot rings display.txt --show

# Save to file
cielab-tools plot rings display.txt --output figure.png

# With reference overlay
cielab-tools plot rings display.txt --reference srgb --output figure.eps --dpi 300

# Multiple L* slices
cielab-tools plot rings display.txt --slices 20,50,80 --reference srgb,bt2020 --output rings.pdf

# Custom styling for publication
cielab-tools plot rings display.txt --reference srgb \
  --style publication \
  --colourmap viridis \
  --labels "Test Display,sRGB" \
  --output figure.eps
```

#### `surface` (3D gamut surface)

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

#### `comparison` (Side-by-side or overlay comparison)

```bash
# Side-by-side rings at multiple L* slices
cielab-tools plot comparison display1.txt display2.txt \
  --type rings \
  --slices 20,50,80 \
  --layout grid \
  --output comparison.png

# Overlay multiple gamuts
cielab-tools plot comparison display1.txt display2.txt display3.txt \
  --type surface \
  --overlay \
  --opacity 0.5 \
  --output overlay.png
```

### Common Options

- `--output <file>`: Output file (png, pdf, eps, svg, tiff)
- `--dpi <n>`: Resolution for raster formats (default: 150, publication: 300-600)
- `--show`: Open interactive preview window
- `--reference <gamut>`: Overlay reference gamut(s)
- `--style <style>`: Style preset (default, publication, presentation)
- `--colour/--color <cmap>`: Colour scheme (both spellings accepted)
- `--colourmap/--colormap <cmap>`: Colour map (both spellings accepted)
- `--labels <labels>`: Comma-separated labels for legend
- `--title <title>`: Plot title
- `--no-legend`: Hide legend
- `--figsize <w,h>`: Figure size in inches (e.g., 8,6)

### 3D Plot Specific Options

- `--elevation <deg>`: Camera elevation angle (default: 30)
- `--azimuth <deg>`: Camera azimuth angle (default: 45)
- `--opacity <val>`: Surface opacity 0-1 (default: 0.8)
- `--wireframe`: Render as wireframe instead of solid surface

### Style Presets

**`publication`**: High-DPI, clean styling, vector formats preferred
- White background, clear typography
- Thick lines, standard scientific colormaps
- Axis labels in standard font sizes

**`presentation`**: Bold colours, legible from distance
- High contrast, larger fonts, vibrant colours

**`default`**: Matplotlib defaults

---

## 3. GENERATE - Create Reference Data

**Top-level command:** `cielab-tools generate <type> [options]`

### Subcommands

#### `reference`
Generate standard reference gamuts as CGATS files or pre-computed cylindrical maps.

```bash
# Generate sRGB gamut data as CGATS
cielab-tools generate reference srgb --output srgb.txt --format cgats

# Generate multiple references
cielab-tools generate reference srgb,bt2020,dci-p3 --output-dir ./references/

# Custom reference
cielab-tools generate reference custom \
  --primaries 0.68,0.32,0.265,0.69,0.15,0.06 \
  --white 0.3127,0.329 \
  --gamma 2.2 \
  --output custom_gamut.txt

# Pre-calculated cylindrical map (for faster repeated calculations)
cielab-tools generate reference srgb --output srgb_cylmap.pkl --format cylmap
```

#### `test-pattern`
Generate test measurement patterns for display characterisation.

```bash
# Standard RGB cube sampling
cielab-tools generate test-pattern --points 729 --output test_pattern.txt

# For specific measurement workflow
cielab-tools generate test-pattern --standard ICDM --output pattern.txt
```

### Options

- `--output <file>`: Output file
- `--output-dir <dir>`: Directory for multiple files
- `--format <format>`: Output format (cgats, json, cylmap)
- `--primaries <x1,y1,x2,y2,x3,y3>`: RGB primary chromaticities
- `--white <x,y>`: White point chromaticity
- `--gamma <value>`: Gamma value
- `--points <n>`: Number of points for test pattern

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
- Standards-compliant metadata in output

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

Display detailed information about the tool, standards compliance, and citation.

```bash
cielab-tools about

> cielab-gamut-tools 1.0.0
>
> Python implementation of CIELab gamut volume calculation.
> Port of the MATLAB reference implementation used in IEC and ICDM standards.
>
> Standards Compliance:
>   • IEC 61966-2-1:2024 - sRGB colour space
>   • IEC 61966-9:2024 - Gamut volume calculation methodology
>   • ICDM v1.3 - Display measurement and characterisation
>   [Additional standards to be documented]
>
> Citation:
>   Smith, E., et al. (2020). "Gamut volume calculation for display
>   colour characterisation." Journal of the Society for Information Display.
>
> Algorithm Reference:
>   Based on MATLAB reference implementation (cielab-gamut-tools-m)
>   Method: Cylindrical integration in CIELab space
>
> Repository: https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py
> Documentation: https://cielab-gamut-tools.readthedocs.io
> License: MIT
```

### Global Options (All Commands)

- `--verbose, -v`: Verbose output during execution
- `--quiet, -q`: Minimal output (values only, for scripting)
- `--version`: Show version number only
- `--help, -h`: Show help

---

## Configuration File

**`~/.config/cielab-gamut/config.yaml`** (optional)

```yaml
# Default reference gamuts
default_references: [srgb, bt2020]

# Default standard
default_standard: IEC

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
- Type-safe with auto-generated help
- Subcommand groups map cleanly to this structure
- Excellent error messages

### Language and Spelling

**IMPORTANT: Standards Compliance**
- IEC and ISO standards use **British English** throughout
- All output (especially with `--standard` flag) must use British spelling:
  - "colour" not "color"
  - "analyse" not "analyze"
  - "characterisation" not "characterization"
- **Input parameters**: Accept BOTH spellings for user convenience
  - `--color`/`--colour`
  - `--colormap`/`--colourmap`
- Implementation: Use Typer aliases for CLI arguments; internal strings and output use
  British English

### Standards List Maintenance

The list of compliant standards will be maintained in a central location:
- **Primary source**: `STANDARDS.md` in repository root
- **Metadata**: Also in `pyproject.toml` for packaging
- **Runtime access**: `about` command and `--standard` metadata read from the same source
- **Updates**: Standards list to be provided by standards committee members

### Dependencies

- **Core**: numpy, scipy, matplotlib, numba (already present)
- **CLI**: typer, rich (pretty terminal output)
- **Config**: pyyaml
- **UI** *(optional extra)*: fastapi, uvicorn — `pip install cielab-gamut-tools[ui]`
- **Reports** *(future)*: TBD — candidates include reportlab, weasyprint

### File Format Support

**Input:**
- CGATS.17 (current)
- IDMS v1.3 (current)
- Raw XYZ/RGB (planned)
- JSON (planned)

**Output:**
- Text (human-readable)
- JSON (machine-readable, standards-compliant)
- CSV (spreadsheet-friendly)

---

## Example Workflows

### Quick Analysis
```bash
# Just need volume
cielab-tools calculate volume display.txt
```

### Scripting
```bash
# Get just the volume value
volume=$(cielab-tools calculate volume display.txt --quiet)
echo "Measured volume: $volume"
```

### Publication Figure
```bash
# High-quality gamut rings
cielab-tools plot rings display.txt \
  --reference srgb,bt2020 \
  --style publication \
  --output figure1.eps \
  --dpi 600 \
  --labels "Test Display,sRGB,BT.2020"
```

### Batch Coverage Table
```bash
# JSON output piped to jq for further processing
for f in displays/*.txt; do
  cielab-tools calculate coverage "$f" --reference srgb,bt2020,dci-p3 --json
done
```

---

## Next Steps

1. **Document standards compliance**
   - Obtain official list of compliant standards from standards committee
   - Create `STANDARDS.md` with full compliance documentation
   - Document any input data requirements per standard

2. **Implement CLI structure**
   - Set up Typer with command groups
   - Implement `about` command
   - Implement `calculate volume`, `calculate coverage`, `calculate compare`
   - Add `plot rings` and `plot surface` (wrap existing plotting code)
   - Add `generate reference`

3. **Testing**
   - Unit tests for each CLI command
   - Integration tests with sample CGATS files
   - Verify `--standard` metadata output is correct

4. **Documentation**
   - Update README with CLI examples
   - Create user guide
   - Document British English conventions

---

## Questions for Review

1. **Standards list**: Please provide the official list of compliant standards with:
   - Full standard names and version numbers (e.g., "IEC 61966-2-1:2024")
   - Brief description of what each standard covers
   - Any specific input data requirements per standard

2. **Report formats** *(for future planning)*: When the `report` command is designed, are
   PDF and HTML sufficient, or is Word/Excel output needed for committee workflows?

3. **Batch processing**: Any specific workflow needs beyond glob patterns (e.g., watching a
   directory for new files, integration with measurement instrument software)?

4. **Pre-calculated data**: Would shipping bundled cylindrical maps for the standard
   references (sRGB, BT.2020, DCI-P3) meaningfully speed up common operations for users
   who always compare against the same references?
