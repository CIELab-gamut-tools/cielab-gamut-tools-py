# cielab-gamut-tools

Calculate and visualize CIELab colour gamuts of displays.

This is a Python port of the [gamut-volume-m](https://github.com/CIELab-gamut-tools/gamut-volume-m) MATLAB library.

## Features

- Load gamut data from CGATS.17 ASCII files or RGB/XYZ matrices
- Support for emissive and reflective displays (IDMS v1.3 format)
- Calculate gamut volumes via cylindrical integration in CIELab space
- Compute gamut intersections for coverage analysis
- Generate synthetic reference gamuts (sRGB, BT.2020, DCI-P3, etc.)
- Visualize gamuts as 3D surfaces or 2D rings

## Prerequisites

This library requires **Python 3.10 or later**.

**Check if Python is installed:**
- Windows: Open Command Prompt and type `python --version`
- macOS/Linux: Open Terminal and type `python3 --version`

**Don't have Python?** Download from [python.org](https://www.python.org/downloads/)
- Windows: Check "Add Python to PATH" during installation
- macOS: Consider using [Homebrew](https://brew.sh/): `brew install python@3.11`

## Installation

### Windows
```cmd
python -m pip install cielab-gamut-tools
```

### macOS/Linux

**Modern Linux distributions (Ubuntu 24.04+, Debian 12+)** require using a virtual environment or pipx due to PEP 668. Choose one of these methods:

**Option 1: Using a virtual environment (recommended)**
```bash
# Create and activate virtual environment
python3 -m venv gamut_env
source gamut_env/bin/activate

# Install the library
pip install cielab-gamut-tools

# Now you can use it normally in Python
python3
>>> from cielab_gamut_tools import SyntheticGamut
```
To deactivate later, type `deactivate`. You'll need to activate (`source gamut_env/bin/activate`) each time you start a new terminal session.

**Option 2: Using pipx (simpler but limited)**
```bash
# Install pipx if you don't have it
sudo apt install pipx
pipx ensurepath

# Install cielab-gamut-tools
pipx install cielab-gamut-tools

# Run your scripts with pipx
pipx run --spec cielab-gamut-tools python3 your_script.py
```
Note: pipx is primarily designed for command-line tools. For a library like this, a virtual environment (Option 1) is usually more convenient.

**Option 3: Older macOS/Linux systems**
```bash
python3 -m pip install cielab-gamut-tools
```

<details>
<summary><strong>Windows: Optional virtual environment</strong> (click to expand)</summary>

Virtual environments keep packages isolated and avoid dependency conflicts.

```cmd
python -m venv gamut_env
gamut_env\Scripts\activate
pip install cielab-gamut-tools
```

To deactivate the virtual environment later, type `deactivate`.
</details>

<details>
<summary><strong>Install from source</strong> (click to expand)</summary>

```bash
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e .
```
</details>

## How to Use

There are two main ways to run Python code:

**Option 1: Interactive Python REPL** (good for experimenting)

Start Python by typing `python` (Windows) or `python3` (macOS/Linux) in your terminal:

```python
>>> from cielab_gamut_tools import SyntheticGamut
>>> srgb = SyntheticGamut.srgb()
>>> print(srgb.volume())
830330.5
```

**Option 2: Run a Python script** (good for repeatable analysis)

1. Create a file `analyze_gamut.py` with your code
2. Run it from the terminal:
   - Windows: `python analyze_gamut.py`
   - macOS/Linux: `python3 analyze_gamut.py`

## Quick Start

```python
from cielab_gamut_tools import Gamut, SyntheticGamut

# Load measured display gamut from CGATS file
display = Gamut.from_cgats("measurements.txt")

# Create standard reference gamuts
srgb = SyntheticGamut.srgb()
bt2020 = SyntheticGamut.bt2020()

# Calculate volumes
print(f"Display volume: {display.volume():.0f}")
print(f"sRGB volume: {srgb.volume():.0f}")

# Calculate sRGB coverage
intersection = display.intersect(srgb)
coverage = intersection.volume() / srgb.volume() * 100
print(f"sRGB coverage: {coverage:.1f}%")

# Visualize
import matplotlib.pyplot as plt
display.plot_rings(reference=srgb)
plt.show()  # Required to display the plot window
```

## Complete Working Example

Save this as `example_srgb_coverage.py`:

```python
from cielab_gamut_tools import Gamut, SyntheticGamut
import matplotlib.pyplot as plt

# Create reference gamut
srgb = SyntheticGamut.srgb()
print(f"sRGB gamut volume: {srgb.volume():.0f}")

# Load your display measurements (replace with your actual file)
display = Gamut.from_cgats("my_display.txt")
print(f"Display gamut volume: {display.volume():.0f}")

# Calculate coverage
intersection = display.intersect(srgb)
coverage = intersection.volume() / srgb.volume() * 100
print(f"sRGB coverage: {coverage:.1f}%")

# Show visualization
display.plot_rings(reference=srgb)
plt.show()
```

**Expected output:**
```
sRGB gamut volume: 830331
Display gamut volume: 956234
sRGB coverage: 98.3%
```

## Working with Measurement Files

### Finding Your File Path

- **Windows:** Shift + Right-click file → "Copy as path"
- **macOS:** Right-click file → Hold Option key → "Copy ... as Pathname"

### Using File Paths in Code

```python
# Windows (use raw strings with backslashes or forward slashes)
gamut = Gamut.from_cgats(r"C:\Users\YourName\Documents\measurements.txt")
# or
gamut = Gamut.from_cgats("C:/Users/YourName/Documents/measurements.txt")

# macOS/Linux
gamut = Gamut.from_cgats("/Users/yourname/Documents/measurements.txt")

# Relative paths (file in same directory as script)
gamut = Gamut.from_cgats("measurements.txt")
```

## Reference Gamuts

The library includes built-in reference gamuts:

```python
srgb = SyntheticGamut.srgb()        # sRGB (D65, gamma 2.2)
bt2020 = SyntheticGamut.bt2020()    # BT.2020 (D65, gamma 2.4)
dci_p3 = SyntheticGamut.dci_p3()    # DCI-P3 (DCI white, gamma 2.6)
display_p3 = SyntheticGamut.display_p3()  # Display P3 (D65, gamma 2.2)
```

Or create custom gamuts:

```python
custom = SyntheticGamut(
    primaries_xy=[[0.68, 0.32], [0.265, 0.69], [0.15, 0.06]],
    white_xy=[0.3127, 0.329],
    gamma=2.2
)
```

## Troubleshooting

**"error: externally-managed-environment" (Ubuntu 24.04+, Debian 12+)**
- This is due to PEP 668 protecting system Python packages
- **Solution:** Use pipx (see Installation section above) or create a virtual environment
- Do NOT use `--break-system-packages` as it can break your system

**"python is not recognized" (Windows)**
- Reinstall Python and check "Add Python to PATH" during installation
- Or use the full path: `C:\Python311\python.exe -m pip install cielab-gamut-tools`

**"pip: command not found"**
- Use `python -m pip` instead of just `pip`
- macOS/Linux: Use `python3 -m pip`

**PATH warnings with Windows Store Python**
- If you see warnings about Scripts directory not on PATH after installation
- The library will still work, but you may need to use full paths for command-line tools
- To fix: Add the directory mentioned in the warning to your PATH environment variable

**Import errors after installation**
- Ensure you're in the same environment where you installed the package
- Verify installation: `pip show cielab-gamut-tools`
- If using a virtual environment, make sure it's activated

**Plot windows don't appear**
- Add `import matplotlib.pyplot as plt` at the top of your script
- Add `plt.show()` after calling `.plot_rings()` or `.plot_surface()`

**"No module named 'cielab_gamut_tools'" after installation**
- Make sure you're running Python from the same environment where you installed
- Try reinstalling: `pip install --force-reinstall cielab-gamut-tools`

**File not found errors**
- Use absolute paths to measurement files (see "Working with Measurement Files" above)
- Check that the file exists and the path is correct

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py.git
cd cielab-gamut-tools-py
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=cielab_gamut_tools --cov-report=term-missing

# Type checking
mypy src

# Linting
ruff check src tests
```

## Citation

If you use this software in academic work, please cite:

> Smith, E., et al. (2020). "Gamut volume calculation for display color characterization."
> Journal of the Society for Information Display.

## License

MIT License - see [LICENSE](LICENSE) for details.
