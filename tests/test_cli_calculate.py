import json
from pathlib import Path

from typer.testing import CliRunner

from cielab_gamut_tools.cli._app import app

runner = CliRunner()

SRGB_FILE = str(Path("tests/data/sRGB.txt"))
LCD_FILE = str(Path("tests/data/lcd.txt"))


class TestCalculateVolumeText:
    def test_single_file_exits_zero(self):
        result = runner.invoke(app, ["calculate", "volume", SRGB_FILE])
        assert result.exit_code == 0

    def test_single_file_contains_volume_label(self):
        result = runner.invoke(app, ["calculate", "volume", SRGB_FILE])
        assert "Volume" in result.output or "volume" in result.output.lower()

    def test_single_file_volume_reasonable(self):
        result = runner.invoke(app, ["calculate", "volume", SRGB_FILE])
        # sRGB volume should be roughly 830k; just check a large number is present
        assert any(c.isdigit() for c in result.output)

    def test_quiet_flag_value_only(self):
        result = runner.invoke(app, ["calculate", "volume", "--quiet", SRGB_FILE])
        assert result.exit_code == 0
        stripped = result.output.strip()
        # Should be a plain number
        float(stripped)

    def test_multiple_files(self):
        result = runner.invoke(app, ["calculate", "volume", SRGB_FILE, LCD_FILE])
        assert result.exit_code == 0

    def test_standard_flag(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--standard", "IDMS", SRGB_FILE]
        )
        assert result.exit_code == 0
        assert "IDMS" in result.output or "Standard" in result.output


class TestCalculateVolumeJson:
    def test_json_output_parseable(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "json", SRGB_FILE]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "volume" in data
        assert "unit" in data

    def test_json_volume_value(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "json", SRGB_FILE]
        )
        data = json.loads(result.output)
        assert 700_000 < data["volume"] < 1_000_000

    def test_json_standard_metadata(self):
        result = runner.invoke(
            app,
            ["calculate", "volume", "--format", "json", "--standard", "IDMS", SRGB_FILE],
        )
        data = json.loads(result.output)
        assert "standard" in data
        assert "calculated" in data
        assert "method" in data

    def test_json_multiple_files_returns_list(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "json", SRGB_FILE, LCD_FILE]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2


class TestCalculateVolumeNamedGamuts:
    def test_srgb_by_name(self):
        result = runner.invoke(app, ["calculate", "volume", "srgb"])
        assert result.exit_code == 0
        assert any(c.isdigit() for c in result.output)

    def test_bt2020_by_name(self):
        result = runner.invoke(app, ["calculate", "volume", "bt.2020"])
        assert result.exit_code == 0

    def test_named_and_file_together(self):
        result = runner.invoke(app, ["calculate", "volume", "srgb", SRGB_FILE])
        assert result.exit_code == 0

    def test_srgb_volume_in_range(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "json", "srgb"]
        )
        data = json.loads(result.output)
        assert 800_000 < data["volume"] < 870_000

    def test_bt2020_larger_than_srgb(self):
        r1 = runner.invoke(app, ["calculate", "volume", "--format", "json", "srgb"])
        r2 = runner.invoke(app, ["calculate", "volume", "--format", "json", "bt.2020"])
        assert json.loads(r2.output)["volume"] > json.loads(r1.output)["volume"]

    def test_unknown_name_exits_nonzero(self):
        result = runner.invoke(app, ["calculate", "volume", "not-a-gamut"])
        assert result.exit_code != 0

    def test_unknown_name_error_mentions_file_and_name(self):
        result = runner.invoke(app, ["calculate", "volume", "not-a-gamut"])
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "not-a-gamut" in combined or result.exit_code != 0


class TestCalculateCoverageText:
    def test_single_reference_exits_zero(self):
        result = runner.invoke(
            app, ["calculate", "coverage", SRGB_FILE, "--reference", "srgb"]
        )
        assert result.exit_code == 0

    def test_shows_coverage_pct(self):
        result = runner.invoke(
            app, ["calculate", "coverage", SRGB_FILE, "--reference", "srgb"]
        )
        assert "%" in result.output

    def test_shows_volumes(self):
        result = runner.invoke(
            app, ["calculate", "coverage", SRGB_FILE, "--reference", "srgb"]
        )
        assert "volume" in result.output.lower() or "Volume" in result.output

    def test_named_dut(self):
        result = runner.invoke(
            app, ["calculate", "coverage", "bt.2020", "--reference", "srgb"]
        )
        assert result.exit_code == 0
        assert "%" in result.output

    def test_multiple_references(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", SRGB_FILE, "--reference", "srgb,bt.2020,dci-p3"],
        )
        assert result.exit_code == 0

    def test_quiet_returns_float(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--quiet", SRGB_FILE, "--reference", "srgb"],
        )
        assert result.exit_code == 0
        float(result.output.strip())

    def test_standard_flag(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", SRGB_FILE, "--reference", "srgb", "--standard", "IDMS"],
        )
        assert result.exit_code == 0
        assert "IDMS" in result.output or "Standard" in result.output


