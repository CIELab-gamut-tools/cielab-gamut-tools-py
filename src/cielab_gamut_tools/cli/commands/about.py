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
        "Python implementation of CIELab gamut volume calculation for\n"
        "display colour characterisation. Port of the MATLAB reference\n"
        "implementation on which the following IEC TC110 and ICDM\n"
        "standards are based.\n"
    )

    console.print("[bold]Standards Compliance:[/bold]")
    for title, subtitle in _STANDARDS:
        console.print(f"  \u2022 {title}")
        console.print(f"    {subtitle}")

    console.print("[bold]Citations:[/bold]")
    console.print(
        "  Gamut volume calculation:\n"
        "  E. Smith, R. L. Heckaman, K. Lang, J. Penczek, J. Bergquist (2020).\n"
        "  \u201cMeasuring the color capability of modern display systems.\u201d\n"
        "  Journal of the Society for Information Display, 28(6), 548\u2013556.\n"
        "  https://doi.org/10.1002/jsid.918\n"
    )
    console.print(
        "  Gamut rings concept:\n"
        "  K. Masaoka, F. Jiang, M. D. Fairchild, R. L. Heckaman (2020).\n"
        "  \u201cAnalysis of color volume of multi-chromatic displays using gamut rings.\u201d\n"
        "  Journal of the Society for Information Display, 28(3), 273\u2013286.\n"
        "  https://doi.org/10.1002/jsid.852\n"
    )
    console.print(
        "  Gamut ring intersection:\n"
        "  K. Masaoka, E. Smith, K. Lang, B. Berkeley, J. Bergquist, J. Penczek (2025).\n"
        "  \u201cVisualization of reproducible object colors in standard color spaces\n"
        "  using the gamut ring intersection.\u201d\n"
        "  Journal of the Society for Information Display, 33(4), 231\u2013245.\n"
        "  https://doi.org/10.1002/jsid.2031\n"
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
