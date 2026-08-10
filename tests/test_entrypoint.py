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


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=5)
def test_mineru_path_hybrid_skips_escalation(
    mock_pages, mock_mime, mock_convert_mineru, mock_classify, native_pdf: Path
):
    mock_classify.return_value = ProcessingPath.NATIVE_PDF
    mock_convert_mineru.return_value = ""  # would normally escalate

    config = PipelineConfig(
        mineru_enabled=True,
        mineru_backend="hybrid-engine",
        fallback_provider="openai",
    )
    result = convert(native_pdf, config)

    assert result.pipeline_used == "mineru:hybrid-engine"
    assert result.escalated is False
    mock_convert_mineru.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.convert_with_fallback")
@patch("docprep.entrypoint.get_provider")
@patch("docprep.entrypoint.detect_mime", return_value="application/pdf")
@patch("docprep.entrypoint.get_page_count", return_value=5)
def test_mineru_path_pipeline_can_escalate(
    mock_pages,
    mock_mime,
    mock_get_provider,
    mock_fallback,
    mock_convert_standard,
    mock_convert_mineru,
    mock_classify,
    native_pdf: Path,
    monkeypatch,
):
    mock_classify.return_value = ProcessingPath.NATIVE_PDF
    mock_convert_mineru.return_value = ""  # low quality -> escalate
    mock_convert_standard.return_value = "# would not be called"
    mock_fallback.return_value = "# Fallback content"
    mock_get_provider.return_value = MagicMock()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    config = PipelineConfig(
        mineru_enabled=True,
        mineru_backend="pipeline",
        fallback_provider="openai",
    )
    result = convert(native_pdf, config)

    assert result.pipeline_used == "openai"
    assert result.escalated is True
    mock_convert_mineru.assert_called_once()
    mock_convert_standard.assert_not_called()
    mock_fallback.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.detect_mime", return_value="text/plain")
@patch("docprep.entrypoint.get_page_count", return_value=1)
def test_mineru_unsupported_mime_falls_back_to_docling(
    mock_pages,
    mock_mime,
    mock_convert_standard,
    mock_convert_mineru,
    mock_classify,
    plain_text_file: Path,
):
    """MinerU doesn't handle text/plain; should fall back to Docling standard."""
    mock_classify.return_value = ProcessingPath.OFFICE
    mock_convert_standard.return_value = "# Plain text content" * 10
    config = PipelineConfig(mineru_enabled=True, mineru_backend="hybrid-engine")

    result = convert(plain_text_file, config)

    assert result.pipeline_used == "standard"
    mock_convert_standard.assert_called_once()
    mock_convert_mineru.assert_not_called()
    assert any("MinerU does not support" in w for w in result.warnings)


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.convert_standard")
@patch("docprep.entrypoint.detect_mime", return_value="application/msword")
@patch("docprep.entrypoint.get_page_count", return_value=2)
def test_mineru_legacy_office_falls_back_to_docling(
    mock_pages,
    mock_mime,
    mock_convert_standard,
    mock_convert_mineru,
    mock_classify,
    tmp_path: Path,
):
    """Legacy .doc is not OOXML; MinerU should defer to Docling."""
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 fake OLE")
    mock_classify.return_value = ProcessingPath.OFFICE
    mock_convert_standard.return_value = "# Legacy doc content" * 10
    config = PipelineConfig(mineru_enabled=True)

    result = convert(source, config)

    assert result.pipeline_used == "standard"
    mock_convert_standard.assert_called_once()
    mock_convert_mineru.assert_not_called()
    assert any("MinerU does not support" in w for w in result.warnings)


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.detect_mime", return_value="image/png")
@patch("docprep.entrypoint.get_page_count", return_value=1)
def test_mineru_image_routed_to_mineru(
    mock_pages, mock_mime, mock_convert_mineru, mock_classify, tmp_path: Path
):
    """Images are in MinerU's supported set and should route there when enabled."""
    # Minimal 1x1 PNG (avoids pymupdf Pixmap.set_rect fixture bug)
    source = tmp_path / "test.png"
    source.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    mock_classify.return_value = ProcessingPath.SCANNED
    mock_convert_mineru.return_value = "# OCR'd image content" * 10
    config = PipelineConfig(mineru_enabled=True, mineru_backend="pipeline")

    result = convert(source, config)

    assert result.pipeline_used == "mineru:pipeline"
    mock_convert_mineru.assert_called_once()


@patch("docprep.entrypoint.classify")
@patch("docprep.entrypoint.convert_mineru")
@patch("docprep.entrypoint.detect_mime", return_value="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
@patch("docprep.entrypoint.get_page_count", return_value=3)
def test_mineru_docx_routed_to_mineru(
    mock_pages, mock_mime, mock_convert_mineru, mock_classify, tmp_path: Path
):
    """DOCX (OOXML) is MinerU-supported and should route there when enabled."""
    source = tmp_path / "doc.docx"
    source.write_bytes(b"PK\x03\x04 fake zip")
    mock_classify.return_value = ProcessingPath.OFFICE
    mock_convert_mineru.return_value = "# MinerU docx content" * 10
    config = PipelineConfig(mineru_enabled=True, mineru_backend="hybrid-engine")

    result = convert(source, config)

    assert result.pipeline_used == "mineru:hybrid-engine"
    mock_convert_mineru.assert_called_once()
