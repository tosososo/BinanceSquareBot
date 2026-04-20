from typer.testing import CliRunner
from binance_square_bot.cli import app

runner = CliRunner()


def test_version():
    """Test version flag works."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "BinanceSquareBot" in result.output


def test_help():
    """Test help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "clean" in result.output
