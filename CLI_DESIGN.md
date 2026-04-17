# CLI Design Plan for cielab-gamut-tools

## Overview

Command-line interface for gamut analysis, visualization, and reporting. Designed for display professionals who need quick, scriptable, standards-compliant analysis.

## Command Groups

```
cielab-gamut
├── calculate     # Analysis and metrics
├── plot          # Visualization (2D/3D)
├── generate      # Create reference gamuts and data
├── report        # Automated report generation
└── about         # Standards compliance and citation information
```

---

## 1. CALCULATE - Analysis and Metrics

**Top-level command:** `cielab-gamut calculate <metric> <file> [options]`

### Subcommands

#### `volume`
Calculate gamut volume.

```bash
# Basic volume
cielab-gamut calculate volume display.txt
> Volume: 956234 (CIELab ΔE*ab units³)

# Multiple files
cielab-gamut calculate volume display1.txt display2.txt display3.txt
> display1.txt: 956234
> display2.txt: 892103
> display3.txt: 1024567

# With metadata output
cielab-gamut calculate volume display.txt --json
> {"file": "display.txt", "volume": 956234, "unit": "deltaE_ab_cubed"}

# Standards-compliant output
cielab-gamut calculate volume display.txt --standard IEC --json
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
cielab-gamut calculate coverage display.txt --reference srgb
> sRGB coverage: 98.3%
> Display volume: 956234
> sRGB volume: 830331
> Intersection volume: 816236

# Multiple references
cielab-gamut calculate coverage display.txt --reference srgb,bt2020,dci-p3
> sRGB coverage: 98.3%
> BT.2020 coverage: 67.2%
> DCI-P3 coverage: 95.1%

# Custom reference from file
cielab-gamut calculate coverage display.txt --reference custom.txt

# Detailed output
cielab-gamut calculate coverage display.txt --reference srgb --json --standard ICDM
```

#### `compare`
Compare multiple displays.

```bash
# Compare volumes
cielab-gamut calculate compare display1.txt display2.txt display3.txt
> Gamut Comparison:
> display1.txt: 956234
> display2.txt: 892103 (-6.7% vs display1)
> display3.txt: 1024567 (+7.2% vs display1)

# Compare coverage
cielab-gamut calculate compare display1.txt display2.txt --reference srgb
> sRGB Coverage Comparison:
> display1.txt: 98.3% (intersection: 816236)
> display2.txt: 94.1% (intersection: 781420)

# Matrix comparison (all pairwise)
cielab-gamut calculate compare display1.txt display2.txt display3.txt --matrix
> Pairwise Intersections:
>              display1  display2  display3
> display1         100%      89%      92%
> display2          87%     100%      85%
> display3          91%      88%     100%
```

#### `metrics`
Calculate comprehensive metrics for standards compliance.

```bash
# All standard metrics
cielab-gamut calculate metrics display.txt --standard IEC
> Volume: 956234
> Convex hull volume: 1023456 (convexity: 93.4%)
> Surface area: 12345
> sRGB coverage: 98.3%
> BT.2020 coverage: 67.2%
> ...

# Specific metrics
cielab-gamut calculate metrics display.txt --metrics volume,surface_area,coverage
```

### Common Options

- `--output <file>`: Write results to file (CSV, JSON, or TXT)
- `--format <format>`: Output format (text, json, csv)
- `--standard <standard>`: Compliance standard (IEC, ICDM)
- `--reference <gamut>`: Reference gamut(s) (srgb, bt2020, dci-p3, display-p3, or file path)
- `--precision <n>`: Decimal places for output (default: 1)
- `--quiet`: Only output values (for scripting)

### Standards Compliance

**All calculations are standards-compliant by design.** This implementation is based on the MATLAB reference code used in IEC and ICDM standards.

When `--standard` flag is used with output:
- Adds standard version numbers to metadata
- Includes traceability information (standard name, method, calculation timestamp)
- JSON output includes full compliance documentation
- Warnings if input data doesn't meet standard requirements (e.g., measurement density, white point)

**Supported standards** (to be documented from standards committee work):
- `IEC`: IEC 61966 series
- `ICDM`: ICDM display metrology specifications

For complete standards compliance information, use: `cielab-gamut about`

---

## 2. PLOT - Visualization

**Top-level command:** `cielab-gamut plot <type> <file> [options]`

### Subcommands

#### `rings` (2D gamut boundaries at L* slices)

```bash
# Preview (opens window)
cielab-gamut plot rings display.txt --show

# Save to file
cielab-gamut plot rings display.txt --output figure.png

# With reference overlay
cielab-gamut plot rings display.txt --reference srgb --output figure.eps --dpi 300

# Multiple L* slices
cielab-gamut plot rings display.txt --slices 20,50,80 --reference srgb,bt2020 --output rings.pdf

# Custom styling for publication
cielab-gamut plot rings display.txt --reference srgb \
  --style publication \
  --colormap viridis \
  --labels "Test Display,sRGB" \
  --output figure.eps
```

