from __future__ import annotations

import csv
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import typer
from rich.console import Console

from cielab_gamut_tools.cli._resolve import NAMED_GAMUTS

app = typer.Typer(
    help="Generate reference gamuts and measurement signal lists.",
    no_args_is_help=True,
)

err_console = Console(stderr=True)

_NAMED_LIST = ", ".join(NAMED_GAMUTS)


def _write_rgb_signals_cgats(signals: np.ndarray, bits: int, grid: int) -> str:
    """Return a CGATS string containing only RGB signal values (no XYZ or Lab)."""
    n = len(signals)
    description = (
        f"RGB input signal values: m={grid}, {n} unique surface points, {bits}-bit"
    )
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "CGATS.17",
        "FORMAT_VERSION\t2",
        description,
        f"IDMS_FILE_TYPE\tCGE_SIGNALS",
        f"CREATED\t{created}",
        "BEGIN_DATA_FORMAT",
        "SampleID RGB_R RGB_G RGB_B",
        "END_DATA_FORMAT",
        f"NUMBER_OF_SETS\t{n}",
        "BEGIN_DATA",
    ]
    for i, row in enumerate(signals):
        lines.append(f"{i + 1} {int(row[0])} {int(row[1])} {int(row[2])}")
    lines.append("END_DATA")
    return "\n".join(lines) + "\n"


@app.command(name="rgb-signals")
def rgb_signals(
    grid: Annotated[
        int,
        typer.Option(
            "--grid",
            "-g",
            help="Grid size m (default 11). Signal count = 6m²−12m+8.",
        ),
    ] = 11,
    bits: Annotated[
        int,
        typer.Option("--bits", "-b", help="Output bit depth (default 8)."),
    ] = 8,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: csv or cgats (default cgats).",
        ),
    ] = "cgats",
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file (default: stdout)."),
    ] = None,
) -> None:
    """Generate the normative RGB input signal list for display gamut measurement.

    Produces the unique surface points of the RGB cube tessellation at grid
    resolution m, scaled to the requested bit depth. The normative signal set
    uses m=11 (602 unique points) as defined in IDMS v1.3 §5.32,
    IEC 62977-3-5, and IEC 62906-6-1.
    """
    if format not in ("csv", "cgats"):
        err_console.print("[red]--format must be 'csv' or 'cgats'[/red]")
        raise typer.Exit(1)

    from cielab_gamut_tools.measurement import make_rgb_signals

    try:
        signals = make_rgb_signals(m=grid, bits=bits)
    except ValueError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["R", "G", "B"])
        for row in signals:
            writer.writerow([int(row[0]), int(row[1]), int(row[2])])
        text = buf.getvalue()
    else:  # cgats
        text = _write_rgb_signals_cgats(signals, bits=bits, grid=grid)

    if output:
        output.write_text(text, encoding="utf-8")
        sys.stdout.write(
            f"Written {len(signals)} signals ({grid=}, {bits}-bit) to {output}\n"
        )
    else:
        sys.stdout.write(text)


@app.command()
def synthetic(
    gamut: Annotated[
        Optional[str],
        typer.Argument(
            help=(
                f"Named gamut: {_NAMED_LIST}. "
                "Omit to supply custom primaries via --primaries."
            )
        ),
    ] = None,
    primaries: Annotated[
        Optional[str],
        typer.Option(
            "--primaries",
            help=(
                "Custom primary chromaticities: rx,ry,gx,gy,bx,by "
                "(6 comma-separated CIE xy values). "
                "Requires --white. Mutually exclusive with a named gamut."
            ),
        ),
    ] = None,
    white: Annotated[
        Optional[str],
        typer.Option(
            "--white",
            "-w",
            help="White point chromaticity: wx,wy (e.g. 0.3127,0.3290 for D65).",
        ),
    ] = None,
    gamma: Annotated[
        float,
        typer.Option("--gamma", help="Display gamma exponent (default 2.2)."),
    ] = 2.2,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="CGATS output mode: envelope (RGB+Lab), measurement (RGB+XYZ), or all.",
        ),
    ] = "envelope",
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path (default: stdout)."),
    ] = None,
) -> None:
    """Generate a synthetic gamut CGATS file from a named gamut or custom primaries.

    Named gamuts match the definitions in IEC 62906-6-1 and IDMS v1.3.
    Custom gamuts require --primaries (6 xy values) and --white (white point xy).

    \b
    Examples:
        cielab-tools generate synthetic srgb --output srgb.txt
        cielab-tools generate synthetic bt.2020 --mode measurement --output bt2020.txt
        cielab-tools generate synthetic --primaries 0.64,0.33,0.21,0.71,0.15,0.06 \\
            --white 0.3127,0.3290 --gamma 2.2 --output custom.txt
    """
    from cielab_gamut_tools import SyntheticGamut

    # Validate mutual exclusion
    if gamut is None and primaries is None:
        err_console.print(
            "[red]Provide a named gamut or --primaries.[/red]\n"
            f"  Named gamuts: {_NAMED_LIST}"
        )
        raise typer.Exit(1)

    if gamut is not None and primaries is not None:
        err_console.print(
            "[red]Provide either a named gamut or --primaries, not both.[/red]"
        )
        raise typer.Exit(1)

    if mode not in ("envelope", "measurement", "all"):
        err_console.print(
            "[red]--mode must be 'envelope', 'measurement', or 'all'.[/red]"
        )
        raise typer.Exit(1)

    # Build the SyntheticGamut
    if gamut is not None:
        method = NAMED_GAMUTS.get(gamut.lower())
        if method is None:
            err_console.print(
                f"[red]Unknown gamut '{gamut}'.[/red]\n"
                f"  Named gamuts: {_NAMED_LIST}"
            )
            raise typer.Exit(1)
        sg = getattr(SyntheticGamut, method)()
    else:
        # Custom primaries
        if white is None:
            err_console.print("[red]--white is required when using --primaries.[/red]")
            raise typer.Exit(1)
        try:
            p_vals = [float(x) for x in primaries.split(",")]  # type: ignore[union-attr]
            if len(p_vals) != 6:
                raise ValueError(f"expected 6 values, got {len(p_vals)}")
            prim_xy = np.array(p_vals).reshape(3, 2)
        except ValueError as exc:
            err_console.print(f"[red]Invalid --primaries: {exc}[/red]")
            raise typer.Exit(1) from exc
        try:
            w_vals = [float(x) for x in white.split(",")]
            if len(w_vals) != 2:
                raise ValueError(f"expected 2 values, got {len(w_vals)}")
            white_xy = np.array(w_vals)
        except ValueError as exc:
            err_console.print(f"[red]Invalid --white: {exc}[/red]")
            raise typer.Exit(1) from exc
        sg = SyntheticGamut(prim_xy, white_xy, gamma=gamma)

    # Write output
    if output is not None:
        try:
            sg.to_cgats(output, mode=mode)
        except ValueError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
        sys.stdout.write(f"Written to {output}\n")
    else:
        # Capture CGATS text via a temporary file and write to stdout
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp_path = tmp.name
        try:
            sg.to_cgats(tmp_path, mode=mode)
            sys.stdout.write(Path(tmp_path).read_text(encoding="utf-8"))
        except ValueError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
        finally:
            os.unlink(tmp_path)
