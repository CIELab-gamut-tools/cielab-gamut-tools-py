from typer.testing import CliRunner

from cielab_gamut_tools import __version__
from cielab_gamut_tools.cli._app import app

runner = CliRunner()


class TestAboutCommand:
    def test_exits_zero(self):
        result = runner.invoke(app, ["about"])
        assert result.exit_code == 0

    def test_contains_version(self):
        result = runner.invoke(app, ["about"])
        assert __version__ in result.output

    def test_contains_idms(self):
        result = runner.invoke(app, ["about"])
        assert "IDMS" in result.output

    def test_contains_iec_62977(self):
        result = runner.invoke(app, ["about"])
        assert "62977" in result.output

    def test_contains_iec_62906(self):
        result = runner.invoke(app, ["about"])
        assert "62906" in result.output

    def test_contains_citation(self):
        result = runner.invoke(app, ["about"])
        assert "Smith" in result.output

    def test_british_spelling(self):
        result = runner.invoke(app, ["about"])
        assert "colour" in result.output.lower()
        assert "characterisation" in result.output


class TestVersionFlag:
    def test_version_exits_zero(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_version_output(self):
        result = runner.invoke(app, ["--version"])
        assert __version__ in result.output


class TestCommandGroups:
    def test_calculate_help(self):
        result = runner.invoke(app, ["calculate", "--help"])
        assert result.exit_code == 0
        assert "volume" in result.output.lower() or "calculate" in result.output.lower()

    def test_plot_help(self):
        result = runner.invoke(app, ["plot", "--help"])
        assert result.exit_code == 0

    def test_generate_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert "cielab-tools" in result.output.lower() or result.exit_code in (0, 2)
