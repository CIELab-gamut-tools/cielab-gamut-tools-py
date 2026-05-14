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
matplotlib.use("Agg")  # non-interactive — must be set before importing pyplot

import matplotlib.pyplot as plt

from cielab_gamut_tools import SyntheticGamut
from cielab_gamut_tools.plotting.rings import plot_rings
from cielab_gamut_tools.plotting.surface import plot_surface

IMAGES_DIR = Path(__file__).parent.parent / "docs" / "images"


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    srgb = SyntheticGamut.srgb().gamut
    bt2020 = SyntheticGamut.bt2020().gamut

    # rings_example: sRGB intersection with BT.2020
    # Equivalent CLI: cgt plot rings srgb -r bt.2020 -i
    print("Generating rings_example.png …")
    fig, _ = plot_rings(srgb, reference=bt2020, intersection_plot=True)
    fig.savefig(IMAGES_DIR / "rings_example.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # surface_example: sRGB solid + BT.2020 wireframe (muted chroma, thin lines)
    # Equivalent CLI: cgt plot surface srgb bt.2020 --style ",wireframe+chroma:0.2+lw:0.5"
    print("Generating surface_example.png …")
    fig2 = plt.figure(figsize=(10, 8))
    ax = fig2.add_subplot(111, projection="3d")
    plot_surface(srgb, ax=ax, alpha=0.8)
    plot_surface(bt2020, ax=ax, wireframe=True, chroma=0.2, linewidth=0.5)
    fig2.savefig(IMAGES_DIR / "surface_example.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)

    print(f"\nDone. Images written to {IMAGES_DIR}")
    print("Commit with: git add docs/images/ && git commit -m 'update docs images'")


if __name__ == "__main__":
    main()
