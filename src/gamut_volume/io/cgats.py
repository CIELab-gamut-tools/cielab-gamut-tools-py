"""
CGATS.17 file format parser.

CGATS (Committee for Graphic Arts Technologies Standards) is a standard
ASCII format for color measurement data, commonly used for display and
print color characterization.

This module also supports the IDMS v1.3 format extension for reflective
display measurements.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def read_cgats(
    path: str | Path,
) -> tuple[NDArray[np.floating], NDArray[np.floating], dict]:
    """
    Read a CGATS.17 format file containing RGB and XYZ data.

    Args:
        path: Path to the CGATS file.

    Returns:
        A tuple of (rgb, xyz, metadata) where:
        - rgb: RGB values, shape (N, 3)
        - xyz: XYZ tristimulus values, shape (N, 3)
        - metadata: Dict of file metadata and keywords

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required fields are missing or format is invalid.

    Example:
        >>> rgb, xyz, meta = read_cgats("display_measurements.txt")
        >>> print(f"Loaded {len(rgb)} measurements")
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CGATS file not found: {path}")

    metadata: dict = {}
    field_names: list[str] = []
    data_rows: list[list[str]] = []
    in_data_section = False

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Check for section markers
            if line == "BEGIN_DATA_FORMAT":
                continue
            elif line == "END_DATA_FORMAT":
                continue
            elif line == "BEGIN_DATA":
                in_data_section = True
                continue
            elif line == "END_DATA":
                in_data_section = False
                continue

            if in_data_section:
                # Parse data row
                data_rows.append(line.split())
            elif not field_names and _looks_like_field_names(line):
                # Parse field names (usually after BEGIN_DATA_FORMAT)
                field_names = line.split()
            else:
                # Parse keyword/value pairs
                _parse_keyword_line(line, metadata)

    if not field_names:
        raise ValueError("No field names found in CGATS file")
    if not data_rows:
        raise ValueError("No data rows found in CGATS file")

    # Extract RGB and XYZ columns
    rgb = _extract_columns(data_rows, field_names, ["RGB_R", "RGB_G", "RGB_B"])
    xyz = _extract_columns(data_rows, field_names, ["XYZ_X", "XYZ_Y", "XYZ_Z"])

    return rgb, xyz, metadata


def _looks_like_field_names(line: str) -> bool:
    """Check if a line looks like field names (contains known field names)."""
    known_fields = {"RGB_R", "RGB_G", "RGB_B", "XYZ_X", "XYZ_Y", "XYZ_Z", "SAMPLE_ID"}
    parts = set(line.split())
    return bool(parts & known_fields)


def _parse_keyword_line(line: str, metadata: dict) -> None:
    """Parse a CGATS keyword line into the metadata dict."""
    # Handle quoted strings
    if '"' in line:
        parts = line.split('"')
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[1]
            metadata[key] = value
            return

    # Handle simple key-value pairs
    parts = line.split(None, 1)
    if len(parts) == 2:
        metadata[parts[0]] = parts[1]
    elif len(parts) == 1:
        metadata[parts[0]] = True


def _extract_columns(
    data_rows: list[list[str]],
    field_names: list[str],
    columns: list[str],
) -> NDArray[np.floating]:
    """Extract specified columns from data rows as a numpy array."""
    try:
        indices = [field_names.index(col) for col in columns]
    except ValueError as e:
        missing = [col for col in columns if col not in field_names]
        raise ValueError(f"Missing required columns: {missing}") from e

    values = []
    for row in data_rows:
        values.append([float(row[i]) for i in indices])

    return np.array(values, dtype=np.float64)