#### `surface` (3D gamut surface)

```bash
# Interactive preview
cielab-gamut plot surface display.txt --show

# Fixed viewpoint for publication
cielab-gamut plot surface display.txt \
  --output surface.png \
  --elevation 30 \
  --azimuth 45 \
  --dpi 300

# With reference overlay
cielab-gamut plot surface display.txt --reference srgb \
  --opacity 0.7 \
  --output comparison.png

# Multiple displays
cielab-gamut plot surface display1.txt display2.txt display3.txt \
  --labels "Display A,Display B,Display C" \
  --output multi_surface.png
```

#### `comparison` (Side-by-side or overlay comparison)

```bash
# Side-by-side rings at multiple L* slices
cielab-gamut plot comparison display1.txt display2.txt \
  --type rings \
  --slices 20,50,80 \
  --layout grid \
  --output comparison.png

# Overlay multiple gamuts
cielab-gamut plot comparison display1.txt display2.txt display3.txt \
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
- `--colormap <cmap>`: Color scheme
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
- Black/white backgrounds
- Clear, thick lines
- Standard scientific colormaps
- Axis labels in standard font sizes

**`presentation`**: Bold colors, clear from distance
- High contrast
- Larger fonts
- Vibrant colors

**`default`**: Matplotlib defaults

---

## 3. GENERATE - Create Reference Data

**Top-level command:** `cielab-gamut generate <type> [options]`

### Subcommands

#### `reference`
Generate standard reference gamuts.

```bash
# Generate sRGB gamut data
cielab-gamut generate reference srgb --output srgb.txt --format cgats

# Generate multiple references
cielab-gamut generate reference srgb,bt2020,dci-p3 --output-dir ./references/

# Custom reference
cielab-gamut generate reference custom \
  --primaries 0.68,0.32,0.265,0.69,0.15,0.06 \
  --white 0.3127,0.329 \
  --gamma 2.2 \
  --output custom_gamut.txt

# Pre-calculated cylindrical map (for faster repeated calculations)
cielab-gamut generate reference srgb --output srgb_cylmap.pkl --format cylmap
```

#### `test-pattern`
Generate test measurement patterns for display characterization.

```bash
# Standard RGB cube sampling
cielab-gamut generate test-pattern --points 729 --output test_pattern.txt

# For specific measurement workflow
cielab-gamut generate test-pattern --standard ICDM --output pattern.txt
```

### Options

- `--output <file>`: Output file
- `--output-dir <dir>`: Directory for multiple files
- `--format <format>`: Output format (cgats, xyz, rgb, json, pkl)
- `--primaries <x1,y1,x2,y2,x3,y3>`: RGB primary chromaticities
- `--white <x,y>`: White point chromaticity
- `--gamma <value>`: Gamma value
- `--points <n>`: Number of points for test pattern

---

## 4. REPORT - Automated Report Generation

**Top-level command:** `cielab-gamut report <config> [files...]`

### Report Configuration (YAML)

**Example: `standard_report.yaml`**

```yaml
# Standard Display Gamut Report
report:
  title: "Display Gamut Analysis Report"
  standard: "IEC"  # IEC or ICDM compliance

  # Calculations to perform
  calculations:
    - metric: volume
      format: "Volume: {value:.0f} ΔE*ab³"

    - metric: coverage
      references: [srgb, bt2020, dci-p3]
      format: "{ref} coverage: {value:.1f}%"

    - metric: metrics
      items: [volume, surface_area, convexity]

  # Plots to include
  plots:
    - type: rings
      slices: [20, 50, 80]
      references: [srgb, bt2020]
      style: publication
      dpi: 300
      caption: "Gamut boundaries at L*=20, 50, and 80"

    - type: surface
      references: [srgb]
      elevation: 30
      azimuth: 45
      dpi: 300
      caption: "3D gamut surface with sRGB reference"

  # Output settings
  output:
    format: pdf  # pdf, html, markdown
    filename: "{basename}_report.{ext}"  # template
    include_metadata: true
    include_timestamp: true
```

### Usage

```bash
# Single file
cielab-gamut report standard_report.yaml display.txt

# Multiple files (batch processing)
cielab-gamut report standard_report.yaml display1.txt display2.txt display3.txt

# File pattern (glob)
cielab-gamut report standard_report.yaml "measurements/*.txt"

# Output to directory
cielab-gamut report standard_report.yaml "*.txt" --output-dir ./reports/

# Override config options
cielab-gamut report standard_report.yaml display.txt \
  --format html \
  --title "Custom Display Report"
```

### Batch Processing

```bash
# Process all CGATS files in directory
cielab-gamut report standard_report.yaml "measurements/*.txt" --output-dir reports/

# With parallel processing
cielab-gamut report standard_report.yaml "*.txt" --jobs 4

