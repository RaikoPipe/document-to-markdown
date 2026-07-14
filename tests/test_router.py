from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from docprep.router import ProcessingPath, classify


def test_classify_native_pdf(native_pdf: Path):
    assert classify(native_pdf) == ProcessingPath.NATIVE_PDF


def test_classify_scanned_pdf(scanned_pdf: Path):
    assert classify(scanned_pdf) == ProcessingPath.SCANNED


def test_classify_plain_text(plain_text_file: Path):
    assert classify(plain_text_file) == ProcessingPath.OFFICE


def test_classify_image(png_image: Path):
    assert classify(png_image) == ProcessingPath.SCANNED


def test_classify_unsupported(tmp_path: Path):
    path = tmp_path / "test.bin"
    path.write_bytes(b"\x00\x01\x02\x03" * 100)
    result = classify(path)
    assert result == ProcessingPath.UNSUPPORTED


def test_classify_docx_mime():
    with patch("docprep.router.detect_mime") as mock_mime:
        mock_mime.return_value = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        with patch("docprep.router._classify_pdf"):
            result = classify(Path("fake.docx"))
            assert result == ProcessingPath.OFFICE


def test_classify_pptx_mime():
    with patch("docprep.router.detect_mime") as mock_mime:
        mock_mime.return_value = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        result = classify(Path("fake.pptx"))
        assert result == ProcessingPath.OFFICE
