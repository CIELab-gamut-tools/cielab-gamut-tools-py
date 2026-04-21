from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from cielab_gamut_tools import Gamut, SyntheticGamut

_err = Console(stderr=True)

NAMED_GAMUTS: dict[str, str] = {
    "srgb": "srgb",
    "bt.2020": "bt2020",
    "dci-p3": "dci_p3",
    "display-p3": "display_p3",
    "adobe-rgb": "adobe_rgb",
}

GAMUT_DISPLAY_NAMES: dict[str, str] = {
    "srgb": "sRGB",
    "bt.2020": "BT.2020",
    "dci-p3": "DCI-P3",
    "display-p3": "Display P3",
    "adobe-rgb": "Adobe RGB",
}


def display_name(arg: str) -> str:
    """Return a human-readable label for a gamut argument."""
    name = GAMUT_DISPLAY_NAMES.get(arg.lower())
    return name if name is not None else Path(arg).name


def resolve_gamut(arg: str) -> Gamut:
    """Resolve a CLI argument to a Gamut — accepts a file path or a named gamut.

    Named gamuts: srgb, bt2020, dci-p3, display-p3, adobe-rgb.
    """
    path = Path(arg)
    if path.exists():
        try:
            return Gamut.from_cgats(path)
        except Exception as exc:
            _err.print(f"[red]Error loading {arg}: {exc}[/red]")
            raise typer.Exit(1) from exc

    method = NAMED_GAMUTS.get(arg.lower())
    if method is not None:
        return getattr(SyntheticGamut, method)().gamut

    _err.print(
        f"[red]Cannot resolve '{arg}':[/red]\n"
        f"  • As a file: [yellow]{path}[/yellow] does not exist.\n"
        f"  • As a named gamut: '{arg}' is not recognised.\n"
        f"  Named gamuts: {', '.join(NAMED_GAMUTS)}"
    )
    raise typer.Exit(1)
