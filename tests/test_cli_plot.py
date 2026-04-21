"""Tests for the `plot` CLI command group (rings and surface)."""
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cielab_gamut_tools.cli._app import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# help
# ---------------------------------------------------------------------------

class TestPlotHelp:
    def test_plot_help_exits_zero(self):
        result = runner.invoke(app, ["plot", "--help"])
        assert result.exit_code == 0

    def test_rings_help_exits_zero(self):
        result = runner.invoke(app, ["plot", "rings", "--help"])
        assert result.exit_code == 0

    def test_rings_help_mentions_reference(self):
        result = runner.invoke(app, ["plot", "rings", "--help"])
        assert "reference" in result.output.lower()

    def test_rings_help_mentions_output(self):
        result = runner.invoke(app, ["plot", "rings", "--help"])
        assert "output" in result.output.lower()

    def test_surface_help_exits_zero(self):
        result = runner.invoke(app, ["plot", "surface", "--help"])
        assert result.exit_code == 0

    def test_surface_help_mentions_output(self):
        result = runner.invoke(app, ["plot", "surface", "--help"])
        assert "output" in result.output.lower()

    def test_surface_help_mentions_alpha(self):
        result = runner.invoke(app, ["plot", "surface", "--help"])
        assert "alpha" in result.output.lower()


# ---------------------------------------------------------------------------
# error cases — no output or show
# ---------------------------------------------------------------------------

class TestPlotErrorCases:
    def test_rings_intersection_without_reference_fails(self):
        result = runner.invoke(app, ["plot", "rings", "srgb", "--intersection", "--show"])
        assert result.exit_code != 0

    def test_rings_unsupported_format_fails(self, tmp_path):
        out = tmp_path / "plot.bmp"
        result = runner.invoke(app, ["plot", "rings", "srgb", "--output", str(out)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# rings — save to file
# ---------------------------------------------------------------------------

class TestPlotRingsSave:
    def test_rings_srgb_saves_png(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(app, ["plot", "rings", "srgb", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert out.stat().st_size > 0

    def test_rings_bt2020_saves_png(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(app, ["plot", "rings", "bt.2020", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_rings_with_reference_saves_png(self, tmp_path):
        out = tmp_path / "rings_ref.png"
        result = runner.invoke(
            app,
            ["plot", "rings", "bt.2020", "--reference", "srgb", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_rings_intersection_saves_png(self, tmp_path):
        out = tmp_path / "rings_intersection.png"
        result = runner.invoke(
            app,
            [
                "plot", "rings", "bt.2020",
                "--reference", "srgb",
                "--intersection",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_rings_saves_svg(self, tmp_path):
        out = tmp_path / "rings.svg"
        result = runner.invoke(app, ["plot", "rings", "srgb", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_rings_custom_dpi(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--output", str(out), "--dpi", "72"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_rings_from_cgats_file(self, tmp_path):
        """Plot rings from a CGATS envelope file."""
        import subprocess, sys
        # Generate a CGATS envelope for sRGB first, then plot it
        cgats_file = tmp_path / "srgb.txt"
        gen_result = runner.invoke(
            app,
            ["generate", "synthetic", "srgb", "--output", str(cgats_file), "--mode", "envelope"],
        )
        assert gen_result.exit_code == 0, gen_result.output

        out = tmp_path / "rings_cgats.png"
        result = runner.invoke(
            app, ["plot", "rings", str(cgats_file), "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()


# ---------------------------------------------------------------------------
# surface — save to file
# ---------------------------------------------------------------------------

class TestPlotSurfaceSave:
    def test_surface_srgb_saves_png(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(app, ["plot", "surface", "srgb", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert out.stat().st_size > 0

    def test_surface_bt2020_saves_png(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(app, ["plot", "surface", "bt.2020", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_surface_saves_svg(self, tmp_path):
        out = tmp_path / "surface.svg"
        result = runner.invoke(app, ["plot", "surface", "srgb", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_surface_custom_alpha(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--output", str(out), "--alpha", "0.5"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_surface_custom_dpi(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--output", str(out), "--dpi", "72"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_surface_two_gamuts_saves_png(self, tmp_path):
        out = tmp_path / "surface_multi.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "bt.2020", "--output", str(out), "--alpha", "0.4"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert out.stat().st_size > 0

    def test_surface_three_gamuts_saves_png(self, tmp_path):
        out = tmp_path / "surface_triple.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "dci-p3", "bt.2020",
             "--output", str(out), "--alpha", "0.4"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_surface_no_gamuts_fails(self):
        result = runner.invoke(app, ["plot", "surface", "--output", "out.png"])
        assert result.exit_code != 0
