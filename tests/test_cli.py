from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from docprep.cli import main
from docprep.result import ConversionResult


def _mock_result(source: Path) -> ConversionResult:
    return ConversionResult(
        source_path=source,
        markdown="# Test Output",
        format_detected="application/pdf",
        pipeline_used="standard",
        page_count=1,
        escalated=False,
        processing_time_seconds=0.1,
    )


@patch("docprep.cli.convert")
def test_convert_stdout(mock_convert, native_pdf: Path):
    mock_convert.return_value = _mock_result(native_pdf)
    runner = CliRunner()
    result = runner.invoke(main, ["convert", str(native_pdf)])
    assert result.exit_code == 0
    assert "# Test Output" in result.output


@patch("docprep.cli.convert")
def test_convert_to_file(mock_convert, native_pdf: Path, tmp_path: Path):
    mock_convert.return_value = _mock_result(native_pdf)
    out = tmp_path / "out.md"
    runner = CliRunner()
    result = runner.invoke(main, ["convert", str(native_pdf), "-o", str(out)])
    assert result.exit_code == 0
    assert out.read_text() == "# Test Output"


@patch("docprep.cli.convert")
def test_convert_json_format(mock_convert, native_pdf: Path):
    mock_convert.return_value = _mock_result(native_pdf)
    runner = CliRunner()
    result = runner.invoke(main, ["convert", str(native_pdf), "--format", "json"])
    assert result.exit_code == 0
    assert '"pipeline_used"' in result.output


def test_info_command(native_pdf: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["info", str(native_pdf)])
    assert result.exit_code == 0
    assert "application/pdf" in result.output
    assert "native_pdf" in result.output