# Generate summary across all files
cielab-gamut report standard_report.yaml "*.txt" --summary summary.pdf
```

### Report Output Formats

**PDF**: Professional reports with embedded figures
- LaTeX-quality typesetting
- Vector graphics embedded
- Multi-page support

**HTML**: Interactive reports
- Embedded plots
- Responsive layout
- Can include interactive plots (plotly)

**Markdown**: Simple text reports
- Easy to convert to other formats
- Version control friendly
- Can be rendered by GitHub, etc.

### Report Templates

Provide standard templates:
- `quick`: Volume and sRGB coverage only
- `standard`: Comprehensive analysis with key plots
- `publication`: High-quality figures and detailed metrics
- `comparison`: Compare multiple displays side-by-side

```bash
# Use built-in template
cielab-gamut report --template standard display.txt

# List available templates
cielab-gamut report --list-templates
```

---

## Global Commands and Options

### `about` Command

Display detailed information about the tool, standards compliance, and citation.

```bash
cielab-gamut about

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
  default_colormap: viridis

# Calculation defaults
calculate:
  precision: 1
  output_format: text

# Report defaults
report:
  output_format: pdf
```

---

## Implementation Notes

### CLI Framework: Typer
- Type-safe with auto-generated help
- Subcommand groups map cleanly to our structure
- Excellent error messages

### Language and Spelling

**IMPORTANT: Standards Compliance**
- IEC and ISO standards use **British English** throughout
- All output (especially with `--standard` flag) must use British spelling:
  - "colour" not "color"
  - "analyse" not "analyze"
  - "metres" not "meters"
- **Input parameters**: Accept BOTH spellings for user convenience
  - `--color`/`--colour`
  - `--colormap`/`--colourmap`
- Implementation: Use aliases for CLI arguments, internal/output uses British English

### Standards List Maintenance

The list of compliant standards will be maintained in a central location:
- **Primary source**: `STANDARDS.md` or `COMPLIANCE.md` in repository root
- **Metadata**: Also in `pyproject.toml` for packaging
- **Runtime access**: Both `about` command and `--standard` metadata read from same source
- **Updates**: Standards list to be provided by standards committee members

### Dependencies
- **Core**: numpy, scipy, matplotlib, numba (already have)
- **CLI**: typer, rich (for pretty terminal output)
- **Reports**: reportlab (PDF) or weasyprint (HTML→PDF)
- **Config**: pyyaml

### File Format Support

**Input:**
- CGATS.17 (current)
- IDMS v1.3 (current)
- Raw XYZ/RGB (to add)
- JSON (to add)

**Output:**
- Text (human-readable)
- JSON (machine-readable, standards-compliant)
- CSV (spreadsheet-friendly)
- CGATS (for interchange)

---

## Examples Workflow

### Quick Analysis
```bash
# Just need volume
cielab-gamut calculate volume display.txt
```

### Publication Figure
```bash
# High-quality gamut rings
cielab-gamut plot rings display.txt \
  --reference srgb,bt2020 \
  --style publication \
  --output figure1.eps \
  --dpi 600 \
  --labels "Test Display,sRGB,BT.2020"
```

### Standards Compliance Report
```bash
# IEC-compliant report
cielab-gamut report --template standard display.txt --standard IEC
```

### Batch Processing
```bash
# Analyze all displays in a directory
cielab-gamut report standard_report.yaml "displays/*.txt" --output-dir reports/
```

### Scripting
```bash
# Get just the volume value for scripting
volume=$(cielab-gamut calculate volume display.txt --quiet)
echo "Measured volume: $volume"
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
   - Implement `calculate` commands first (leverage existing code)
   - Add `plot` commands (wrap existing plotting)
   - Implement `generate` for references
   - Build `report` system with YAML config

3. **Testing**
   - Unit tests for each CLI command
   - Integration tests with sample files
   - Verify metadata output includes correct standard information

4. **Documentation**
   - Update README with CLI examples
   - Create user guide
   - Add example reports and configs
   - Document British English conventions

---

## Questions for Review

1. **Standards list**: Please provide the official list of compliant standards with:
   - Full standard names and version numbers (e.g., "IEC 61966-2-1:2024")
   - Brief description of what each standard covers
   - Any specific input data requirements

2. **Report formats**: PDF sufficient, or need Word/Excel output?

3. **Batch processing**: Any specific workflow needs (e.g., watching a directory, integration with measurement software)?

4. **Additional metrics**: Beyond volume and coverage, what other calculations are important?
   - Surface area?
   - Convexity ratio?
   - Per-region analysis (shadows, midtones, highlights)?
   - Gamut volume under specific illuminants?
   - Any metrics specific to emissive vs. reflective displays?

5. **Pre-calculated data**: Would cached cylindrical maps for standard references speed up common operations significantly?

6. **Interactive features**: Any need for interactive HTML reports with embedded plotly plots?