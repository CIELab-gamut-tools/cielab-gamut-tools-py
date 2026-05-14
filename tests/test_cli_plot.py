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

    def test_rings_bad_xlim_fails(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--xlim=bad,values", "--output", str(out)]
        )
        assert result.exit_code != 0

    def test_rings_bad_figsize_fails(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--figsize=10", "--output", str(out)]
        )
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
# rings — new options (item 17)
# ---------------------------------------------------------------------------

class TestPlotRingsNewOptions:
    def test_no_bands(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--no-bands", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_band_chroma(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--band-chroma", "30", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_band_ls_range(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--band-ls=30,80", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_primaries_none(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--primaries", "none", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_primaries_all(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--primaries", "all", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_reference2(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app,
            ["plot", "rings", "srgb", "--reference2", "bt.2020", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_chroma_rings(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app,
            ["plot", "rings", "srgb", "--chroma-rings", "50,100,150", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_title_override(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app,
            ["plot", "rings", "srgb", "--title", "My display", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_no_title(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--no-title", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_figsize(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--figsize=10,10", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_xlim_ylim(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app,
            [
                "plot", "rings", "srgb",
                "--xlim=-150,150", "--ylim=-150,150",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_l_rings(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--l-rings=20,40,60,80", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_ref_primaries(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app,
            [
                "plot", "rings", "srgb",
                "--reference", "bt.2020",
                "--ref-primaries", "rgb",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_primary_color_input(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--primary-color", "input", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_primary_origin_ring(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--primary-origin", "ring", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_no_cent_mark(self, tmp_path):
        out = tmp_path / "rings.png"
        result = runner.invoke(
            app, ["plot", "rings", "srgb", "--no-cent-mark", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output


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

    def test_surface_title(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--title", "My gamut", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_surface_figsize(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--figsize=12,10", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_surface_axis_limits(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            [
                "plot", "surface", "srgb",
                "--xlim=-100,100", "--ylim=-100,100", "--zlim=0,100",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_surface_view_angle(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--elev", "45", "--azim", "30", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_surface_multi_gamut_with_options(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            [
                "plot", "surface", "srgb", "bt.2020",
                "--alpha", "0.5", "--title", "Comparison",
                "--elev", "20", "--azim", "-45",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# surface — wireframe and per-gamut style
# ---------------------------------------------------------------------------

class TestPlotSurfaceWireframe:
    def test_wireframe_all(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--wireframe", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_wireframe_multi_gamut(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "bt.2020", "--wireframe", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_style_wireframe_single(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_style_alpha_single(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "alpha:0.5", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_style_mixed_two_gamuts(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "bt.2020", "--style", "wireframe,alpha:0.5",
             "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_style_with_empty_field(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "bt.2020", "dci-p3",
             "--style", ",wireframe,alpha:0.6", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_style_shorter_than_gamuts(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "bt.2020", "dci-p3",
             "--style", "wireframe,", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_wireframe_grey_shorthand(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+grey", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_wireframe_gray_shorthand(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+gray", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_colour_british(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+colour:#808080", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_color_no_hash(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+color:808080", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_lw(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+lw:2.0", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_alpha(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+alpha:0.5", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_chroma(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+chroma:0.3", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_lightness(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "wireframe+lightness:60", "--output", str(out)]
        )
        assert result.exit_code == 0, result.output

    def test_wireframe_chroma_and_lightness(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--style", "wireframe+chroma:0.3+lightness:60",
             "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_solid_and_wireframe_mixed(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "bt.2020",
             "--style", "alpha:1.0,wireframe+grey+lw:1.5",
             "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_style_color_and_chroma_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--style", "wireframe+color:#808080+chroma:0.3",
             "--output", str(out)],
        )
        assert result.exit_code != 0

    def test_style_color_and_lightness_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--style", "wireframe+colour:#808080+lightness:50",
             "--output", str(out)],
        )
        assert result.exit_code != 0

    def test_style_grey_and_color_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--style", "wireframe+grey+color:#808080",
             "--output", str(out)],
        )
        assert result.exit_code != 0

    def test_style_and_wireframe_flag_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--wireframe", "--style", "wireframe",
             "--output", str(out)],
        )
        assert result.exit_code != 0

    def test_style_and_alpha_flag_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app,
            ["plot", "surface", "srgb", "--alpha", "0.5", "--style", "wireframe",
             "--output", str(out)],
        )
        assert result.exit_code != 0

    def test_style_unknown_token_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "invalid", "--output", str(out)]
        )
        assert result.exit_code != 0

    def test_style_bad_alpha_value_fails(self, tmp_path):
        out = tmp_path / "surface.png"
        result = runner.invoke(
            app, ["plot", "surface", "srgb", "--style", "alpha:notanumber", "--output", str(out)]
        )
        assert result.exit_code != 0
