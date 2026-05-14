import json
from urllib.error import URLError
from urllib.request import urlopen

from rich.console import Console

from cielab_gamut_tools import __version__


def _check_for_update() -> str | None:
    """Return the latest PyPI version string if newer than installed, else None."""
    try:
        with urlopen(
            "https://pypi.org/pypi/cielab-gamut-tools/json", timeout=3
        ) as resp:
            latest = json.loads(resp.read())["info"]["version"]
    except (URLError, KeyError, ValueError, OSError):
        return None

    def _parse(v: str) -> tuple[int, ...]:
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return (0,)

    if _parse(latest) > _parse(__version__):
        return latest
    return None


_STANDARDS = [
    (
        "ICDM Information Display Measurements Standard (IDMS) v1.3, \u00a75.32",
        "Colour Gamut Envelope \u2014 Colour Capability",
    ),
    (
        "IEC 62977-3-5 \u2014 Electronic displays:",
        "Evaluation of optical performance \u2014 Colour capabilities",
    ),
    (
        "IEC 62906-6-1 \u2014 Displays:",
        "Colour gamut intersection visualisation method",
    ),
]


def about_command() -> None:
    """Display standards compliance, citation, and algorithm information."""
    console = Console()

    console.print(f"\n[bold]cielab-gamut-tools {__version__}[/bold]\n")
    console.print(
        "Python implementation of CIELab gamut volume calculation.\n"
        "Port of the MATLAB reference implementation on which the following\n"
        "IEC TC110 and ICDM standards are based.\n"
    )

    console.print("[bold]Standards Compliance:[/bold]")
    for title, subtitle in _STANDARDS:
        console.print(f"  \u2022 {title}")
        console.print(f"    {subtitle}")
    console.print(
        "  [dim][Final publication numbers subject to IEC TC110 ballot][/dim]\n"
    )

    console.print("[bold]Citation:[/bold]")
    console.print(
        "  Smith, E., et al. (2020). \u201cGamut volume calculation for display\n"
        "  colour characterisation.\u201d "
        "Journal of the Society for Information Display.\n"
    )

    console.print("[bold]Algorithm:[/bold]")
    console.print(
        "  Cylindrical integration in CIELab space via M\u00f6ller-Trumbore\n"
        "  ray-triangle intersection. Bradford chromatic adaptation to D50.\n"
        "  Reference implementation: cielab-gamut-tools-m (MATLAB/Octave).\n"
    )

    console.print(
        "[bold]Repository:[/bold]   "
        "https://github.com/CIELab-gamut-tools/cielab-gamut-tools-py"
    )
    console.print(
        "[bold]Documentation:[/bold] https://cielab-gamut-tools.readthedocs.io"
    )
    console.print("[bold]Licence:[/bold]       MIT\n")

    latest = _check_for_update()
    if latest:
        console.print(
            f"[yellow]A new version is available: {latest} "
            f"(you have {__version__})[/yellow]"
        )
        console.print("  [dim]pipx upgrade cielab-gamut-tools[/dim]")
        console.print("  [dim]pip install --upgrade cielab-gamut-tools[/dim]\n")
