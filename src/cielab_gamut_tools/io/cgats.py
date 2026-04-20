"""
CGATS.17 file format parser and writer.

CGATS (Committee for Graphic Arts Technologies Standards) is a standard
ASCII format for color measurement data, commonly used for display and
print color characterization.

This module also supports the IDMS v1.3 format extension for reflective
display measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass
class CgatsData:
    """
    Data parsed from a CGATS file.

    Fields are None when the corresponding columns were not present in the file.

    Attributes:
        rgb: RGB values, shape (N, 3), or None if absent.
        xyz: XYZ tristimulus values, shape (N, 3), or None if absent.
        lab: CIELab values, shape (N, 3), or None if absent.
        metadata: Dict of file metadata and keywords.
    """

    rgb: NDArray[np.floating] | None
    xyz: NDArray[np.floating] | None
    lab: NDArray[np.floating] | None
    metadata: dict


def read_cgats(path: str | Path) -> CgatsData:
    """
    Read a CGATS.17 format file.

    Detects which colorspace columns are present (RGB, XYZ, LAB) and
    returns all available data. Any combination of XYZ and LAB may be
    present; at least one is expected for gamut analysis.

    Args:
        path: Path to the CGATS file.

    Returns:
        CgatsData with rgb, xyz, lab, and metadata fields. Each field is
        None if the corresponding columns were not present in the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If no field names or data rows are found.

    Example:
        >>> data = read_cgats("measurements.txt")
        >>> print(f"Loaded {len(data.rgb)} measurements")
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

            if not line or line.startswith("#"):
                continue

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
                data_rows.append(line.split())
            elif not field_names and _looks_like_field_names(line):
                field_names = line.split()
            else:
                _parse_keyword_line(line, metadata)

    if not field_names:
        raise ValueError("No field names found in CGATS file")
    if not data_rows:
        raise ValueError("No data rows found in CGATS file")

    rgb = _try_extract_columns(data_rows, field_names, ["RGB_R", "RGB_G", "RGB_B"])
    xyz = _try_extract_columns(data_rows, field_names, ["XYZ_X", "XYZ_Y", "XYZ_Z"])
    lab = _try_extract_columns(data_rows, field_names, ["LAB_L", "LAB_A", "LAB_B"])

    return CgatsData(rgb=rgb, xyz=xyz, lab=lab, metadata=metadata)


def write_cgats(
    path: str | Path,
    *,
    rgb: NDArray[np.floating] | None = None,
    xyz: NDArray[np.floating] | None = None,
    lab: NDArray[np.floating] | None = None,
    sample_ids: NDArray[np.integer] | None = None,
    description: str | None = None,
    created: str | None = None,
    file_type: str | None = None,
) -> None:
    """
    Write a CGATS.17 Format 2 file.

    Column order in the output is always: SampleID, RGB (if provided),
    XYZ (if provided), LAB (if provided). At least one of xyz or lab
    must be supplied.

    Args:
        path: Output file path.
        rgb: RGB values, shape (N, 3). Written as RGB_R/G/B columns.
        xyz: XYZ tristimulus values, shape (N, 3). Written as XYZ_X/Y/Z.
        lab: CIELab values, shape (N, 3). Written as LAB_L/A/B.
        sample_ids: Sample ID values, shape (N,). Auto-generated as
            1-based integers if not provided.
        description: Free-text description written as a bare line after
            FORMAT_VERSION (matches MATLAB writeCGATS convention).
        created: Creation date string written as ``CREATED\\t<value>``.
        file_type: Written as ``IDMS_FILE_TYPE\\t<value>`` if provided.

    Raises:
        ValueError: If neither xyz nor lab is provided.
        ValueError: If provided arrays have inconsistent lengths.

    Example:
        >>> write_cgats("envelope.txt", rgb=rgb, lab=lab,
        ...             description="sRGB envelope", file_type="CGE_ENVELOPE")
    """
    if xyz is None and lab is None:
        raise ValueError("At least one of xyz or lab must be provided")

    # Determine N and validate consistency
    n: int | None = None
    for name, arr in [("rgb", rgb), ("xyz", xyz), ("lab", lab)]:
        if arr is not None:
            arr_n = len(arr)
            if n is None:
                n = arr_n
            elif arr_n != n:
                raise ValueError(
                    f"Array length mismatch: expected {n}, got {arr_n} for {name}"
                )
    assert n is not None

    if sample_ids is None:
        ids = np.arange(1, n + 1, dtype=np.float64)
    else:
        ids = np.asarray(sample_ids, dtype=np.float64)

    # Build field list and data matrix
    fields: list[str] = ["SampleID"]
    columns: list[NDArray] = [ids.reshape(-1, 1)]

    if rgb is not None:
        fields += ["RGB_R", "RGB_G", "RGB_B"]
        columns.append(np.asarray(rgb, dtype=np.float64))
    if xyz is not None:
        fields += ["XYZ_X", "XYZ_Y", "XYZ_Z"]
        columns.append(np.asarray(xyz, dtype=np.float64))
    if lab is not None:
        fields += ["LAB_L", "LAB_A", "LAB_B"]
        columns.append(np.asarray(lab, dtype=np.float64))

    data = np.hstack(columns)

    path = Path(path)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("CGATS.17\n")
        f.write("FORMAT_VERSION\t2\n")
        if description is not None:
            f.write(f"{description}\n")
        if file_type is not None:
            f.write(f"IDMS_FILE_TYPE\t{file_type}\n")
        if created is not None:
            f.write(f"CREATED\t{created}\n")
        f.write("BEGIN_DATA_FORMAT\n")
        f.write(" ".join(fields) + "\n")
        f.write("END_DATA_FORMAT\n")
        f.write(f"NUMBER_OF_SETS\t{n}\n")
        f.write("BEGIN_DATA\n")
        for row in data:
            f.write(" ".join(f"{v:g}" for v in row) + "\n")
        f.write("END_DATA\n")


def _looks_like_field_names(line: str) -> bool:
    """Check if a line looks like CGATS field names.

    We require at least one *data* column name (RGB, XYZ, or LAB) to be
    present. This avoids false-positives on lines like ``KEYWORD SampleID``
    which contain an ID token but are metadata declarations, not field lists.
    """
    data_fields = {
        "RGB_R", "RGB_G", "RGB_B",
        "XYZ_X", "XYZ_Y", "XYZ_Z",
        "LAB_L", "LAB_A", "LAB_B",
    }
    parts = set(line.split())
    return bool(parts & data_fields)


def _parse_keyword_line(line: str, metadata: dict) -> None:
    """Parse a CGATS keyword line into the metadata dict."""
    if '"' in line:
        parts = line.split('"')
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[1]
            metadata[key] = value
            return

    parts = line.split(None, 1)
    if len(parts) == 2:
        metadata[parts[0]] = parts[1]
    elif len(parts) == 1:
        metadata[parts[0]] = True


def _try_extract_columns(
    data_rows: list[list[str]],
    field_names: list[str],
    columns: list[str],
) -> NDArray[np.floating] | None:
    """Extract columns if all are present; return None if any are missing."""
    if not all(col in field_names for col in columns):
        return None
    indices = [field_names.index(col) for col in columns]
    values = [[float(row[i]) for i in indices] for row in data_rows]
    return np.array(values, dtype=np.float64)
