import webbrowser
from pathlib import Path

import typer

_DIST = Path(__file__).parents[2] / "ui" / "dist"


def ui_command(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Do not open browser automatically."
    ),
) -> None:
    """Start the interactive web UI."""
    import uvicorn

    if not _DIST.is_dir():
        typer.echo(
            "Error: UI assets not found. Build the frontend first:\n\n"
            "    cd src/cielab_gamut_tools/ui/frontend\n"
            "    npm install\n"
            "    npm run build\n\n"
            "Or run  make ui  from the project root.",
            err=True,
        )
        raise typer.Exit(1)

    url = f"http://localhost:{port}"
    typer.echo(f"CIELab gamut tools UI → {url}  (Ctrl-C to stop)")
    if not no_browser:
        webbrowser.open(url)
    uvicorn.run(
        "cielab_gamut_tools.ui.server:app",
        host="localhost",
        port=port,
        reload=False,
    )