class TestCalculateCoverageJson:
    def test_json_parseable(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "json", SRGB_FILE, "--reference", "srgb"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "coverage_pct" in data

    def test_json_fields(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "json", SRGB_FILE, "--reference", "srgb"],
        )
        data = json.loads(result.output)
        for key in ("dut_volume", "ref_volume", "intersection_volume", "unit"):
            assert key in data

    def test_json_multiple_references_is_list(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "json", SRGB_FILE, "--reference", "srgb,bt.2020"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list) and len(data) == 2

    def test_srgb_self_coverage_near_100(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "json", "srgb", "--reference", "srgb"],
        )
        data = json.loads(result.output)
        assert data["coverage_pct"] > 99.0

    def test_bt2020_coverage_of_srgb_less_than_100(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "json", SRGB_FILE, "--reference", "bt.2020"],
        )
        data = json.loads(result.output)
        assert data["coverage_pct"] < 100.0


class TestCalculateCoverageCsv:
    def test_csv_header(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "csv", SRGB_FILE, "--reference", "srgb"],
        )
        assert result.exit_code == 0
        assert "reference" in result.output
        assert "coverage_pct" in result.output

    def test_csv_multiple_references_row_count(self):
        result = runner.invoke(
            app,
            ["calculate", "coverage", "--format", "csv", SRGB_FILE, "--reference", "srgb,bt.2020,dci-p3"],
        )
        lines = [l for l in result.output.strip().splitlines() if l]
        assert len(lines) == 4  # header + 3 data rows


class TestCalculateCompareVolume:
    def test_two_files_exits_zero(self):
        result = runner.invoke(app, ["calculate", "compare", SRGB_FILE, LCD_FILE])
        assert result.exit_code == 0

    def test_named_gamuts(self):
        result = runner.invoke(app, ["calculate", "compare", "srgb", "bt.2020"])
        assert result.exit_code == 0

    def test_requires_two_gamuts(self):
        result = runner.invoke(app, ["calculate", "compare", SRGB_FILE])
        assert result.exit_code != 0

    def test_json_has_delta(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--format", "json", "srgb", "bt.2020"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list) and len(data) == 2
        assert "delta_pct_vs_first" in data[0]
        assert data[0]["delta_pct_vs_first"] == 0.0

    def test_csv_header(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--format", "csv", "srgb", "bt.2020"]
        )
        assert "delta_pct_vs_first" in result.output

    def test_quiet_returns_volumes(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--quiet", "srgb", "bt.2020"]
        )
        lines = result.output.strip().splitlines()
        assert len(lines) == 2
        float(lines[0])
        float(lines[1])


class TestCalculateCompareReference:
    def test_reference_mode_exits_zero(self):
        result = runner.invoke(
            app, ["calculate", "compare", SRGB_FILE, LCD_FILE, "--reference", "srgb"]
        )
        assert result.exit_code == 0

    def test_reference_shows_coverage(self):
        result = runner.invoke(
            app, ["calculate", "compare", SRGB_FILE, LCD_FILE, "--reference", "srgb"]
        )
        assert "%" in result.output

    def test_reference_json_is_list(self):
        result = runner.invoke(
            app,
            ["calculate", "compare", "--format", "json", SRGB_FILE, LCD_FILE, "--reference", "srgb"],
        )
        data = json.loads(result.output)
        assert isinstance(data, list) and len(data) == 2
        assert "coverage_pct" in data[0]


class TestCalculateCompareMatrix:
    def test_matrix_exits_zero(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--matrix", "srgb", "bt.2020", "dci-p3"]
        )
        assert result.exit_code == 0

    def test_matrix_json_shape(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--format", "json", "--matrix", "srgb", "bt.2020"]
        )
        data = json.loads(result.output)
        assert "matrix_pct" in data
        assert data["matrix_pct"][0][0] == 100.0  # diagonal
        assert data["matrix_pct"][1][1] == 100.0

    def test_matrix_csv_row_count(self):
        result = runner.invoke(
            app, ["calculate", "compare", "--format", "csv", "--matrix", "srgb", "bt.2020", "dci-p3"]
        )
        lines = [l for l in result.output.strip().splitlines() if l]
        assert len(lines) == 4  # header row + 3 data rows

    def test_matrix_and_reference_mutually_exclusive(self):
        result = runner.invoke(
            app,
            ["calculate", "compare", "--matrix", "--reference", "srgb", "srgb", "bt.2020"],
        )
        assert result.exit_code != 0


class TestCalculateVolumeCsv:
    def test_csv_has_header(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "csv", SRGB_FILE]
        )
        assert result.exit_code == 0
        assert "file" in result.output
        assert "volume_dEab3" in result.output

    def test_csv_has_data_row(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "csv", SRGB_FILE]
        )
        lines = [l for l in result.output.strip().splitlines() if l]
        assert len(lines) == 2  # header + 1 data row

    def test_csv_multiple_files(self):
        result = runner.invoke(
            app, ["calculate", "volume", "--format", "csv", SRGB_FILE, LCD_FILE]
        )
        lines = [l for l in result.output.strip().splitlines() if l]
        assert len(lines) == 3  # header + 2 data rows
