"""Tests for the `generate` CLI command group (rgb-signals and reference)."""
import csv
import io
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cielab_gamut_tools.cli._app import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# generate rgb-signals
# ---------------------------------------------------------------------------

class TestGenerateRgbSignalsHelp:
    def test_exits_zero(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--help"])
        assert result.exit_code == 0

    def test_mentions_grid(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--help"])
        assert "grid" in result.output.lower()

    def test_mentions_bits(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--help"])
        assert "bits" in result.output.lower()


class TestGenerateRgbSignalsCgats:
    def test_default_exits_zero(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        assert result.exit_code == 0

    def test_default_produces_cgats_header(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        assert "CGATS.17" in result.output

    def test_default_produces_602_rows(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        # Count BEGIN_DATA .. END_DATA rows
        lines = result.output.splitlines()
        in_data = False
        rows = []
        for line in lines:
            if line.strip() == "BEGIN_DATA":
                in_data = True
                continue
            if line.strip() == "END_DATA":
                break
            if in_data and line.strip():
                rows.append(line)
        assert len(rows) == 602

    def test_number_of_sets_602(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        assert "NUMBER_OF_SETS\t602" in result.output

    def test_default_8bit_max_value_255(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        # Last signal for sRGB cube is white (255 255 255)
        assert "255 255 255" in result.output

    def test_grid_5_produces_98_rows(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--grid", "5"])
        assert result.exit_code == 0
        assert "NUMBER_OF_SETS\t98" in result.output

    def test_16bit_max_value_65535(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--bits", "16"])
        assert result.exit_code == 0
        assert "65535 65535 65535" in result.output

    def test_output_to_file(self, tmp_path):
        out = tmp_path / "signals.txt"
        result = runner.invoke(app, ["generate", "rgb-signals", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "CGATS.17" in content
        assert "NUMBER_OF_SETS\t602" in content

    def test_file_type_header(self):
        result = runner.invoke(app, ["generate", "rgb-signals"])
        assert "CGE_SIGNALS" in result.output


class TestGenerateRgbSignalsCsv:
    def test_csv_exits_zero(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--format", "csv"])
        assert result.exit_code == 0

    def test_csv_has_header_row(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--format", "csv"])
        first_line = result.output.splitlines()[0]
        assert first_line == "R,G,B"

    def test_csv_has_602_data_rows(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--format", "csv"])
        rows = list(csv.reader(io.StringIO(result.output)))
        assert len(rows) == 603  # header + 602 data rows

    def test_csv_values_are_integers(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--format", "csv"])
        rows = list(csv.reader(io.StringIO(result.output)))[1:]  # skip header
        for row in rows[:10]:  # spot-check first 10
            assert len(row) == 3
            for val in row:
                assert val.isdigit()

    def test_csv_10bit(self):
        result = runner.invoke(
            app, ["generate", "rgb-signals", "--format", "csv", "--bits", "10"]
        )
        assert result.exit_code == 0
        rows = list(csv.reader(io.StringIO(result.output)))[1:]
        # White point should be 1023 for 10-bit
        white = [row for row in rows if row == ["1023", "1023", "1023"]]
        assert len(white) == 1

    def test_csv_to_file(self, tmp_path):
        out = tmp_path / "signals.csv"
        result = runner.invoke(
            app, ["generate", "rgb-signals", "--format", "csv", "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        rows = list(csv.reader(out.open(encoding="utf-8")))
        assert rows[0] == ["R", "G", "B"]
        assert len(rows) == 603


class TestGenerateRgbSignalsErrors:
    def test_invalid_format(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--format", "xml"])
        assert result.exit_code != 0

    def test_invalid_grid(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--grid", "1"])
        assert result.exit_code != 0

    def test_invalid_bits(self):
        result = runner.invoke(app, ["generate", "rgb-signals", "--bits", "0"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# generate reference
# ---------------------------------------------------------------------------

class TestGenerateSyntheticHelp:
    def test_exits_zero(self):
        result = runner.invoke(app, ["generate", "synthetic", "--help"])
        assert result.exit_code == 0

    def test_lists_named_gamuts(self):
        result = runner.invoke(app, ["generate", "synthetic", "--help"])
        assert "srgb" in result.output.lower()
        assert "bt.2020" in result.output.lower()


class TestGenerateSyntheticNamed:
    @pytest.mark.parametrize("name", ["srgb", "bt.2020", "dci-p3", "display-p3", "adobe-rgb"])
    def test_named_gamut_exits_zero(self, name):
        result = runner.invoke(app, ["generate", "synthetic", name])
        assert result.exit_code == 0

    def test_srgb_produces_cgats(self):
        result = runner.invoke(app, ["generate", "synthetic", "srgb"])
        assert "CGATS.17" in result.output

    def test_srgb_envelope_has_lab_columns(self):
        result = runner.invoke(app, ["generate", "synthetic", "srgb"])
        assert "LAB_L" in result.output
        assert "LAB_A" in result.output
        assert "LAB_B" in result.output

    def test_srgb_envelope_file_type(self):
        result = runner.invoke(app, ["generate", "synthetic", "srgb"])
        assert "CGE_ENVELOPE" in result.output

    def test_srgb_envelope_602_rows(self):
        result = runner.invoke(app, ["generate", "synthetic", "srgb"])
        assert "NUMBER_OF_SETS\t602" in result.output

    def test_measurement_mode_has_xyz_columns(self):
        result = runner.invoke(
            app, ["generate", "synthetic", "srgb", "--mode", "measurement"]
        )
        assert result.exit_code == 0
        assert "XYZ_X" in result.output
        assert "CGE_MEASUREMENT" in result.output

    def test_all_mode_has_both(self):
        result = runner.invoke(
            app, ["generate", "synthetic", "srgb", "--mode", "all"]
        )
        assert result.exit_code == 0
        assert "LAB_L" in result.output
        assert "XYZ_X" in result.output

    def test_output_to_file(self, tmp_path):
        out = tmp_path / "srgb.txt"
        result = runner.invoke(
            app, ["generate", "synthetic", "srgb", "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "CGATS.17" in content
        assert "CGE_ENVELOPE" in content

    def test_case_insensitive_name(self):
        result = runner.invoke(app, ["generate", "synthetic", "SRGB"])
        assert result.exit_code == 0
        assert "CGATS.17" in result.output


class TestGenerateSyntheticCustom:
    # Adobe RGB primaries + D65 white — should produce a valid gamut
    ADOBE_PRIMARIES = "0.64,0.33,0.21,0.71,0.15,0.06"
    D65_WHITE = "0.3127,0.3290"

    def test_custom_primaries_exits_zero(self):
        result = runner.invoke(
            app,
            [
                "generate", "synthetic",
                "--primaries", self.ADOBE_PRIMARIES,
                "--white", self.D65_WHITE,
            ],
        )
        assert result.exit_code == 0

    def test_custom_primaries_produces_cgats(self):
        result = runner.invoke(
            app,
            [
                "generate", "synthetic",
                "--primaries", self.ADOBE_PRIMARIES,
                "--white", self.D65_WHITE,
            ],
        )
        assert "CGATS.17" in result.output

    def test_custom_primaries_to_file(self, tmp_path):
        out = tmp_path / "custom.txt"
        result = runner.invoke(
            app,
            [
                "generate", "synthetic",
                "--primaries", self.ADOBE_PRIMARIES,
                "--white", self.D65_WHITE,
                "--gamma", "2.2",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0
        assert out.exists()


class TestGenerateSyntheticErrors:
    def test_no_args_fails(self):
        result = runner.invoke(app, ["generate", "synthetic"])
        assert result.exit_code != 0

    def test_gamut_and_primaries_mutually_exclusive(self):
        result = runner.invoke(
            app,
            [
                "generate", "synthetic", "srgb",
                "--primaries", "0.64,0.33,0.21,0.71,0.15,0.06",
            ],
        )
        assert result.exit_code != 0

    def test_primaries_without_white_fails(self):
        result = runner.invoke(
            app,
            ["generate", "synthetic", "--primaries", "0.64,0.33,0.21,0.71,0.15,0.06"],
        )
        assert result.exit_code != 0

    def test_wrong_primaries_count_fails(self):
        result = runner.invoke(
            app,
            [
                "generate", "synthetic",
                "--primaries", "0.64,0.33,0.21",
                "--white", "0.3127,0.3290",
            ],
        )
        assert result.exit_code != 0

    def test_wrong_white_count_fails(self):
        result = runner.invoke(
            app,
            [
                "generate", "synthetic",
                "--primaries", "0.64,0.33,0.21,0.71,0.15,0.06",
                "--white", "0.3127",
            ],
        )
        assert result.exit_code != 0

    def test_unknown_named_gamut_fails(self):
        result = runner.invoke(app, ["generate", "synthetic", "rec2020"])
        assert result.exit_code != 0

    def test_invalid_mode_fails(self):
        result = runner.invoke(
            app, ["generate", "synthetic", "srgb", "--mode", "xyz-only"]
        )
        assert result.exit_code != 0
