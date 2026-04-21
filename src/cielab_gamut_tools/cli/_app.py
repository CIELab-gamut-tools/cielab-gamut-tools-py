from typing import Optional

import typer

from cielab_gamut_tools import __version__
from cielab_gamut_tools.cli.commands import calculate, generate, plot
from cielab_gamut_tools.cli.commands.about import about_command

app = typer.Typer(
    name="cielab-tools",
    help="CIELab gamut analysis tools for display colour characterisation.",
    no_args_is_help=True,
)

app.add_typer(calculate.app, name="calculate")
app.add_typer(plot.app, name="plot")
app.add_typer(generate.app, name="generate")

app.command(name="about")(about_command)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"cielab-gamut-tools {__version__}")
        raise typer.Exit()


@app.callback()
def _callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass
