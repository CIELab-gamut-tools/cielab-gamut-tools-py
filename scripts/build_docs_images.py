"""
Generate example images for the documentation.

Usage (from the repository root):
    python scripts/build_docs_images.py

After running, commit the generated files:
    git add docs/images/
    git commit -m "update docs images"
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive — must be set before any pyplot import

from typer.testing import CliRunner

from cielab_gamut_tools.cli._app import app

IMAGES_DIR = Path(__file__).parent.parent / "docs" / "images"

runner = CliRunner()


def _invoke(*args: str) -> None:
    result = runner.invoke(app, list(args))
    if result.exit_code != 0:
        raise RuntimeError(
            f"Command failed (exit {result.exit_code}):\n"
            f"  cgt {' '.join(args)}\n"
            f"{result.output}"
        )


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # rings_example: sRGB intersection with BT.2020
    print("Generating rings_example.png …")
    _invoke(
        "plot", "rings", "srgb",
        "--reference", "bt.2020",
        "--intersection",
        "--output", str(IMAGES_DIR / "rings_example.png"),
        "--dpi", "150",
    )

    # surface_example: sRGB solid + BT.2020 wireframe (muted chroma, thin lines)
    print("Generating surface_example.png …")
    _invoke(
        "plot", "surface", "srgb", "bt.2020",
        "--style", ",wireframe+chroma:0.2+lw:0.5",
        "--output", str(IMAGES_DIR / "surface_example.png"),
        "--dpi", "150",
    )

    print(f"\nDone. Images written to {IMAGES_DIR}")
    print("Commit with: git add docs/images/ && git commit -m 'update docs images'")


if __name__ == "__main__":
    main()
