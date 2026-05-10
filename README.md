# cielab-gamut-tools

Calculate and visualize CIELab colour gamuts of displays.

Implements the gamut volume algorithm from the [gamut-volume-m](https://github.com/CIELab-gamut-tools/gamut-volume-m) MATLAB library. Results are normative under IDMS v1.3, IEC 62977-3-5, and IEC 62906-6-1.

## Installation

Requires Python 3.10 or later.

```bash
pip install cielab-gamut-tools
```

On Ubuntu 24.04+ / Debian 12+ you may need a virtual environment or pipx due to PEP 668:

```bash
# virtual environment
python3 -m venv gamut_env && source gamut_env/bin/activate
pip install cielab-gamut-tools

# or pipx (CLI only)
pipx install cielab-gamut-tools
```

<details>
<summary>Install from source</summary>

```bash
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e .
```
</details>

### Updating

```bash
pipx upgrade cielab-gamut-tools   # if installed with pipx
pip install --upgrade cielab-gamut-tools  # if installed with pip
```

If `--version` still shows the old version after upgrading, force-reinstall:

```bash
pipx install cielab-gamut-tools --force
pip install --force-reinstall cielab-gamut-tools
```

`cielab-tools about` will tell you if a newer version is available.

---

## Command-line usage

After installation, two equivalent commands are available:

```
cielab-gamut-tools   # canonical name used in standards citations
cielab-tools         # short alias for everyday use
```

### Standards and citation information

```bash
cielab-tools about
```

### Calculate gamut volume

```bash
# From a CGATS measurement file
cielab-tools calculate volume display.txt

# Named reference gamut
cielab-tools calculate volume srgb

# Multiple gamuts — tabulated output
cielab-tools calculate volume display1.txt display2.txt srgb bt.2020

# Machine-readable output
cielab-tools calculate volume display.txt --format json
cielab-tools calculate volume display.txt --format csv

# Standards-traceable output (appends algorithm metadata)
cielab-tools calculate volume display.txt --standard IDMS --format json

# Value only, for scripting
cielab-tools calculate volume srgb --quiet
```

Named gamuts: `srgb`, `bt.2020`, `dci-p3`, `display-p3`, `adobe-rgb`.

### Calculate gamut coverage

```bash
# Coverage against a single reference
cielab-tools calculate coverage display.txt --reference srgb

# Multiple references in one pass
cielab-tools calculate coverage display.txt --reference srgb,bt.2020,dci-p3

# CSV for spreadsheet import
cielab-tools calculate coverage display.txt --reference srgb,bt.2020 --format csv
```

### Compare multiple gamuts

```bash
# Volume comparison — delta vs first gamut
cielab-tools calculate compare display1.txt display2.txt display3.txt

# Coverage of each against a single reference
cielab-tools calculate compare display1.txt display2.txt --reference srgb

# Full pairwise intersection matrix (entry (i,j) = % of gamut j covered by gamut i)
cielab-tools calculate compare srgb bt.2020 dci-p3 display-p3 --matrix
cielab-tools calculate compare srgb bt.2020 dci-p3 --matrix --format csv
```

### Visualise gamut diagrams

```bash
# 2D ring diagram (a*-b* plane, L* encoded as ring radii)
cielab-tools plot rings display.txt
cielab-tools plot rings display.txt --reference srgb
cielab-tools plot rings display.txt --reference srgb --intersection

# Save to file
cielab-tools plot rings display.txt --reference srgb --output rings.png
cielab-tools plot rings display.txt --output rings.pdf --dpi 300

# 3D surface in CIELab space
cielab-tools plot surface display.txt

# Overlay multiple gamuts (use --alpha < 1 to see through surfaces)
cielab-tools plot surface srgb bt.2020 --alpha 0.4
cielab-tools plot surface display.txt srgb --alpha 0.5 --output comparison.png
```

### Generate reference files

```bash
# RGB test signal list for measurement (normative 602-point set, m=11)
cielab-tools generate rgb-signals                          # CGATS to stdout
cielab-tools generate rgb-signals --output signals.txt
cielab-tools generate rgb-signals --grid 9 --bits 10      # reduced grid, 10-bit

# Synthetic reference gamut as CGATS file
cielab-tools generate synthetic srgb --output srgb_envelope.txt
cielab-tools generate synthetic bt.2020 --mode measurement --output bt2020_meas.txt

# Custom primaries
cielab-tools generate synthetic \
    --primaries 0.64,0.33,0.21,0.71,0.15,0.06 \
    --white 0.3127,0.3290 --gamma 2.2 --output custom.txt
```

---

## Numerical precision

All three computation paths give the same volume result:

| Path | sRGB example |
|------|-------------|
| `calculate volume srgb` | 830,807 |
| CGATS measurement file | 830,807 |
| CGATS envelope file | 830,807 |

The MATLAB reference value for sRGB is 830,766 (~0.005% difference). The standards specify a tolerance of ±1%.

---

## Using as a Python library

The CLI covers most workflows. If you need to integrate gamut calculations into a Python script or pipeline:

```python
from cielab_gamut_tools import Gamut, SyntheticGamut

# Load measured display gamut
display = Gamut.from_cgats("measurements.txt")

# Reference gamuts
srgb   = SyntheticGamut.srgb()
bt2020 = SyntheticGamut.bt2020()

# Volume and coverage
print(f"Display volume: {display.volume():.0f}")
intersection = display.intersect(srgb)
print(f"sRGB coverage: {intersection.volume() / srgb.volume() * 100:.1f}%")

# Visualize (returns a matplotlib Figure)
fig = display.plot_rings(reference=srgb)
fig.savefig("rings.png", dpi=150)
```

Available reference gamuts: `srgb()`, `bt2020()`, `dci_p3()`, `display_p3()`, `adobe_rgb()`, or construct a custom gamut from CIE xy primaries and white point:

```python
custom = SyntheticGamut(
    primaries_xy=[[0.68, 0.32], [0.265, 0.69], [0.15, 0.06]],
    white_xy=[0.3127, 0.329],
    gamma=2.2,
)
```

Test signal generation and CGATS export are also available via the API — see the module docstrings for details.

---

## Troubleshooting

**"error: externally-managed-environment" (Ubuntu 24.04+, Debian 12+)**  
Use a virtual environment or pipx — see Installation above.

**CLI command not found after installation**  
The `Scripts` (Windows) or `bin` (macOS/Linux) directory may not be on your PATH. Either add it, or run via `python -m cielab_gamut_tools`.

**File not found errors**  
Pass an absolute path to your measurement file. On Windows you can Shift+right-click the file and choose "Copy as path"; on macOS hold Option when right-clicking and choose "Copy … as Pathname".

**Plot window doesn't appear when using the Python API**  
Call `import matplotlib.pyplot as plt; plt.show()` after plotting, or use `--output` via the CLI to save directly to a file.

---

## Development

```bash
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e ".[dev]"
pytest
```

## Citation

If you use this software in academic work, please cite:

> Smith, E., et al. (2020). "Gamut volume calculation for display color characterization."  
> Journal of the Society for Information Display.

## License

MIT — see [LICENSE](LICENSE) for details.
