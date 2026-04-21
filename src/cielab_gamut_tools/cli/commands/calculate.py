import typer

app = typer.Typer(
    help="Calculate gamut metrics (volume, coverage, comparison).",
    no_args_is_help=True,
)
