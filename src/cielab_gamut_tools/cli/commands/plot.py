from __future__ import annotations

from enum import Enum
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


class _Primaries(str, Enum):
    none = "none"
    rgb = "rgb"
    all = "all"


class _PrimaryOrigin(str, Enum):
    centre = "centre"
    ring = "ring"


class _PrimaryColor(str, Enum):
    input = "input"
    output = "output"


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


def _parse_float_pair(value: str, flag: str) -> tuple[float, float]:
    """Parse 'A,B' into (float(A), float(B)), exit with error on failure."""
    parts = value.split(",")
    if len(parts) != 2:
        err_console.print(f"[red]{flag} expects two comma-separated numbers, e.g. {flag}=-100,100[/red]")
        raise typer.Exit(1)
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        err_console.print(f"[red]{flag}: could not parse '{value}' as two numbers[/red]")
        raise typer.Exit(1)


def _parse_style_list(
    style_str: str,
    n_gamuts: int,
    default_wireframe: bool,
    default_alpha: float,
) -> list[tuple[bool, float]]:
    """Parse --style into per-gamut (wireframe, alpha) pairs."""
    parts = style_str.split(",")
    result: list[tuple[bool, float]] = []
    for i in range(n_gamuts):
        raw = parts[i].strip() if i < len(parts) else ""
        if not raw:
            result.append((default_wireframe, default_alpha))
        elif raw == "wireframe":
            result.append((True, default_alpha))
        elif raw.startswith("alpha:"):
            try:
                a = float(raw[6:])
            except ValueError:
                err_console.print(f"[red]--style: invalid alpha value in '{raw}'[/red]")
                raise typer.Exit(1)
            result.append((False, a))
        else:
            err_console.print(
                f"[red]--style: unknown token '{raw}' "
                f"(expected 'wireframe', 'alpha:FLOAT', or empty)[/red]"
            )
            raise typer.Exit(1)
    return result


