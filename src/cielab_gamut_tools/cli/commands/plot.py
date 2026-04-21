from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from cielab_gamut_tools.cli._resolve import NAMED_GAMUTS, resolve_gamut

app = typer.Typer(
    help="Visualise gamut data as ring diagrams or 3D surfaces.",
    no_args_is_help=True,
)

err_console = Console(stderr=True)

_SUPPORTED_FORMATS = {".png", ".pdf", ".svg", ".jpg", ".jpeg", ".tiff"}


def _save_or_show(fig, output: Optional[Path], show: bool, dpi: int) -> None:
    """Save figure to file and/or show it interactively."""
    import matplotlib.pyplot as plt

    if output is not None:
        suffix = output.suffix.lower()
        if suffix not in _SUPPORTED_FORMATS:
            err_console.print(
                f"[red]Unsupported output format '{suffix}'. "
                f"Use one of: {', '.join(sorted(_SUPPORTED_FORMATS))}[/red]"
            )
            raise typer.Exit(1)
        fig.savefig(output, dpi=dpi, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)


@app.command()
def rings(
    gamut: Annotated[
        str,
        typer.Argument(
            help=(
                "CGATS file or named gamut to plot. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            )
        ),
    ],
    reference: Annotated[
        Optional[str],
        typer.Option(
            "--reference",
            "-r",
            help=(
                "Reference gamut — file path or named gamut. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            ),
        ),
    ] = None,
    intersection: Annotated[
        bool,
        typer.Option(
            "--intersection",
            help="Show gamut rings as intersection of DUT and reference (requires --reference).",
        ),
    ] = False,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Save plot to this file (png, pdf, svg, jpg, tiff)."),
    ] = None,
    show: Annotated[
        bool,
        typer.Option("--show", help="Display the plot interactively."),
    ] = False,
    dpi: Annotated[
        int,
        typer.Option("--dpi", help="Resolution for raster output formats."),
    ] = 150,
) -> None:
    """Plot gamut rings diagram (2D L*-encoded concentric rings in a*-b* space)."""
    if output is None:
        show = True

    if intersection and reference is None:
        err_console.print("[red]--intersection requires --reference.[/red]")
        raise typer.Exit(1)

    # Use Agg backend when only saving (avoids display dependency)
    if output is not None and not show:
        import matplotlib
        matplotlib.use("Agg")

    dut_gamut = resolve_gamut(gamut)
    ref_gamut = resolve_gamut(reference) if reference is not None else None

    from cielab_gamut_tools.plotting.rings import plot_rings

    fig = plot_rings(
        dut_gamut,
        reference=ref_gamut,
        intersection_plot=intersection,
    )

    _save_or_show(fig, output, show, dpi)


@app.command()
def surface(
    gamuts: Annotated[
        list[str],
        typer.Argument(
            help=(
                "One or more CGATS files or named gamuts to plot on the same axes. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            )
        ),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Save plot to this file (png, pdf, svg, jpg, tiff)."),
    ] = None,
    show: Annotated[
        bool,
        typer.Option("--show", help="Display the plot interactively."),
    ] = False,
    dpi: Annotated[
        int,
        typer.Option("--dpi", help="Resolution for raster output formats."),
    ] = 150,
    alpha: Annotated[
        float,
        typer.Option("--alpha", help="Surface transparency per gamut (0=transparent, 1=opaque)."),
    ] = 0.8,
) -> None:
    """Plot one or more 3D gamut surfaces in CIELab space.

    When multiple gamuts are given they are overlaid on the same axes.
    Use --alpha < 1 to see through overlapping surfaces.
    """
    if not gamuts:
        err_console.print("[red]Provide at least one gamut.[/red]")
        raise typer.Exit(1)

    if output is None:
        show = True

    if output is not None and not show:
        import matplotlib
        matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    from cielab_gamut_tools.plotting.surface import plot_surface

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    for arg in gamuts:
        gamut = resolve_gamut(arg)
        plot_surface(gamut, ax=ax, alpha=alpha)

    _save_or_show(fig, output, show, dpi)
