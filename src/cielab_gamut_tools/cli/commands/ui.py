import webbrowser

import typer


def ui_command(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Do not open browser automatically."
    ),
) -> None:
    """Start the interactive web UI."""
    import uvicorn

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