def _parse_float_list(value: str, flag: str) -> list[float]:
    """Parse 'A,B,...' into a list of floats, exit with error on failure."""
    try:
        return [float(x) for x in value.split(",")]
    except ValueError:
        err_console.print(f"[red]{flag}: could not parse '{value}' as a list of numbers[/red]")
        raise typer.Exit(1)


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
    # ── Reference options ────────────────────────────────────────────────────
    reference: Annotated[
        Optional[str],
        typer.Option(
            "--reference", "-r",
            help=(
                "Reference gamut — file path or named gamut. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            ),
        ),
    ] = None,
    reference2: Annotated[
        Optional[str],
        typer.Option(
            "--reference2",
            help="Second reference gamut — shown as an outer dotted ring only.",
        ),
    ] = None,
    intersection: Annotated[
        bool,
        typer.Option(
            "--intersection", "-i",
            help="Show gamut rings as intersection of DUT and reference (requires --reference).",
        ),
    ] = False,
    # ── Ring levels ──────────────────────────────────────────────────────────
    l_rings: Annotated[
        Optional[str],
        typer.Option(
            "--l-rings",
            help=(
                "Comma-separated L* values for inner rings "
                "(default '10,20,30,40,50,60,70,80,90')."
            ),
        ),
    ] = None,
    # ── Colour bands ─────────────────────────────────────────────────────────
    show_bands: Annotated[
        bool,
        typer.Option("--bands/--no-bands", help="Show/hide colour-fill bands between rings."),
    ] = True,
    band_chroma: Annotated[
        Optional[float],
        typer.Option("--band-chroma", help="Chroma of band fill colours (default 50)."),
    ] = None,
    band_ls: Annotated[
        Optional[str],
        typer.Option(
            "--band-ls",
            help=(
                "Band lightness — single value or 'LO,HI' range interpolated across bands "
                "(default '20,90'). Use --band-ls=VAL for negative values."
            ),
        ),
    ] = None,
    # ── Primary indicators ───────────────────────────────────────────────────
    primaries: Annotated[
        _Primaries,
        typer.Option(
            "--primaries",
            help="Primary-colour arrows: 'none', 'rgb' (default), or 'all' (R,G,B,C,M,Y).",
        ),
    ] = _Primaries.rgb,
    ref_primaries: Annotated[
        _Primaries,
        typer.Option(
            "--ref-primaries",
            help="Reference primary-colour arrows: 'none' (default), 'rgb', or 'all'.",
        ),
    ] = _Primaries.none,
    primary_color: Annotated[
        _PrimaryColor,
        typer.Option(
            "--primary-color",
            help=(
                "Primary arrow head colour: 'output' (default, uses measured Lab→sRGB) "
                "or 'input' (nominal R/G/B colour)."
            ),
        ),
    ] = _PrimaryColor.output,
    primary_origin: Annotated[
        _PrimaryOrigin,
        typer.Option(
            "--primary-origin",
            help="Where primary arrows start: 'centre' (default) or 'ring' (outer ring boundary).",
        ),
    ] = _PrimaryOrigin.centre,
    show_cent_mark: Annotated[
        bool,
        typer.Option(
            "--cent-mark/--no-cent-mark",
            help="Show/hide the centre cross marker (default: show).",
        ),
    ] = True,
    # ── Constant-chroma reference circles ────────────────────────────────────
    chroma_rings: Annotated[
        Optional[str],
        typer.Option(
            "--chroma-rings",
            help="Draw constant-chroma reference circles at these C* radii (comma-separated, e.g. 50,100,150).",
        ),
    ] = None,
    # ── Plot decoration ───────────────────────────────────────────────────────
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Override the auto-generated plot title."),
    ] = None,
    no_title: Annotated[
        bool,
        typer.Option("--no-title", help="Suppress the plot title entirely."),
    ] = False,
    # ── Figure geometry ───────────────────────────────────────────────────────
    figsize: Annotated[
        Optional[str],
        typer.Option(
            "--figsize",
            help="Figure size as 'W,H' in inches (default '8,8').",
        ),
    ] = None,
    xlim: Annotated[
        Optional[str],
        typer.Option(
            "--xlim",
            help="Override a* axis limits as 'MIN,MAX'. Use --xlim=VAL for negative values.",
        ),
    ] = None,
    ylim: Annotated[
        Optional[str],
        typer.Option(
            "--ylim",
            help="Override b* axis limits as 'MIN,MAX'. Use --ylim=VAL for negative values.",
        ),
    ] = None,
    # ── Output ────────────────────────────────────────────────────────────────
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

    # ── Parse comma-separated options ────────────────────────────────────────
    parsed_l_rings: list[float] | None = (
        _parse_float_list(l_rings, "--l-rings") if l_rings is not None else None
    )

    parsed_band_ls: float | tuple | list | None = None
    if band_ls is not None:
        vals = _parse_float_list(band_ls, "--band-ls")
        parsed_band_ls = vals[0] if len(vals) == 1 else tuple(vals) if len(vals) == 2 else vals

    parsed_chroma_rings: list[float] = (
        _parse_float_list(chroma_rings, "--chroma-rings") if chroma_rings is not None else []
    )

    parsed_figsize: tuple[float, float] = (8.0, 8.0)
    if figsize is not None:
        parsed_figsize = _parse_float_pair(figsize, "--figsize")

    parsed_xlim: tuple[float, float] | None = (
        _parse_float_pair(xlim, "--xlim") if xlim is not None else None
    )
    parsed_ylim: tuple[float, float] | None = (
        _parse_float_pair(ylim, "--ylim") if ylim is not None else None
    )

    # ── Resolve title sentinel ────────────────────────────────────────────────
    if no_title:
        resolved_title = None
    elif title is not None:
        resolved_title = title
    else:
        resolved_title = "auto"

    # ── Build kwargs ─────────────────────────────────────────────────────────
    kwargs: dict = dict(
        intersection_plot=intersection,
        show_bands=show_bands,
        primaries=primaries.value,
        ref_primaries=ref_primaries.value,
        primary_color=primary_color.value,
        primary_origin=primary_origin.value,
        cent_mark="+k" if show_cent_mark else None,
        chroma_rings=parsed_chroma_rings,
        figsize=parsed_figsize,
        title=resolved_title,
    )
    if parsed_l_rings is not None:
        kwargs["l_rings"] = parsed_l_rings
    if band_chroma is not None:
        kwargs["band_chroma"] = band_chroma
    if parsed_band_ls is not None:
        kwargs["band_ls"] = parsed_band_ls
    if parsed_xlim is not None:
        kwargs["xlim"] = parsed_xlim
    if parsed_ylim is not None:
        kwargs["ylim"] = parsed_ylim

    dut_gamut = resolve_gamut(gamut)
    ref_gamut = resolve_gamut(reference) if reference is not None else None
    ref2_gamut = resolve_gamut(reference2) if reference2 is not None else None

    from cielab_gamut_tools.plotting.rings import plot_rings

    fig, _ax = plot_rings(
        dut_gamut,
        reference=ref_gamut,
        reference2=ref2_gamut,
        **kwargs,
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
    alpha: Annotated[
        Optional[float],
        typer.Option("--alpha", help="Surface transparency for solid gamuts (0=transparent, 1=opaque). Default: 0.8."),
    ] = None,
    wireframe: Annotated[
        bool,
        typer.Option("--wireframe", help="Render all gamuts as wireframe (edges only, no fill)."),
    ] = False,
    style: Annotated[
        Optional[str],
        typer.Option(
            "--style",
            help=(
                "Per-gamut rendering style: comma-separated list aligned with gamut arguments. "
                "Each entry: 'wireframe', 'alpha:FLOAT', or empty to use global defaults. "
                "Cannot be combined with --wireframe or --alpha."
            ),
        ),
    ] = None,
    # ── Plot decoration ───────────────────────────────────────────────────────
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Set the plot title."),
    ] = None,
    # ── Figure geometry ───────────────────────────────────────────────────────
    figsize: Annotated[
        Optional[str],
        typer.Option("--figsize", help="Figure size as 'W,H' in inches (default '10,8')."),
    ] = None,
    xlim: Annotated[
        Optional[str],
        typer.Option("--xlim", help="Override a* axis limits as 'MIN,MAX' (default '-128,128')."),
    ] = None,
    ylim: Annotated[
        Optional[str],
        typer.Option("--ylim", help="Override b* axis limits as 'MIN,MAX' (default '-128,128')."),
    ] = None,
    zlim: Annotated[
        Optional[str],
        typer.Option("--zlim", help="Override L* axis limits as 'MIN,MAX' (default '0,100')."),
    ] = None,
    # ── 3D view angle ─────────────────────────────────────────────────────────
    elev: Annotated[
        Optional[float],
        typer.Option("--elev", help="3D view elevation angle in degrees."),
    ] = None,
    azim: Annotated[
        Optional[float],
        typer.Option("--azim", help="3D view azimuth angle in degrees."),
    ] = None,
    # ── Output ────────────────────────────────────────────────────────────────
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
    """Plot one or more 3D gamut surfaces in CIELab space.

    When multiple gamuts are given they are overlaid on the same axes.
    Use --alpha < 1 to see through overlapping solid surfaces, or --wireframe
    to render all gamuts as edges only. For per-gamut control use --style.
    """
    if not gamuts:
        err_console.print("[red]Provide at least one gamut.[/red]")
        raise typer.Exit(1)

    if style is not None and (wireframe or alpha is not None):
        err_console.print("[red]--style cannot be combined with --wireframe or --alpha.[/red]")
        raise typer.Exit(1)

    if output is None:
        show = True

    if output is not None and not show:
        import matplotlib
        matplotlib.use("Agg")

    # ── Parse options ────────────────────────────────────────────────────────
    parsed_figsize = _parse_float_pair(figsize, "--figsize") if figsize is not None else (10.0, 8.0)
    parsed_xlim = _parse_float_pair(xlim, "--xlim") if xlim is not None else None
    parsed_ylim = _parse_float_pair(ylim, "--ylim") if ylim is not None else None
    parsed_zlim = _parse_float_pair(zlim, "--zlim") if zlim is not None else None

    global_alpha = alpha if alpha is not None else 0.8
    per_gamut: list[tuple[bool, float]] = (
        _parse_style_list(style, len(gamuts), wireframe, global_alpha)
        if style is not None
        else [(wireframe, global_alpha)] * len(gamuts)
    )

    import matplotlib.pyplot as plt

    from cielab_gamut_tools.plotting.surface import plot_surface

    fig = plt.figure(figsize=parsed_figsize)
    ax = fig.add_subplot(111, projection="3d")

    for arg, (wf, al) in zip(gamuts, per_gamut):
        g = resolve_gamut(arg)
        plot_surface(g, ax=ax, wireframe=wf, alpha=al)

    # Apply overrides to the shared axes after all gamuts are drawn
    if title is not None:
        ax.set_title(title)
    if parsed_xlim is not None:
        ax.set_xlim(*parsed_xlim)
    if parsed_ylim is not None:
        ax.set_ylim(*parsed_ylim)
    if parsed_zlim is not None:
        ax.set_zlim(*parsed_zlim)
    if elev is not None or azim is not None:
        ax.view_init(elev=elev, azim=azim)

    _save_or_show(fig, output, show, dpi)
