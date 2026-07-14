from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from docprep.config import PipelineConfig
from docprep.entrypoint import convert
from docprep.router import ProcessingPath


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=5)
def test_native_pdf_path(mock_pages, mock_mime, mock_convert, mock_classify, native_pdf: Path):
    mock_classify.return_value = ProcessingPath.NATIVE_PDF
    mock_convert.return_value = "# Converted\n\nSome content here." * 10

    result = convert(native_pdf, PipelineConfig())

    assert result.pipeline_used == "standard"
    assert result.escalated is False
    mock_convert.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_vlm")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=1)
def test_scanned_path(mock_pages, mock_mime, mock_convert, mock_classify, scanned_pdf: Path):
    mock_classify.return_value = ProcessingPath.SCANNED
    mock_convert.return_value = "# Scanned content" * 10

    result = convert(scanned_pdf, PipelineConfig())

    assert result.pipeline_used == "vlm"
    mock_convert.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.convert_with_fallback")
@patch("docprep.entrypoint.get_provider")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=5)
def test_escalation(
    mock_pages,
    mock_mime,
    mock_get_provider,
    mock_fallback,
    mock_convert,
    mock_classify,
    native_pdf: Path,
    monkeypatch,
):
    mock_classify.return_value = ProcessingPath.NATIVE_PDF
    mock_convert.return_value = ""
    mock_fallback.return_value = "# Fallback content"
    mock_get_provider.return_value = MagicMock()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    config = PipelineConfig(fallback_provider="openai")
    result = convert(native_pdf, config)

    assert result.escalated is True
    assert result.pipeline_used == "openai"
    mock_fallback.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=5)
def test_no_escalation_when_disabled(
    mock_pages, mock_mime, mock_convert, mock_classify, native_pdf: Path
):
    mock_classify.return_value = ProcessingPath.NATIVE_PDF
    mock_convert.return_value = ""

    config = PipelineConfig(fallback_enabled=False)
    result = convert(native_pdf, config)

    assert result.escalated is False
